# Antegraph Evaluation Semantics

**Spec version:** 1.0 (policy `schema_version` `"1.0"`) · **Evaluator version:** `0.1.0`
**Status:** Normative. The evaluator, diff, search and invariant checker MUST behave as written here. Changing any rule in this document requires an ADR in `docs/decisions/` and a bump of `EVALUATOR_VERSION`.

The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

---

## 1. Closed domains

Every enumeration is closed. A value outside these sets is a validation error.

| Name | Values |
|---|---|
| `Role` | `manager`, `finance`, `security`, `legal`, `procurement`, `it`, `executive` |
| `Department` | `engineering`, `sales`, `marketing`, `finance`, `hr`, `operations`, `legal` |
| `Category` | `software`, `hardware`, `services`, `marketing`, `travel`, `office`, `facilities` |
| `VendorRisk` | `low`, `medium`, `high`, `prohibited`, `unknown` |
| `Currency` | `USD` |
| `EvidenceType` | `security_questionnaire`, `soc2_report`, `quote`, `contract_draft`, `w9` |
| `Decision` | `AUTO_APPROVED`, `NEEDS_APPROVAL`, `BLOCKED` |
| `Severity` | `critical`, `major`, `minor` |

## 2. Purchase requests

A `PurchaseRequest` has exactly these fields. All are required, none may be `null`, and unknown fields are rejected.

| Field | Type | Constraint |
|---|---|---|
| `id` | string | `^[A-Za-z0-9_-]{1,64}$` |
| `requester_id` | string | `^[A-Za-z0-9_-]{1,64}$`, pseudonymous |
| `requester_roles` | array of `Role` | no duplicates, may be empty. Treated as a set |
| `department` | `Department` | |
| `category` | `Category` | |
| `amount_minor` | integer | `0 ≤ amount_minor ≤ 1_000_000_000_000` |
| `currency` | `Currency` | MUST equal the policy's `currency` |
| `vendor_id` | string | `^[A-Za-z0-9_-]{1,64}$`, pseudonymous |
| `vendor_risk` | `VendorRisk` | unknown risk is written `"unknown"`, never omitted |
| `is_new_vendor` | boolean | |
| `requested_at` | string | RFC 3339 timestamp with UTC offset `Z` |

**Amounts** are integer minor units (USD cents): `$12,500.00` is `1250000`. JSON numbers with a fraction or exponent (`1250000.0`, `1.25e6`) and booleans MUST be rejected for `amount_minor`. No type coercion is performed for any field.

**Missing or invalid data.** A request that fails validation is **not evaluated**. Replay counts it under `invalid` and reports its errors. The evaluator never substitutes defaults.

## 3. Policies

```
Policy    := { schema_version: "1.0", policy_id, version, currency, effective_date?, rules: [Rule] }
Rule      := { id, priority, when: Predicate, effect: Effect, explanation }
Predicate := { "all": [Condition, ...] }      -- 1..10 conditions, conjunction
           | { "always": true }
Condition := { field, op, value }
Effect    := { type: "require_approval", role: Role, stage: 1..9 }
           | { type: "require_evidence", evidence: EvidenceType }
           | { type: "block", reason_code: ^[A-Z][A-Z0-9_]{2,63}$ }
```

- `rules`: 1..200 entries. Rule `id`s MUST be unique and match `^[a-z0-9][a-z0-9-]{2,63}$`.
- `priority`: integer `0..10000`.
- `explanation`: 1..500 characters.
- Serialized policy size MUST NOT exceed 64 KiB.

### 3.1 Supported conditions

| `field` | `op` | `value` |
|---|---|---|
| `amount_minor` | `gt`, `gte`, `lt`, `lte`, `eq` | integer in the amount range |
| `category`, `department`, `vendor_risk` | `eq`, `neq` | one enum value |
| `category`, `department`, `vendor_risk` | `in`, `not_in` | 1..20 distinct enum values |
| `is_new_vendor` | `eq` | boolean |

Any other field, operator, value type, effect type or `schema_version` MUST be rejected with `UNSUPPORTED_CONSTRUCT` (or `UNSUPPORTED_SCHEMA_VERSION`). The evaluator MUST NOT ignore a construct it does not understand.

