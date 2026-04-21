# Call Me Maybe — Architecture Contracts

## 1) Purpose

This document defines the canonical architecture contracts for the project before feature implementation begins.  
Its goal is to keep module boundaries stable, interfaces typed, and error handling/logging consistent across the pipeline.

This file is the source of truth for:
- module responsibilities,
- input/output contracts between modules,
- error taxonomy and propagation behavior,
- logging policy (INFO / DEBUG / ERROR),
- deterministic serialization policy.

---

## 2) Module Ownership Map

| Module | Responsibility | Inputs | Outputs | Errors |
|---|---|---|---|---|
| `input_parser` | Parse raw user text into structured intent/entities | `str` | `ParsedInput` | `InputParseError`, `ValidationError` |
| `schema_manager` | Normalize parsed intent into canonical function schema | `ParsedInput` | `NormalizedSchema` | `SchemaError`, `ValidationError` |
| `llm_adapter` | Send normalized context to LLM provider and receive response | `NormalizedSchema` + prompt/context | `RawLLMOutput` | `LLMAdapterError`, `LLMTimeoutError` |
| `output_parser` | Parse raw LLM response into validated function call result | `RawLLMOutput` | `FunctionCallResult` | `OutputParseError`, `ValidationError` |
| `orchestrator` | Coordinate pipeline stages and surface final result | User input + runtime config | `FunctionCallResult` | Any `CallMeMaybeError` subclass |

---

## 3) Interface Contracts (Canonical Types)

Defined in `src/call_me_maybe/models.py`:
- `FunctionParameter`
- `FunctionDefinition`
- `ParsedInput`
- `NormalizedSchema`
- `RawLLMOutput`
- `FunctionCallResult`

Defined in `src/call_me_maybe/errors.py`:
- `CallMeMaybeError` (base)
- `InputParseError`
- `SchemaError`
- `LLMAdapterError`
- `LLMTimeoutError` (inherits from `LLMAdapterError`)
- `OutputParseError`
- `ValidationError`

Contract rule:
- Inter-module communication must use these models and typed exceptions.
- Avoid ad-hoc dictionaries across module boundaries unless immediately validated into a model.

---

## 4) End-to-End Data Flow (ASCII)

```text
User Input (raw text)
        |
        v
+------------------+
|   input_parser   |
+------------------+
        |
        | ParsedInput
        v
+------------------+
|  schema_manager  |
+------------------+
        |
        | NormalizedSchema
        v
+------------------+
|    llm_adapter   |
+------------------+
        |
        | RawLLMOutput
        v
+------------------+
|   output_parser  |
+------------------+
        |
        | FunctionCallResult
        v
  Final pipeline output
```

---

## 5) Error Propagation Policy

1. All domain/application errors must inherit from `CallMeMaybeError`.
2. Each module raises the most specific typed exception available.
3. Do not propagate bare `Exception` across module boundaries.
4. If low-level exceptions occur (network, parsing internals, etc.), wrap them in domain errors:
   - LLM communication failures → `LLMAdapterError`
   - LLM timeout → `LLMTimeoutError`
   - schema invalidity → `SchemaError`
5. User-facing messages should be safe and concise; internal debug detail goes to logs.

---

## 6) Logging Policy

### INFO
Use for major stage transitions and high-level lifecycle events:
- pipeline started/finished,
- input parsed,
- schema normalized,
- LLM call started/completed,
- output parsed.

### DEBUG
Use for deep troubleshooting:
- raw LLM prompt/response payloads,
- intermediate normalization details,
- detailed parser internals.

> DEBUG logs may contain sensitive content and should be disabled in production by default.

### ERROR
Use when failures occur:
- include error class name,
- include pipeline stage,
- include trace/correlation ID if available,
- include safe summary for operators.

---

## 7) Canonical Field Ordering Policy (Deterministic Serialization)

To keep snapshots, logs, and cache keys reproducible, serialized contracts must use a stable field order.

Canonical ordering:
- `FunctionParameter`: `name`, `type`, `required`, `description`, `default`, `enum`
- `FunctionDefinition`: `name`, `description`, `parameters`, `strict`, `returns`
- `FunctionCallResult`: `prompt`, `function_name`, `arguments`, `success`, `error`, `raw_output`

Rules:
1. Preserve declared model field order when serializing.
2. Avoid transformations that randomize dictionary key order before serialization.
3. Test snapshots should assume canonical field order.

---

## 8) Alignment Requirement for Existing Modules

`src/call_me_maybe/schema_manager.py` must:
- import and use models from `models.py`,
- raise typed exceptions from `errors.py`,
- avoid redefining duplicate contracts.

---

## 9) Definition of Contract Completion

Architecture contract layer is considered complete when:
- all module boundaries have declared input/output models,
- all module failure modes map to typed exceptions,
- logging policy is defined and consistent,
- no TODO/TBD placeholders remain in contracts.