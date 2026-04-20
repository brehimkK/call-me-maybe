#!/usr/bin/env python3
"""
sync_issues.py — Idempotent GitHub issue sync tool for Call Me Maybe.

Usage (called by GitHub Actions workflow):
    python sync_issues.py [options]

Options:
    --payload PATH      Path to issues.yaml payload file (required)
    --repo OWNER/REPO   Target repository slug (required)
    --token TOKEN       GitHub API token (required, or via GITHUB_TOKEN env var)
    --mode MODE         create | update | sync  (default: sync)
    --dry-run           Print planned actions, do not mutate GitHub state
    --include-bonus     Include issues marked bonus:true (default: False)
    --fail-on-error     Exit non-zero if any P0 issue fails (default: True)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib import request, error as urllib_error
from urllib.parse import quote

import yaml


# ---------------------------------------------------------------------------
# GitHub API client (stdlib-only, no external dependencies)
# ---------------------------------------------------------------------------

class GitHubAPIError(Exception):
    """Raised when the GitHub REST API returns a non-2xx response."""

    def __init__(self, status: int, message: str, body: str = "") -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


class GitHubClient:
    """Minimal GitHub REST API v3 client using urllib (no third-party libs)."""

    BASE = "https://api.github.com"
    RETRY_STATUSES = {429, 500, 502, 503, 504}
    MAX_RETRIES = 3
    RETRY_BACKOFF = 2.0  # seconds, doubles each retry

    def __init__(self, token: str, repo: str) -> None:
        self.token = token
        self.repo = repo  # "owner/repo"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "sync-issues/1.0",
        }

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.BASE}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = request.Request(url, data=data, headers=self._headers(), method=method)
        delay = self.RETRY_BACKOFF
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                with request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode()
                    return json.loads(raw) if raw.strip() else {}
            except urllib_error.HTTPError as exc:
                body_text = exc.read().decode(errors="replace") if exc.fp else ""
                if exc.code in self.RETRY_STATUSES and attempt <= self.MAX_RETRIES:
                    print(
                        f"  [retry {attempt}/{self.MAX_RETRIES}] HTTP {exc.code} — waiting {delay:.1f}s",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise GitHubAPIError(exc.code, str(exc.reason), body_text) from exc

        raise GitHubAPIError(0, "Max retries exceeded")

    # ------------------------------------------------------------------
    # Milestones
    # ------------------------------------------------------------------

    def list_milestones(self, state: str = "open") -> list[dict[str, Any]]:
        path = f"/repos/{self.repo}/milestones?state={state}&per_page=100"
        results: list[dict[str, Any]] = []
        while path:
            page = self._request("GET", path)
            results.extend(page)
            path = ""  # pagination not needed for small milestone counts
        return results

    def create_milestone(self, title: str, description: str = "") -> dict[str, Any]:
        return self._request(
            "POST",
            f"/repos/{self.repo}/milestones",
            {"title": title, "description": description},
        )

    def resolve_milestone(
        self,
        title: str,
        description: str,
        existing: dict[str, int],
        dry_run: bool,
    ) -> Optional[int]:
        if title in existing:
            return existing[title]
        if dry_run:
            print(f"  [dry-run] Would create milestone: {title!r}")
            return None
        ms = self.create_milestone(title, description)
        number: int = ms["number"]
        existing[title] = number
        print(f"  Created milestone #{number}: {title!r}")
        return number

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------

    def list_labels(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self._request(
                "GET",
                f"/repos/{self.repo}/labels?per_page=100&page={page}",
            )
            if not batch:
                break
            results.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return results

    def create_label(self, name: str, color: str, description: str) -> None:
        self._request(
            "POST",
            f"/repos/{self.repo}/labels",
            {"name": name, "color": color.lstrip("#"), "description": description},
        )

    def ensure_labels(
        self,
        label_defs: list[dict[str, Any]],
        dry_run: bool,
    ) -> None:
        if dry_run:
            for lbl in label_defs:
                print(f"  [dry-run] Would ensure label exists: {lbl['name']!r}")
            return
        existing = {lbl["name"] for lbl in self.list_labels()}
        for lbl in label_defs:
            if lbl["name"] not in existing:
                self.create_label(lbl["name"], lbl["color"], lbl.get("description", ""))
                print(f"  Created label: {lbl['name']!r}")

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    def search_issues_by_fingerprint(self, fingerprint: str) -> Optional[dict[str, Any]]:
        """Search for an issue whose body contains the fingerprint comment."""
        q = quote(f'repo:{self.repo} is:issue in:body "{fingerprint}"')
        data = self._request("GET", f"/search/issues?q={q}&per_page=5")
        items: list[dict[str, Any]] = data.get("items", [])
        for item in items:
            body = item.get("body", "") or ""
            if fingerprint in body:
                return item
        return None

    def search_issues_by_title(self, title: str) -> Optional[dict[str, Any]]:
        """Fallback: search by exact title."""
        q = quote(f'repo:{self.repo} is:issue in:title "{title}"')
        data = self._request("GET", f"/search/issues?q={q}&per_page=10")
        items: list[dict[str, Any]] = data.get("items", [])
        for item in items:
            if item.get("title", "") == title:
                return item
        return None

    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str],
        milestone: Optional[int],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title, "body": body, "labels": labels}
        if milestone is not None:
            payload["milestone"] = milestone
        return self._request("POST", f"/repos/{self.repo}/issues", payload)

    def update_issue(
        self,
        number: int,
        title: str,
        body: str,
        labels: list[str],
        milestone: Optional[int],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title, "body": body, "labels": labels}
        if milestone is not None:
            payload["milestone"] = milestone
        return self._request("PATCH", f"/repos/{self.repo}/issues/{number}", payload)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class IssueSpec:
    id: str
    title: str
    body: str
    milestone: str
    priority: str
    size: str
    bonus: bool
    labels: list[str]
    blocked_by: list[str]
    blocks: list[str]

    @property
    def fingerprint(self) -> str:
        return f"<!-- fingerprint:call-me-maybe:{self.id} -->"

    @property
    def is_p0(self) -> bool:
        return self.priority == "P0"


@dataclass
class SyncResult:
    issue_id: str
    title: str
    action: str  # created | updated | skipped | failed | dry-run
    issue_number: Optional[int] = None
    error: Optional[str] = None


@dataclass
class SyncReport:
    results: list[SyncResult] = field(default_factory=list)

    @property
    def created(self) -> list[SyncResult]:
        return [r for r in self.results if r.action == "created"]

    @property
    def updated(self) -> list[SyncResult]:
        return [r for r in self.results if r.action == "updated"]

    @property
    def skipped(self) -> list[SyncResult]:
        return [r for r in self.results if r.action == "skipped"]

    @property
    def failed(self) -> list[SyncResult]:
        return [r for r in self.results if r.action == "failed"]

    @property
    def dry_run_items(self) -> list[SyncResult]:
        return [r for r in self.results if r.action == "dry-run"]


# ---------------------------------------------------------------------------
# Payload loading and validation
# ---------------------------------------------------------------------------

REQUIRED_ISSUE_FIELDS = {"id", "title", "body", "milestone", "priority", "size", "bonus", "labels"}
VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_SIZES = {"XS", "S", "M", "L"}
VALID_MODES = {"create", "update", "sync"}


def load_payload(path: Path) -> dict[str, Any]:
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Payload root must be a mapping, got {type(data).__name__}")
    _validate_payload_schema(data)
    return data


def _validate_payload_schema(data: dict[str, Any]) -> None:
    errors: list[str] = []

    if "project" not in data:
        errors.append("Missing required field: 'project'")
    if "milestones" not in data or not isinstance(data["milestones"], list):
        errors.append("Missing or invalid field: 'milestones' (must be a list)")
    if "issues" not in data or not isinstance(data["issues"], list):
        errors.append("Missing or invalid field: 'issues' (must be a list)")

    for i, issue in enumerate(data.get("issues", [])):
        prefix = f"issues[{i}]"
        missing = REQUIRED_ISSUE_FIELDS - set(issue.keys())
        if missing:
            errors.append(f"{prefix}: missing fields: {sorted(missing)}")
            continue
        if issue["priority"] not in VALID_PRIORITIES:
            errors.append(
                f"{prefix}.priority: invalid value {issue['priority']!r} — must be one of {sorted(VALID_PRIORITIES)}"
            )
        if issue["size"] not in VALID_SIZES:
            errors.append(
                f"{prefix}.size: invalid value {issue['size']!r} — must be one of {sorted(VALID_SIZES)}"
            )
        if not isinstance(issue["labels"], list):
            errors.append(f"{prefix}.labels: must be a list")
        if not isinstance(issue["bonus"], bool):
            errors.append(f"{prefix}.bonus: must be a boolean")

    if errors:
        msg = "\n".join(f"  - {e}" for e in errors)
        raise ValueError(f"Payload schema validation failed:\n{msg}")


def build_issue_specs(data: dict[str, Any], include_bonus: bool) -> list[IssueSpec]:
    specs: list[IssueSpec] = []
    for raw in data["issues"]:
        spec = IssueSpec(
            id=raw["id"],
            title=raw["title"],
            body=raw["body"].strip(),
            milestone=raw["milestone"],
            priority=raw["priority"],
            size=raw["size"],
            bonus=raw["bonus"],
            labels=list(raw.get("labels", [])),
            blocked_by=list(raw.get("blocked_by", [])),
            blocks=list(raw.get("blocks", [])),
        )
        if spec.bonus and not include_bonus:
            continue
        specs.append(spec)
    return specs


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------

def sync_issues(
    client: GitHubClient,
    specs: list[IssueSpec],
    milestone_map: dict[str, Optional[int]],
    mode: str,
    dry_run: bool,
    fail_on_p0_error: bool,
) -> SyncReport:
    report = SyncReport()

    for spec in specs:
        print(f"\n{'[DRY-RUN] ' if dry_run else ''}Processing {spec.id}: {spec.title!r}")
        ms_number = milestone_map.get(spec.milestone)

        try:
            if dry_run:
                # Never query the API in dry-run mode
                result = SyncResult(spec.id, spec.title, "dry-run")
                _print_result(result)
                report.results.append(result)
                continue

            existing = _find_existing_issue(client, spec)
            result = _sync_single_issue(
                client=client,
                spec=spec,
                existing=existing,
                milestone_number=ms_number,
                mode=mode,
            )
        except GitHubAPIError as exc:
            result = SyncResult(
                issue_id=spec.id,
                title=spec.title,
                action="failed",
                error=str(exc),
            )
            print(f"  ERROR: {exc}", file=sys.stderr)
            if spec.is_p0 and fail_on_p0_error:
                report.results.append(result)
                _print_summary(report)
                print(
                    f"\nFatal: P0 issue {spec.id} failed and --fail-on-error is set. Aborting.",
                    file=sys.stderr,
                )
                sys.exit(1)

        report.results.append(result)
        _print_result(result)

        # Rate limit courtesy pause between API calls
        time.sleep(0.5)

    return report


def _find_existing_issue(
    client: GitHubClient,
    spec: IssueSpec,
) -> Optional[dict[str, Any]]:
    """Search by fingerprint first, fall back to exact title."""
    existing = client.search_issues_by_fingerprint(spec.fingerprint)
    if existing is not None:
        return existing
    return client.search_issues_by_title(spec.title)


def _sync_single_issue(
    client: GitHubClient,
    spec: IssueSpec,
    existing: Optional[dict[str, Any]],
    milestone_number: Optional[int],
    mode: str,
) -> SyncResult:
    if existing:
        issue_number: Optional[int] = existing.get("number")
        url = existing.get("html_url", "")
        if mode == "create":
            print(f"  Skipping (exists #{issue_number}, mode=create): {url}")
            return SyncResult(spec.id, spec.title, "skipped", issue_number)
        # mode == update or sync → update
        if issue_number is None:
            raise GitHubAPIError(0, f"Existing issue for {spec.id!r} has no 'number' field")
        updated = client.update_issue(
            number=issue_number,
            title=spec.title,
            body=spec.body,
            labels=spec.labels,
            milestone=milestone_number,
        )
        return SyncResult(spec.id, spec.title, "updated", updated["number"])
    else:
        if mode == "update":
            print(f"  Skipping (not found, mode=update)")
            return SyncResult(spec.id, spec.title, "skipped")
        # mode == create or sync → create
        created = client.create_issue(
            title=spec.title,
            body=spec.body,
            labels=spec.labels,
            milestone=milestone_number,
        )
        return SyncResult(spec.id, spec.title, "created", created["number"])


def _print_result(result: SyncResult) -> None:
    icon = {
        "created": "✅",
        "updated": "🔄",
        "skipped": "⏭️",
        "failed": "❌",
        "dry-run": "🔍",
    }.get(result.action, "?")
    num = f" #{result.issue_number}" if result.issue_number else ""
    err = f" — {result.error}" if result.error else ""
    print(f"  {icon} [{result.action.upper()}]{num} {result.title!r}{err}")


# ---------------------------------------------------------------------------
# Milestone resolution
# ---------------------------------------------------------------------------

def resolve_milestones(
    client: GitHubClient,
    milestone_defs: list[dict[str, str]],
    dry_run: bool,
) -> dict[str, Optional[int]]:
    result: dict[str, Optional[int]] = {}
    if dry_run:
        for ms_def in milestone_defs:
            print(f"  [dry-run] Would ensure milestone exists: {ms_def['title']!r}")
            result[ms_def["title"]] = None
        return result
    existing_raw = client.list_milestones(state="open") + client.list_milestones(state="closed")
    existing: dict[str, int] = {m["title"]: m["number"] for m in existing_raw}
    for ms_def in milestone_defs:
        title = ms_def["title"]
        description = ms_def.get("description", "")
        number = client.resolve_milestone(title, description, existing, dry_run)
        result[title] = number
    return result


# ---------------------------------------------------------------------------
# GitHub Actions step summary
# ---------------------------------------------------------------------------

def write_step_summary(report: SyncReport, dry_run: bool, include_bonus: bool) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    lines = [
        "## 📋 Issue Sync Report\n",
        f"**Mode:** {'dry-run' if dry_run else 'live'} | "
        f"**Bonus issues:** {'included' if include_bonus else 'excluded'}\n",
        "",
        "| ID | Title | Action | Issue # |",
        "|----|-------|--------|---------|",
    ]
    for r in report.results:
        num = f"#{r.issue_number}" if r.issue_number else "—"
        lines.append(f"| `{r.issue_id}` | {r.title} | {r.action} | {num} |")

    lines += [
        "",
        "### Summary",
        f"- ✅ Created: {len(report.created)}",
        f"- 🔄 Updated: {len(report.updated)}",
        f"- ⏭️ Skipped: {len(report.skipped)}",
        f"- ❌ Failed: {len(report.failed)}",
        f"- 🔍 Dry-run planned: {len(report.dry_run_items)}",
    ]

    with open(summary_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def _print_summary(report: SyncReport) -> None:
    print("\n" + "=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)
    print(f"  Created  : {len(report.created)}")
    print(f"  Updated  : {len(report.updated)}")
    print(f"  Skipped  : {len(report.skipped)}")
    print(f"  Failed   : {len(report.failed)}")
    print(f"  Dry-run  : {len(report.dry_run_items)}")
    print("=" * 60)
    if report.failed:
        print("\nFailed issues:")
        for r in report.failed:
            print(f"  - {r.issue_id}: {r.title!r} — {r.error}")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Idempotently sync GitHub issues from a YAML payload file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--payload",
        required=True,
        type=Path,
        help="Path to the issues.yaml payload file",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository slug: owner/repo",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN", ""),
        help="GitHub API token (default: $GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--mode",
        choices=list(VALID_MODES),
        default="sync",
        help="Sync mode: create (never update), update (never create), sync (both). Default: sync",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without mutating GitHub state",
    )
    parser.add_argument(
        "--include-bonus",
        action="store_true",
        help="Include issues marked bonus:true (default: skip them)",
    )
    parser.add_argument(
        "--no-fail-on-error",
        action="store_true",
        help="Do not exit with non-zero status when a P0 issue fails (default: fail)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    if not args.token:
        print(
            "Error: GitHub token required. Pass --token or set $GITHUB_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.payload.exists():
        print(f"Error: Payload file not found: {args.payload}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading payload: {args.payload}")
    data = load_payload(args.payload)
    print(f"  Project: {data['project']}")
    print(f"  Milestones: {len(data['milestones'])}")
    print(f"  Issues (total): {len(data['issues'])}")

    specs = build_issue_specs(data, include_bonus=args.include_bonus)
    print(
        f"  Issues (after bonus filter, include_bonus={args.include_bonus}): {len(specs)}"
    )

    client = GitHubClient(token=args.token, repo=args.repo)

    print(f"\nResolving labels ({'dry-run' if args.dry_run else 'live'})...")
    client.ensure_labels(data.get("labels", []), dry_run=args.dry_run)

    print(f"\nResolving milestones ({'dry-run' if args.dry_run else 'live'})...")
    milestone_map = resolve_milestones(
        client, data["milestones"], dry_run=args.dry_run
    )

    print(f"\nSyncing issues (mode={args.mode}, dry-run={args.dry_run})...")
    report = sync_issues(
        client=client,
        specs=specs,
        milestone_map=milestone_map,
        mode=args.mode,
        dry_run=args.dry_run,
        fail_on_p0_error=not args.no_fail_on_error,
    )

    _print_summary(report)
    write_step_summary(report, dry_run=args.dry_run, include_bonus=args.include_bonus)

    if report.failed and not args.no_fail_on_error:
        p0_failures = [r for r in report.failed if any(
            s.id == r.issue_id and s.is_p0 for s in specs
        )]
        if p0_failures:
            print(
                f"\nFatal: {len(p0_failures)} P0 issue(s) failed. Exiting non-zero.",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