### 3.2 Condition truth

For request `r` and condition `c`, with `x = r[c.field]`:

| op | holds iff |
|---|---|
| `gt` | `x > v` (strict) |
| `gte` | `x ≥ v` |
| `lt` | `x < v` (strict) |
| `lte` | `x ≤ v` |
| `eq` | `x = v` |
| `neq` | `x ≠ v` |
| `in` | `x ∈ v` |
| `not_in` | `x ∉ v` |

So `{"field": "amount_minor", "op": "gt", "value": 1000000}` does **not** hold at `$10,000.00` and **does** hold at `$10,000.01`.

A rule **matches** when `when` is `{"always": true}`, or when every condition in `all` holds.

## 4. Evaluation

`evaluate(policy, request) → EvaluationResult` is a pure function. It MUST NOT read clocks, randomness, environment or IO. Its outcome fields MUST NOT depend on the order of `rules` or on `priority`.

### 4.1 Rule precedence

1. **Every matching rule fires.** There is no first-match and no shadowing.
2. **Block dominates.** If at least one matching rule has a `block` effect:
   - `decision = BLOCKED`
   - `stages = []`
   - `blockers` lists every matching block rule.
   - Matching `require_approval` rules appear in `matched_rules` with `suppressed_by_block = true`.
   - Evidence requirements are still computed and reported (informational).
3. `priority` only orders `matched_rules` and `reasons` for display: descending priority, then ascending rule `id`.

### 4.2 Approval path normalization

Applied to the matching `require_approval` rules when the request is not blocked:

1. **Duplicate approvers.** Each role appears at most once in the path, at the **minimum** declared stage among the rules requiring it. Its provenance is the sorted, de-duplicated list of all those rule IDs.
2. **Grouping.** Roles with the same (minimum) declared stage form one stage. Roles within a stage are parallel and are serialized in ascending role-name order.
3. **Dense renumbering.** Non-empty stages are sorted by declared stage and renumbered `1..k`. Declared stages `{1, 3}` become indices `{1, 2}`.

Example: rules require `finance@3`, `manager@1`, `finance@1`, `legal@3`. Result: stage 1 = `{finance, manager}` and stage 2 = `{legal}`. Finance's provenance contains both finance rule IDs.

### 4.3 Decision

```
BLOCKED          if any block rule matches
NEEDS_APPROVAL   else if the normalized path has ≥ 1 stage
AUTO_APPROVED    otherwise
```

### 4.4 Evidence

`evidence` is the set of `EvidenceType`s from matching `require_evidence` rules, sorted by name, each with its sorted rule IDs.

### 4.5 Result

```
EvaluationResult := {
  evaluator_version, policy_hash, request_hash,
  decision,
  stages:   [ { index, roles: [ { role, rule_ids } ] } ],
  evidence: [ { evidence, rule_ids } ],
  blockers: [ { reason_code, rule_id } ],          -- sorted by rule_id
  matched_rules: [ { rule_id, effect_type, suppressed_by_block } ],
  reasons:  [ string ]                              -- from rule explanations, in display order
}
```

`matched_rules` and `reasons` are explanatory. The **outcome** of a result is `(decision, stages without rule_ids, evidence types, blocker reason codes)`. Two results are **behaviorally equal** iff their outcomes are equal.

## 5. Hashing

`content_hash(x) = "sha256:" + hex(SHA-256(utf8(canonical_json(x))))`, where `canonical_json` serializes the validated document with keys sorted, separators `,` and `:`, no insignificant whitespace, and non-ASCII characters emitted as-is. Array order is preserved. In particular rule order is part of a policy's content, so reordering rules changes the hash but never the behavior.

## 6. Semantic diff

For the same request, compare base result `B` and proposed result `P`. A request's change set contains every applicable class:

| Class | Holds when |
|---|---|
| `DECISION_CHANGED(from, to)` | `B.decision ≠ P.decision` |
| `BLOCK_ADDED(code)` / `BLOCK_REMOVED(code)` | reason code present only in P / only in B |
| `APPROVAL_ADDED(role)` | role in P's path only |
| `APPROVAL_REMOVED(role)` | role in B's path only |
| `APPROVAL_REORDERED(role)` | role in both paths, and for some other role `o` in both paths, `sign(stage_B(role) − stage_B(o)) ≠ sign(stage_P(role) − stage_P(o))` |
| `EVIDENCE_ADDED(type)` / `EVIDENCE_REMOVED(type)` | evidence present only in P / only in B |
| `PROVENANCE_CHANGED` | no class above applies, but the rule IDs behind the outcome differ |
| `UNCHANGED` | no class above applies |

