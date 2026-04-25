#!/usr/bin/env python3
# bulk_update_issues.py
# Usage:
#   export GITHUB_TOKEN=ghp_xxx
#   python bulk_update_issues.py
#
# Repo target: brehimkK/call-me-maybe

import os
import requests
from datetime import datetime

OWNER = "brehimkK"
REPO = "call-me-maybe"
API = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN")

if not TOKEN:
    raise SystemExit("Missing GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

SUBJECT_HEADER = """# call me maybe — Introduction to function calling in LLMs

**Summary:** Does LLMs speak the language of computers? We’ll find out.  
**Made in collaboration with:** @ldevelle, @pcamaren, @crfernan  
**Version:** 1.3

---

## Mandatory alignment checklist (from subject)
- [ ] Python 3.10+
- [ ] flake8 + mypy compliance
- [ ] Graceful error handling (no crashes)
- [ ] Type hints + docstrings
- [ ] Makefile rules: `install`, `run`, `debug`, `clean`, `lint` (+ optional `lint-strict`)
- [ ] Pydantic validation for classes
- [ ] No forbidden libs (dspy/transformers/huggingface/pytorch/outlines/etc.)
- [ ] Uses Qwen/Qwen3-0.6B compatibility
- [ ] Function chosen by LLM (no heuristics)
- [ ] No private llm_sdk APIs
- [ ] `uv sync`-compatible setup
- [ ] Correct CLI usage with input/output paths
- [ ] Output JSON strictly: `prompt`, `name`, `parameters`
- [ ] Deterministic + reliable behavior
- [ ] README complete per subject requirements
"""

MILESTONES_WANTED = {
    "M1 - Foundation & Architecture",
    "M2 - Core Function Calling Pipeline",
    "M3 - Validation, Determinism & Tests",
    "M4 - Documentation & Submission",
}

def gh_get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def gh_post(url, payload):
    r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def gh_patch(url, payload):
    r = requests.patch(url, headers=HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def ensure_label(name, color="0e8a16", description=""):
    url = f"{API}/repos/{OWNER}/{REPO}/labels/{name}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 404:
        gh_post(f"{API}/repos/{OWNER}/{REPO}/labels", {
            "name": name,
            "color": color,
            "description": description[:100],
        })

def get_all_open_issues():
    issues = []
    page = 1
    while True:
        batch = gh_get(
            f"{API}/repos/{OWNER}/{REPO}/issues",
            params={"state": "open", "per_page": 100, "page": page}
        )
        if not batch:
            break
        # Exclude pull requests
        batch = [i for i in batch if "pull_request" not in i]
        issues.extend(batch)
        page += 1
    return issues

def get_milestones():
    ms = []
    page = 1
    while True:
        batch = gh_get(
            f"{API}/repos/{OWNER}/{REPO}/milestones",
            params={"state": "all", "per_page": 100, "page": page}
        )
        if not batch:
            break
        ms.extend(batch)
        page += 1
    return ms

def ensure_milestone(title):
    milestones = get_milestones()
    for m in milestones:
        if m["title"] == title:
            return m["number"]
    created = gh_post(f"{API}/repos/{OWNER}/{REPO}/milestones", {"title": title})
    return created["number"]

def normalize_title(old_title):
    base = old_title.strip()
    # remove duplicate prefix if any
    prefix = "call me maybe – "
    if base.lower().startswith(prefix):
        return base
    return f"{prefix}{base}"

def classify(issue):
    t = issue["title"].lower()
    b = (issue.get("body") or "").lower()

    if any(k in t or k in b for k in ["readme", "documentation", "docs"]):
        return {
            "labels": ["type:docs", "priority:P0", "status:ready", "area:docs", "size:S"],
            "milestone": "M4 - Documentation & Submission"
        }
    if any(k in t or k in b for k in ["test", "validation", "determinism"]):
        return {
            "labels": ["type:test", "priority:P0", "status:ready", "area:validation", "size:M"],
            "milestone": "M3 - Validation, Determinism & Tests"
        }
    if any(k in t or k in b for k in ["pipeline", "extract", "adapter", "llm", "parser", "schema"]):
        return {
            "labels": ["type:feature", "priority:P0", "status:ready", "area:pipeline", "size:M"],
            "milestone": "M2 - Core Function Calling Pipeline"
        }
    return {
        "labels": ["type:chore", "priority:P1", "status:ready", "area:architecture", "size:S"],
        "milestone": "M1 - Foundation & Architecture"
    }

def build_body(issue):
    old = issue.get("body") or ""
    number = issue["number"]
    title = issue["title"]

    steps = f"""## Exact implementation steps (subject-compliant)
1. Re-read Chapter IV and V constraints before coding.
2. Implement only what this issue requires in `src/` with type hints + docstrings.
3. Ensure error handling is explicit (no unhandled exceptions).
4. Add/adjust tests for this issue scope.
5. Run:
   - `uv sync`
   - `make lint`
   - `make test`
   - `uv run python -m src --functions_definition data/input/functions_definition.json --input data/input/function_calling_tests.json --output data/output/function_calls.json`
6. Validate output format strictly:
   - array of objects
   - keys exactly: `prompt`, `name`, `parameters`
   - parameter types match `functions_definition.json`
7. Update README section impacted by this change.
8. Add evidence in comments/PR: command outputs + what was validated.

## Acceptance criteria
- [ ] Matches subject v1.3 constraints exactly
- [ ] Deterministic and robust behavior for this issue scope
- [ ] Lint + tests passing
- [ ] No forbidden dependencies
- [ ] Reviewer can reproduce via `uv sync` and run command

## Original issue content (archived)
{old if old.strip() else "_No prior body content._"}

---

_Last normalized automatically on {datetime.utcnow().isoformat()}Z for subject compliance._
"""
    return SUBJECT_HEADER + "\n" + steps

def main():
    # ensure baseline labels
    labels_def = [
        ("type:feature","1d76db","New functionality"),
        ("type:docs","0075ca","Documentation work"),
        ("type:test","5319e7","Testing work"),
        ("type:chore","7057ff","Maintenance task"),
        ("priority:P0","b60205","Critical"),
        ("priority:P1","d93f0b","High"),
        ("priority:P2","fbca04","Medium"),
        ("status:ready","0e8a16","Ready to start"),
        ("area:pipeline","006b75","Pipeline"),
        ("area:validation","5319e7","Validation"),
        ("area:docs","0052cc","Docs"),
        ("area:architecture","3f51b5","Architecture"),
        ("size:S","bfdadc","Small"),
        ("size:M","bfd4f2","Medium"),
        ("size:L","c2e0c6","Large"),
    ]
    for n,c,d in labels_def:
        ensure_label(n,c,d)

    # ensure milestones
    ms_numbers = {title: ensure_milestone(title) for title in MILESTONES_WANTED}

    issues = get_all_open_issues()
    print(f"Found {len(issues)} open issues")

    for issue in issues:
        num = issue["number"]
        norm = classify(issue)
        new_title = normalize_title(issue["title"])
        new_body = build_body(issue)
        milestone_number = ms_numbers[norm["milestone"]]

        # update title/body/milestone
        gh_patch(f"{API}/repos/{OWNER}/{REPO}/issues/{num}", {
            "title": new_title,
            "body": new_body,
            "milestone": milestone_number
        })

        # replace labels exactly
        requests.put(
            f"{API}/repos/{OWNER}/{REPO}/issues/{num}/labels",
            headers=HEADERS,
            json={"labels": norm["labels"]},
            timeout=30
        ).raise_for_status()

        print(f"Updated issue #{num}: {new_title}")

    print("All open issues normalized successfully.")

if __name__ == "__main__":
    main()