A change in stage *index* alone is not a reorder. Example: B = `manager → finance`, P = `manager → security → finance`. Finance moves from index 2 to 3, but its order relative to `manager` is unchanged. The result is `APPROVAL_ADDED(security)` only.

**Severity** for ranking: `APPROVAL_REMOVED`, `BLOCK_REMOVED` and `DECISION_CHANGED` to a less restrictive decision are **high**. Other outcome classes are **medium**. `PROVENANCE_CHANGED` is **low**. Restrictiveness order: `AUTO_APPROVED < NEEDS_APPROVAL < BLOCKED`.

## 7. Invariants

Invariants are business guarantees owned separately from policies, versioned and hashed the same way.

```
Invariant := { id: ^INV-[A-Z]+-[0-9]{3}$, severity, when: Predicate, assert: Assertion, message }
Assertion := { type: "requires_role", role }
           | { type: "role_before", before: Role, after: Role }
           | { type: "decision_in", decisions: [Decision] }
           | { type: "min_approvals", n: 1..7 }
           | { type: "not_only_requester_roles" }
```

An invariant is **violated** by a result `R` for request `r` iff `when` matches `r` and the assertion fails:

| Assertion | Holds iff |
|---|---|
| `requires_role(x)` | `x` appears in some stage of `R` |
| `role_before(a, b)` | both appear and `stage(a) < stage(b)` |
| `decision_in(ds)` | `R.decision ∈ ds` |
| `min_approvals(n)` | number of distinct roles in `R`'s path `≥ n` |
| `not_only_requester_roles` | `R.decision ≠ NEEDS_APPROVAL`, or at least one path role is not in `r.requester_roles` |

Invariants are checked **independently on each policy's result**. Differing from the base policy is not a violation, and a violation does not require a difference. For a pair (B, P), each violated invariant is classified:

| Class | Violated by B | Violated by P |
|---|---|---|
| `NEW` | no | yes |
| `PRE_EXISTING` | yes | yes |
| `FIXED` | yes | no |

## 8. Counterexamples

A **witness** for (B, P) is a schema-valid `PurchaseRequest` whose change set is not `UNCHANGED`, or which violates an invariant under P. A witness is reported only after **re-verification**: it is round-tripped through request validation and both stored policy versions are re-evaluated from their stored content. The recomputed change set and policy hashes MUST equal the reported ones.

A search report states `complete: true` only if it explored every cell of the input partition (ROADMAP §7.5) within the stated bounds. "No difference, complete" means no valid request in the modelled domain behaves differently **under this evaluator**. It is not a statement about constructs outside this spec. "No difference, incomplete" claims nothing.

## 9. Errors

Errors are returned all at once, as `{code, pointer, message, severity}`, where `pointer` is an RFC 6901 JSON Pointer into the input.

| Code | Severity | Meaning |
|---|---|---|
| `SCHEMA_INVALID` | error | not valid JSON, or wrong shape |
| `TYPE_ERROR` | error | wrong type, e.g. a float amount |
| `MISSING_FIELD` / `UNKNOWN_FIELD` | error | required field absent / extra field present |
| `INVALID_ENUM` | error | value outside a closed domain |
| `OUT_OF_RANGE` | error | numeric or size bound exceeded |
| `DUPLICATE_RULE_ID` | error | two rules share an `id` |
| `UNSUPPORTED_CONSTRUCT` | error | field/op/value/effect not in §3 |
| `UNSUPPORTED_SCHEMA_VERSION` | error | `schema_version` ≠ `"1.0"` |
| `CURRENCY_MISMATCH` | error | request currency ≠ policy currency |
| `UNSATISFIABLE_RULE` | warning | the rule's conditions can never hold together |

A policy with any `error` cannot be submitted. Warnings are shown to the reviewer and do not block submission.
