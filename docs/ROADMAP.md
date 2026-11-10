# Antegraph — Implementation Roadmap

> *See the consequences before they happen.*
> A predeployment verification and impact-analysis engine for procurement approval policies.

Status: **v1.0 plan** · Created 2026-11-10 · Owner: @GodwinKangor
Tracking: each ticket in §15 is a GitHub issue; each week is a GitHub milestone (M1–M6).

---

## 0. Scope evaluation & smallest vertical slice

**Assessment.** The full proposal (evaluator, diff, replay, counterexamples, invariants, review, audit, UI, simulation) fits about six focused weeks for one developer, but only if the policy language stays small. The biggest risk is not the stack. It is **semantic ambiguity**: what counts as a "changed path"? Those definitions come first (§5), and everything else rests on them.

**Smallest coherent vertical slice (end of Week 1, CLI only, no DB/UI):**

```
fixtures/policies/v1.json, v2.json  ──►  antegraph evaluate  ──►  EvaluationResult JSON
fixtures/requests/golden.json       ──►  antegraph diff      ──►  per-request change classes
```

The slice proves the core claim: the $12,500 software request routes to finance under v1 and not under v2, with rule provenance. Everything later wraps that core in persistence, search, review and UI.

**Key assumptions** (each is a default; see §19 to revisit):

| # | Assumption |
|---|---|
| A1 | Single currency per policy (USD). No FX. Requests in another currency are rejected as `UNSUPPORTED_CURRENCY`. |
| A2 | The policy language is conjunctive predicates over a fixed, enumerated request schema. No OR in MVP (write two rules). No arithmetic, regex, or user code. |
| A3 | Policies output **roles**, not named people. "Self-approval" is modelled through `requester_roles`. |
| A4 | All datasets are synthetic. No real procurement data. |
| A5 | "Accepted" means recorded in Antegraph's audit log. Nothing deploys anywhere. |
| A6 | Replays of ≤10k requests run synchronously in-process. No job queue in MVP. |

**Priority legend:** **P0** = must-have MVP · **P1** = should-have · **P2** = stretch.

---

## 1. Product brief

**Users**
- **Policy author** (procurement ops admin): edits approval rules.
- **Compliance reviewer** (finance / security / audit): decides whether a change is acceptable.
- **Workflow engineer**: tests policy configurations before release and integrates Antegraph into CI.

**Jobs-to-be-done**
1. *When I change a threshold or routing rule, I want to know which purchases will route differently, so I don't silently remove a control.*
2. *When I review someone else's change, I want concrete evidence (examples, counts, violated guarantees), so I can sign off without reverse-engineering JSON.*
3. *When I ship a policy config, I want a reproducible check that fails if a business guarantee is broken.*

**Pain points**
- Text diffs show changed numbers, not changed behavior.
- Historical data only covers what already happened. Edge cases, like a $12,500 request when none occurred, go untested.
- Sign-offs are informal, with no record of what evidence the reviewer saw.

**Success criteria (product-level)**
- For any pair of supported policies, Antegraph either produces a **verified witness** of a behavioral difference or reports **"no difference within the modelled domain"** with stated bounds.
- Every finding links to rule provenance (which rule IDs caused it).
- Every acceptance or rejection is attributable, timestamped, rationale-bearing, and tied to policy hashes and evidence hashes.
- Results are bit-for-bit reproducible from (policy hashes, dataset hash, evaluator version, seed).

**Core differentiator (hypothesis, not a market claim):** Antegraph compares **ordered, multi-stage approval paths with evidence requirements and blocks**, not just allow/deny. It combines replay, exhaustive bounded counterexample search, independent invariants, and a substantive human sign-off in one procurement-shaped workflow.

**Non-goals:** paying or processing invoices or funds; vendor banking data; live system integration; autonomous deployment; fraud detection; contract interpretation; behavior prediction without a validated model; free-form LLM policy execution; claiming formal proof beyond the supported language fragment.

---

## 2. Competitor / building-block matrix

Repository status was checked on **2026-11-10** via the GitHub API and PyPI. Licenses and features change, so re-verify before release (validation tasks below).

| Tool | What it is (verified) | Overlap with Antegraph | Reuse? | Uncertain gaps / validation task |
|---|---|---|---|---|
| **Cedar** — [github.com/cedar-policy/cedar](https://github.com/cedar-policy/cedar) (Apache-2.0, active) | Authorization policy language. The repo includes **`cedar-policy-symcc`**, a symbolic compiler that checks policy-set **equivalence, implication, disjointness, always-allows/denies with counterexamples**, verified in Lean, using cvc5. | **High** on "find a request where two policies differ". This is the closest prior art, and Antegraph must say so. | No (MVP). Cite it as prior art. A later Cedar import adapter is possible. | SymCC reasons about **allow/deny decisions**. Antegraph's object is an **ordered approval path + evidence + blocks**. *Validation:* read the SymCC docs and confirm whether multi-valued/ordered outputs can be encoded. Record the result in ADR-0003. |
| **OPA / Rego** — [github.com/open-policy-agent/opa](https://github.com/open-policy-agent/opa) (Apache-2.0, active) | General-purpose policy engine. Rego can return structured documents (it could compute an approval list). Has `opa test` unit testing. | Medium: could serve as the evaluator. | No. A Go/WASM runtime dependency plus a non-trivial language works against the goals of exhaustive enumeration and small, typed semantics. | *Validation:* confirm OPA has no built-in semantic diff or counterexample generation between policy versions (believed absent; check docs and ecosystem). |
| **Z3** — [github.com/Z3Prover/z3](https://github.com/Z3Prover/z3) (MIT per LICENSE.txt; GitHub reports NOASSERTION; `z3-solver` 5.4.0.0 on PyPI) | SMT solver with Python bindings. | Optional second engine for counterexample search and equivalence. | **P2 stretch.** Used as an independent cross-check of the enumerator. | *Validation:* re-confirm license text and wheel availability for macOS arm64 and Linux CI. |
| **PM4Py** — [github.com/process-intelligence-solutions/pm4py](https://github.com/process-intelligence-solutions/pm4py) (**AGPL-3.0**, active) | Process mining from event logs. | Low. Antegraph replays requests against rules, not discovered process models. | **No.** AGPL is a heavy obligation for an MIT-style portfolio repo, and the feature fit is weak. | None needed. Mention as related work only. |
| **SimPy** — official source [gitlab.com/team-simpy/simpy](https://gitlab.com/team-simpy/simpy) (MIT; PyPI `simpy` 4.1.2). *Note:* the link in the proposal, `github.com/simpx/simpy`, is an unmaintained **fork** (last push 2021). | Discrete-event simulation. | Optional workload simulation. | **P2.** Pure Python and small, so it fits if the stretch goal is reached. | Use PyPI/GitLab as the canonical source. |
| **Closest "policy diff" competitors** | Cedar SymCC (above). AWS Zelkova / IAM Access Analyzer "policy checks" (proprietary). Workflow configuration inside procurement suites (Zip, Coupa, etc.) is not inspectable. | Unknown. | — | **Pending:** 1–2 h desk research on whether procurement-orchestration products offer "preview impact of rule change". Record findings in `docs/research/competitors.md` with links. **No novelty claims until done.** |

**Build-vs-buy rationale.** Antegraph builds its own evaluator for four reasons. (1) The language is deliberately tiny (≈200 LOC evaluator). (2) Exhaustive bounded search needs a **finite partition of the input space**, which is easy to derive from our own AST and impractical from Rego. (3) Python keeps the stack single-language for the core. (4) Tests can encode exact semantics. It buys pydantic (validation), FastAPI (HTTP), SQLAlchemy/Alembic (persistence), Hypothesis (property tests), and optionally z3-solver and SimPy.

---

## 3. End-to-end user journeys

### 3.1 Policy author: Priya (procurement ops)
**Happy path**
1. Opens *Policies → acme-procurement*, sees active `v1` (hash `3f9a…`).
2. Clicks **New draft from v1** and edits `finance-software-threshold` from `1000000` → `1500000`.
3. Clicks **Validate**: schema OK, no warnings.
4. Clicks **Submit for review**. The draft is frozen into immutable `v2` with a content hash. Audit event `policy_version.created`.
5. Clicks **Run analysis** (replay on `synthetic-2026-11-seed42`, counterexample search, invariant check), then gets a review link to send to the reviewer.

**Failure paths**
- Invalid JSON or unknown field `amount_gt_minor` → `400 SCHEMA_INVALID` with a JSON pointer (`/rules/1/when/all/0/field`). The draft is saved but cannot be submitted.
- `amount_minor` value given as `15000.00` (float) → `TYPE_ERROR: amounts must be integer minor units`.
- Duplicate rule IDs → `DUPLICATE_RULE_ID`.
- A rule that can never match (e.g. `amount gt 5` AND `amount lt 3`) → **warning** `UNSATISFIABLE_RULE` (submission allowed, shown to the reviewer).
- Author tries to approve their own version → `403 SELF_REVIEW_FORBIDDEN`.

### 3.2 Compliance reviewer: Marcus (finance controls)
**Happy path**
1. Opens the review workspace for `v2` vs `v1`.
2. **Rule changes** tab: one modified rule, `finance-software-threshold`, `gt 1000000 → gt 1500000` (structural diff, not text).
3. **Replay** tab: `N` of `M` historical requests changed (actual numbers come from the run), all classified `APPROVAL_REMOVED(finance)`. He opens one and sees the side-by-side paths with provenance.
4. **Counterexamples** tab: a verified witness, a $12,500.00 software request. v1 path `manager → finance`, v2 path `manager`. Search reports *complete within modelled domain*.
5. **Invariants** tab: `INV-FIN-001` (software > $10,000 must include finance) is **newly violated** by v2.
6. Clicks **Reject** with the rationale "Finance threshold is governed by memo FC-7; raise requires CFO sign-off." The decision is recorded with reviewer, time, policy hashes, and evidence hash.

**Failure paths**
- Analysis runs are stale (policy or dataset changed since the run) → decision buttons disabled until re-run.
- Rationale shorter than 20 characters → validation error.
- Reviewer tries to **Accept** while critical invariant violations exist → must tick "I acknowledge N critical invariant violations" (recorded). This is an override, not a block, because a human decides.

### 3.3 Workflow engineer: Lin
**Happy path:** `antegraph check --base v1.json --proposed v2.json --invariants default.json --dataset ds.jsonl --format json` → exit code `0` if no new critical violations, `2` if any, `1` on input errors. The result JSON includes all hashes. Runs in CI against a policy-config repo.

**Failure paths:** unsupported `schema_version` → exit `1`, `UNSUPPORTED_SCHEMA_VERSION`. The search exceeds its bound → result marked `"complete": false` with the reason. CI can be configured to fail on incompleteness.

---

## 4. MVP scope & acceptance criteria

| ID | Feature | Input | Output | Depends | Definition of done (testable) | Pri |
|---|---|---|---|---|---|---|
| F1 | Request & policy schema + validation | JSON | typed objects or error list with codes + JSON pointers | — | All negative fixtures in `fixtures/invalid/` produce the expected error codes. Floats are rejected for amounts. | P0 |
| F2 | Canonical hashing | policy / request / invariant-set JSON | SHA-256 hex | F1 | Key order and whitespace don't change the hash. Any semantic change does. Hypothesis test. | P0 |
| F3 | Deterministic evaluator | policy + request | `EvaluationResult` | F1 | 12 golden cases (§12) pass. Shuffled rule order gives an identical result (property test). | P0 |
| F4 | Semantic diff | two results | `ChangeSet` with classes | F3 | Every class in §5.9 has at least one fixture. Identical policies give `UNCHANGED` for 10k random requests. | P0 |
| F5 | Synthetic dataset generator | seed, n, profile | JSONL + manifest (hash) | F1 | Same seed gives a byte-identical file. Includes all boundary scenarios. | P0 |
| F6 | Historical replay | 2 policies + dataset | `ReplayRun` summary + per-request diffs | F4, F5 | Counts equal brute-force recomputation. Labeled scenarios reach recall = 1.0. | P0 |
| F7 | Invariant checker | invariant set + request + result | violations, classified new/pre-existing/fixed | F3 | Fixture invariants flag the expected golden cases only. | P0 |
| F8 | Bounded counterexample search | 2 policies (+ invariants) | verified witnesses + completeness statement | F3, F4, F7 | Finds the $12,500 witness for v1→v2. Reports "no difference" for 5 known-equivalent pairs. Each witness is re-verified. | P0 |
| F9 | Version store (DB) | drafts / submits | immutable versions with hash | F2 | `UPDATE` on `policy_versions` fails at the DB level. Re-submitting identical content returns the existing version. | P0 |
| F10 | REST API | HTTP | JSON | F3–F9 | Integration tests cover each endpoint in §8. OpenAPI published. | P0 |
| F11 | Review decision + audit log | decision, rationale, evidence run IDs | `ReviewDecision`, `AuditEvent` | F9, F10 | Author ≠ reviewer is enforced. Audit hash chain verifies. Append-only enforced by trigger. | P0 |
| F12 | UI: review workspace | browser | pages in §9 | F10 | Playwright E2E runs the demo script end-to-end. | P0 |
| F13 | CLI `check` with exit codes | files | JSON + exit code | F6–F8 | Exit codes tested. | P1 |
| F14 | Rule-level structural diff | 2 policies | added / removed / modified rules | F1 | Fixture shows exactly one modified field for v1→v2. | P1 |
| F15 | Benchmarks | n ∈ {100, 1k, 5k, 10k} | report with hardware | F6 | `make bench` writes `bench/results/*.json`. Numbers are real. | P1 |
| F16 | Export report (JSON/CSV) | run IDs | file | F6–F8 | Round-trip test. | P2 |
| F17 | Z3 cross-check | 2 policies | SAT/UNSAT + model | F8 | Agrees with the enumerator on all pair fixtures. | P2 |
| F18 | SimPy workload simulation | path counts + assumptions | distributions with assumption labels | F6 | M/M/1 sanity test within tolerance. UI labels it "Simulation". | P2 |
| F19 | NL → draft rule assistant | prose | suggested JSON draft (never auto-submitted) | F1 | Output always goes through F1 + human edit. | P2 (post-MVP) |

**Cut lines**
- **4-week cut:** F1–F12 with a minimal UI (review workspace only, JSON textarea editor, no rule-table editor). F13 if time allows. No F15 report polish, F16–F19.
- **6-week cut:** F1–F15 complete and polished, plus one of F16/F17/F18 (recommended: **F17 Z3 cross-check**, because it strengthens the correctness story more than simulation does).
- **Rule if time is short:** drop P2, then F14 polish, then UI niceties. **Never cut** F3, F8 (with witness verification), F7, F11.

---

## 5. Domain model & precise semantics

Normative copy lives in `docs/SEMANTICS.md` (ticket #2). This section is the source for it.

### 5.1 Enumerations (closed sets, versioned with `schema_version`)
```
Role        = manager | finance | security | legal | procurement | it | executive
Department  = engineering | sales | marketing | finance | hr | operations | legal
Category    = software | hardware | services | marketing | travel | office | facilities
VendorRisk  = low | medium | high | prohibited | unknown
Currency    = USD                      # A1
Decision    = AUTO_APPROVED | NEEDS_APPROVAL | BLOCKED
EvidenceType= security_questionnaire | soc2_report | quote | contract_draft | w9
Severity    = critical | major | minor
```

### 5.2 PurchaseRequest
| Field | Type | Constraints |
|---|---|---|
| `id` | str | `^[A-Za-z0-9_-]{1,64}$`, unique within dataset |
| `requester_id` | str | pseudonymous (`emp_0042`), no names or emails |
| `requester_roles` | set[Role] | may be empty. Used only by invariants (SoD) |
| `department` | Department | required |
| `category` | Category | required |
| `amount_minor` | int | `0 ≤ amount_minor ≤ 10^12` (≤ $10B). **Floats rejected.** |
| `currency` | Currency | must equal the policy currency |
| `vendor_id` | str | pseudonymous |
| `vendor_risk` | VendorRisk | required. Use `unknown` explicitly, never null |
| `is_new_vendor` | bool | required |
| `requested_at` | datetime | RFC 3339 UTC. Not used by MVP predicates |

**Missing data:** every field is required. A missing or null field is a **validation error**, never a silent default, and the request is excluded from evaluation and reported (`replay.invalid_requests`). Unknown extra fields are rejected (`extra="forbid"`).

### 5.3 PolicyVersion
`id (uuid)`, `policy_id`, `version_label` (e.g. `v2`), `schema_version` (`"1.0"`), `currency`, `effective_date` (informational), `author_id`, `parent_version_id?`, `rules: list[Rule]`, `content_hash` (SHA-256 of canonical content, §6.3), `created_at`. **Immutable** after creation. Edits happen on a separate mutable `PolicyDraft`.

### 5.4 Rule
`id` (`^[a-z0-9][a-z0-9-]{2,63}$`, unique within the policy), `priority` (int 0–10000, informational ordering only, see 5.6), `when: Predicate`, `effect: Effect`, `explanation` (str, 1–500 chars, shown to humans).

**Predicate** = `{"all": [Condition, ...]}` (conjunction, 1–10 conditions). An empty `all` is not allowed; use the explicit `{"always": true}` instead.
**Condition** = `{"field": F, "op": OP, "value": V}` with this type table (anything else gives `UNSUPPORTED_CONSTRUCT`):

| field | allowed ops | value type |
|---|---|---|
| `amount_minor` | `gt gte lt lte eq` | int |
| `category`, `department`, `vendor_risk` | `eq neq in not_in` | enum / list[enum] (1–20, no duplicates) |
| `is_new_vendor` | `eq` | bool |

There are no `requester_id`, `vendor_id` or date predicates in MVP (no unbounded domains, which keeps search exhaustive).

**Effect** (exactly one per rule):
- `{"type": "require_approval", "role": Role, "stage": int 1–9}`
- `{"type": "require_evidence", "evidence": EvidenceType}`
- `{"type": "block", "reason_code": str}`

### 5.5 Threshold semantics
`gt` is strict (`>`), `gte` is `≥`, and so on. All comparisons are on integers. "Above $10,000" written as `gt 1000000` means **$10,000.00 does not match and $10,000.01 does**. The UI always renders thresholds with the operator symbol and both dollar amounts: `> $10,000.00 (1000000¢)`.

### 5.6 Rule precedence & overlap
- **All matching rules fire.** There is no first-match and no shadowing, because approvals accumulate.
- **Block dominates:** if any `block` rule matches, `decision = BLOCKED`, `stages = []`, and `blockers` lists all matching block rules. Matching approval and evidence rules are still listed in `matched_rules` (for explanation), flagged `suppressed_by_block: true`.
- `priority` affects **only presentation order** of reasons (desc priority, then rule id). It never changes the outcome. A property test enforces this.

### 5.7 ApprovalStage, ApprovalPath & normalization
1. Collect `(role, declared_stage, rule_id)` from matching `require_approval` rules.
2. **Duplicate approvers:** a role appearing more than once is kept once, at its **minimum** declared stage. Provenance is the union of rule IDs, sorted.
3. Group by declared stage, sort ascending, drop empty stages, and **renumber densely 1..k** (declared stages 1, 3 become 1, 2).
4. Within a stage, roles are a **set** (parallel approvals), serialized sorted by role name.
5. `ApprovalPath = tuple[ApprovalStage]`, where `ApprovalStage = {index, roles: [ {role, rule_ids[]} ]}`.
6. `decision = BLOCKED` if blockers, else `NEEDS_APPROVAL` if stages are non-empty, else `AUTO_APPROVED`.
7. `evidence` = sorted unique set of required `EvidenceType`, each with its rule IDs.

### 5.8 EvaluationResult
`policy_hash`, `request_hash`, `evaluator_version` (semver constant in code), `decision`, `stages`, `evidence`, `blockers`, `matched_rules` (sorted per 5.6 with `suppressed_by_block`), `reasons` (human-readable strings generated from rule explanations). **Pure function**: no clock, randomness, or IO.

### 5.9 Semantic diff: change classes
Given base result `B` and proposed result `P` for the same request. A request can carry several classes; `UNCHANGED` is used only if no other class applies.

| Class | Condition |
|---|---|
| `DECISION_CHANGED` | `B.decision ≠ P.decision` (with `from`/`to`) |
| `BLOCK_ADDED` / `BLOCK_REMOVED` | blocker reason codes newly present / absent |
| `APPROVAL_ADDED(role)` | role in P's path, not B's |
| `APPROVAL_REMOVED(role)` | role in B's path, not P's |
| `APPROVAL_REORDERED(role)` | role in both, but its **relative order** changed. Formally, for some other common role `r'`, `cmp(stage_B(role), stage_B(r')) ≠ cmp(stage_P(role), stage_P(r'))`. Pure renumbering caused by an added or removed stage is **not** a reorder. |
| `EVIDENCE_ADDED/REMOVED(type)` | evidence set difference |
| `PROVENANCE_CHANGED` | same outcome, different rule IDs (informational, `minor`) |
| `UNCHANGED` | none of the above |

Severity mapping for UI sorting: removals and `BLOCK_REMOVED` are **high**, additions and reorders are **medium**, provenance is **low**.

### 5.10 Invariant
`id`, `severity`, `when: Predicate` (same language as rules, over the request), `assert: Assertion`, `message`. Assertions (over request + result):
- `requires_role(role)`: role appears in some stage.
- `role_before(role_a, role_b)`: both present and `stage(a) < stage(b)`.
- `decision_in([Decision…])`
- `min_approvals(n)`: total distinct roles ≥ n.
- `not_only_requester_roles`: if `decision = NEEDS_APPROVAL`, at least one path role ∉ `requester_roles` (separation of duties / no self-approval).

**Semantics:** invariants are evaluated **independently on each policy's result**. *Differing from the old policy is not a violation*, and *a violation does not require a difference.* Classification per (request, invariant): `NEW` (fails P only), `PRE_EXISTING` (fails both), `FIXED` (fails B only). Invariant sets are versioned and hashed like policies, and owned by compliance, not the policy author.

### 5.11 ReplayRun
`id`, `base_version_id`, `proposed_version_id`, `dataset_id`, `invariant_set_id?`, `evaluator_version`, `status`, `started_at`, `finished_at`, `summary` (`total`, `invalid`, `changed`, `by_class{}`, `by_rule{}`, `invariant{new, pre_existing, fixed}`), `result_hash` (hash over sorted per-request diffs, which makes it reproducible).

### 5.12 Counterexample
`id`, `run_id`, `kind` (`DIFFERENCE` | `INVARIANT_VIOLATION`), `request` (a full, schema-valid PurchaseRequest with `id = "cx-<hash8>"`), `base_result`, `proposed_result`, `change_classes`, `invariant_id?`, `verified: bool` (set only by the independent re-evaluation in §7.6), `region_signature` (which partition cell it represents).

### 5.13 ReviewDecision
`id`, `proposed_version_id`, `base_version_id`, `reviewer_id`, `decision` (`ACCEPT` | `REJECT` | `REQUEST_CHANGES`), `rationale` (20–4000 chars), `acknowledged_violations: list[invariant_id]`, `evidence_run_ids`, `evidence_hash` (hash of {policy hashes, run result_hashes, counterexample ids}), `created_at`. Append-only. The effective status of a version is the latest decision.

### 5.14 AuditEvent
`seq` (bigserial), `id`, `actor_id`, `event_type` (`policy_draft.created`, `policy_version.created`, `run.completed`, `review.decided`, …), `entity_type`, `entity_id`, `payload` (jsonb), `created_at`, `prev_hash`, `event_hash = sha256(prev_hash ‖ canonical(event without hash))`. Append-only and hash-chained (tamper-evident, **not** tamper-proof).

### 5.15 Unsupported constructs
Any field, op, effect type, or `schema_version` not listed is rejected with `UNSUPPORTED_CONSTRUCT` and a pointer. Antegraph never "best-efforts" an unknown construct, because a silently ignored rule would invalidate every guarantee.

---

## 6. Policy DSL / JSON schema

### 6.1 `fixtures/policies/acme_v1.json`
```json
{
  "schema_version": "1.0",
  "policy_id": "acme-procurement",
  "version": "v1",
  "currency": "USD",
  "effective_date": "2026-01-01",
  "rules": [
    {
      "id": "manager-baseline",
      "priority": 100,
      "when": {"all": [{"field": "amount_minor", "op": "gt", "value": 0}]},
      "effect": {"type": "require_approval", "role": "manager", "stage": 1},
      "explanation": "Every non-zero purchase requires the requester's manager."
    },
    {
      "id": "security-new-software-vendor",
      "priority": 300,
      "when": {"all": [
        {"field": "category", "op": "eq", "value": "software"},
        {"field": "is_new_vendor", "op": "eq", "value": true}
      ]},
      "effect": {"type": "require_approval", "role": "security", "stage": 2},
      "explanation": "New software vendors require a security review."
    },
    {
      "id": "finance-software-threshold",
      "priority": 200,
      "when": {"all": [
        {"field": "category", "op": "eq", "value": "software"},
        {"field": "amount_minor", "op": "gt", "value": 1000000}
      ]},
      "effect": {"type": "require_approval", "role": "finance", "stage": 3},
      "explanation": "Software purchases above $10,000.00 require finance approval."
    },
    {
      "id": "legal-large-purchase",
      "priority": 200,
      "when": {"all": [{"field": "amount_minor", "op": "gte", "value": 5000000}]},
      "effect": {"type": "require_approval", "role": "legal", "stage": 3},
      "explanation": "Purchases of $50,000.00 or more require legal review."
    },
    {
      "id": "high-risk-questionnaire",
      "priority": 150,
      "when": {"all": [{"field": "vendor_risk", "op": "in", "value": ["high", "unknown"]}]},
      "effect": {"type": "require_evidence", "evidence": "security_questionnaire"},
      "explanation": "High- or unknown-risk vendors must provide a security questionnaire."
    },
    {
      "id": "block-prohibited-vendor",
      "priority": 1000,
      "when": {"all": [{"field": "vendor_risk", "op": "eq", "value": "prohibited"}]},
      "effect": {"type": "block", "reason_code": "VENDOR_PROHIBITED"},
      "explanation": "Purchases from prohibited vendors are blocked."
    }
  ]
}
```

### 6.2 `fixtures/policies/acme_v2.json`
Identical except `"version": "v2"`, `"effective_date": "2026-12-01"`, and:
```json
{
  "id": "finance-software-threshold",
  "priority": 200,
  "when": {"all": [
    {"field": "category", "op": "eq", "value": "software"},
    {"field": "amount_minor", "op": "gt", "value": 1500000}
  ]},
  "effect": {"type": "require_approval", "role": "finance", "stage": 3},
  "explanation": "Software purchases above $15,000.00 require finance approval."
}
```
Additional fixtures: `acme_v2_reorder.json` (security moved to stage 4, after finance), `acme_v1_shuffled.json` (same rules in a different order. Rule order is content, so the **hash differs**, but behavior is identical. This fixture tests that "different hash, same behavior" is reported as *no behavioral difference*), and `acme_v1_dup_finance.json` (finance required at stages 1 and 3).

### 6.3 `fixtures/invariants/acme_guarantees.json`
```json
{
  "schema_version": "1.0",
  "invariant_set_id": "acme-guarantees",
  "version": "inv-1",
  "invariants": [
    {"id": "INV-FIN-001", "severity": "critical",
     "when": {"all": [{"field": "category", "op": "eq", "value": "software"},
                      {"field": "amount_minor", "op": "gt", "value": 1000000}]},
     "assert": {"type": "requires_role", "role": "finance"},
     "message": "Software purchases above $10,000.00 must include finance approval (fictional control FC-7)."},
    {"id": "INV-SEC-001", "severity": "critical",
     "when": {"all": [{"field": "category", "op": "eq", "value": "software"},
                      {"field": "is_new_vendor", "op": "eq", "value": true}]},
     "assert": {"type": "requires_role", "role": "security"},
     "message": "New software vendors must be reviewed by security."},
    {"id": "INV-SOD-001", "severity": "major",
     "when": {"always": true},
     "assert": {"type": "not_only_requester_roles"},
     "message": "At least one approver role must not be held by the requester."},
    {"id": "INV-BLK-001", "severity": "critical",
     "when": {"all": [{"field": "vendor_risk", "op": "eq", "value": "prohibited"}]},
     "assert": {"type": "decision_in", "decisions": ["BLOCKED"]},
     "message": "Prohibited vendors must always be blocked."}
  ]
}
```

### 6.4 Validation, versioning, hashing, errors
- **Validation:** pydantic v2 models with `extra="forbid"` and `strict=True` (no int↔float/str coercion), plus a semantic pass for duplicate IDs, the field/op/value type table, enum membership, and unsatisfiable conjunctions (warning). JSON Schema is **generated** from the pydantic models (`antegraph schema > docs/policy.schema.json`) for editor support. One source of truth.
- **Error shape:** `{"code": "UNSUPPORTED_CONSTRUCT", "pointer": "/rules/2/when/all/0/op", "message": "...", "severity": "error|warning"}`. All errors are returned at once, not just the first.
- **Canonical hash:** `sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))` over the validated model dump. Floats are impossible by construction. Hashes are prefixed by algorithm in storage (`sha256:…`). Lists keep order (rule order is content, even though it does not affect behavior).
- **Versioning:** drafts are mutable. `submit` validates, freezes and hashes. If content identical to an existing version is submitted, the existing version is returned (idempotent). `schema_version` is checked against a supported set. Migrations between schema versions are explicit functions with tests.
- **No arbitrary code execution:** policies are **data**, interpreted by a closed `match` over known ops. No `eval`, no templating, no regex, no user-defined functions, and size limits (≤200 rules, ≤64 KB). An LLM may later *suggest* JSON, but it goes through the same validator and a human edit and submit step.
- **Human verification of changes:** the reviewer sees (1) a **rule-level structural diff** (`modified: finance-software-threshold.when.all[1].value 1000000 → 1500000`, rendered as "> $10,000.00 → > $15,000.00"), (2) behavioral evidence (replay, witnesses, invariants), and (3) the hashes they are signing against.

---

## 7. Algorithms

Notation: R = rules, C = conditions per rule (≤10), N = requests, F = fields, K = partition cells.

### 7.1 Rule evaluation — O(R·C + R log R)
```
def evaluate(policy, req) -> EvaluationResult:
    matched = [r for r in policy.rules if all(holds(c, req) for c in r.when.all)]
    blocks   = [r for r in matched if r.effect.type == "block"]
    approvals= [r for r in matched if r.effect.type == "require_approval"]
    evidence = [r for r in matched if r.effect.type == "require_evidence"]
    if blocks:
        return Result(decision=BLOCKED, stages=[], blockers=sorted_reasons(blocks),
                      evidence=normalize_evidence(evidence),
                      matched=annotate(matched, suppressed=approvals))
    stages = normalize_path(approvals)
    decision = NEEDS_APPROVAL if stages else AUTO_APPROVED
    return Result(decision, stages, evidence=normalize_evidence(evidence), matched=...)

def holds(c, req):           # closed match: no other ops exist
    v = getattr(req, c.field)
    match c.op: case "gt": v >  c.value ; case "gte": v >= c.value ; ...
                case "in": v in c.value ; case "not_in": v not in c.value ; ...
```
Open question resolved: evidence is still reported for blocked requests. A blocked request remains blocked, and the evidence list is informational.

### 7.2 Path normalization — O(A log A), A = matched approvals
```
def normalize_path(approvals):
    best = {}                                  # role -> (min_stage, set(rule_ids))
    for r in approvals:
        s, ids = best.get(r.role, (inf, set()))
        best[r.role] = (min(s, r.stage), ids | {r.id})
    by_stage = group(best, key=min_stage)      # declared stage -> roles
    return [Stage(index=i+1, roles=sorted(roles_with_provenance))
            for i, (_, roles) in enumerate(sorted(by_stage.items()))]
```

### 7.3 Semantic diff — O(S²) worst case, S = distinct roles (≤7)
```
def diff(B, P) -> ChangeSet:
    classes = []
    if B.decision != P.decision: classes.append(DECISION_CHANGED(B.decision, P.decision))
    bset, pset = blocker_codes(B), blocker_codes(P)   # BLOCK_ADDED / BLOCK_REMOVED
    sB, sP = stage_of(B), stage_of(P)                 # role -> index
    for r in sP.keys() - sB.keys(): APPROVAL_ADDED(r)
    for r in sB.keys() - sP.keys(): APPROVAL_REMOVED(r)
    common = sB.keys() & sP.keys()
    for r in common:
        if any(sign(sB[r]-sB[o]) != sign(sP[r]-sP[o]) for o in common if o != r):
            APPROVAL_REORDERED(r)
    evidence set diffs; provenance diff if no outcome class
    return ChangeSet(classes or [UNCHANGED])
```

### 7.4 Historical replay — O(N·R·C) time, O(N) memory (streamed, O(changed) if only changes are stored)
```
def replay(base, proposed, dataset, invariants=None):
    summary = Counter()
    for req in dataset.stream():                 # validated; invalid -> summary.invalid
        b, p = evaluate(base, req), evaluate(proposed, req)
        cs = diff(b, p); inv = classify_invariants(invariants, req, b, p)
        summary.update(cs, inv); yield RequestDiff(req.id, b, p, cs, inv)
    result_hash = sha256 over sorted(request_id, canonical(cs), inv)
```
Optimisation, only if benchmarks demand it: memoize per-policy evaluation by the request's **region signature** (§7.5). Measure before adding.

### 7.5 Counterexample search: bounded exhaustive enumeration (MVP)
**Key observation.** Every atomic predicate is `field op constant`, over integer or finite enum domains. So the input space splits into finitely many **cells**, and within a cell every predicate (in both policies *and* the invariants) has the same truth value. Every evaluation outcome is then constant per cell, apart from `requester_roles`, which is handled separately.

```
def build_partition(policies, invariants, bounds):
    consts = sorted({c.value for c in all_conditions if c.field == "amount_minor"})
    # cells: every threshold point t, plus one interior point of each open interval
    amounts = {0, bounds.max_amount}
    for t in consts: amounts |= {t-1, t, t+1} ∩ [0, max]
    for (lo, hi) in adjacent_pairs(sorted(amounts)):
        if hi - lo > 1: amounts.add(round_nice((lo + hi) // 2))  # "human" midpoint, e.g. 1250000
    enums: if a field is referenced anywhere -> full enum, else a single fixed representative
    bools: {False, True} if referenced, else {False}
    requester_roles: all subsets of R_path, the roles any policy can output (|R_path| ≤ 7 -> ≤128),
                     only if an invariant uses not_only_requester_roles, else {∅}
    return product(...)          # K = |amounts|·|cat|·|dept|·|risk|·|bool|·|roles|

def search(base, proposed, invariants, bounds):
    cells = build_partition(...)
    if len(cells) > bounds.max_cells: return Incomplete(reason="CELL_LIMIT", explored=...)
    witnesses = defaultdict(list)
    for cell in cells:                          # deterministic order
        req = materialize(cell)                 # schema-valid PurchaseRequest, id = cx-<hash8>
        b, p = evaluate(base, req), evaluate(proposed, req)
        cs = diff(b, p)
        if cs != UNCHANGED: witnesses[signature(cs)].append(req)
        for v in violations(invariants, req, p): witnesses[("INV", v.id)].append(req)
    chosen = [pick_representative(ws) for ws in witnesses.values()]   # prefer midpoints, then smallest amount
    return Result(complete=True, cells=K, witnesses=[verify(w) for w in chosen])
```
**Completeness argument (for the supported fragment).** For an integer field with thresholds `t₁<…<t_m`, each predicate `x op t_i` is constant on each of the sets `{t_i}` and the open integer intervals between consecutive thresholds (plus below t₁ and above t_m). The construction samples every one of these, because `t-1` and `t+1` land inside the adjacent intervals and midpoints add a "nicer" representative. Enum and bool fields that are referenced are enumerated fully, and unreferenced fields cannot affect any predicate. `not_only_requester_roles` depends only on `requester_roles ∩ R_path`, and all subsets of `R_path` are enumerated. Therefore **if no cell differs, no valid request within `[0, max_amount]` differs.** This is equivalence *relative to* (a) this evaluator's implementation, (b) the closed schema, and (c) the amount bound. It is checked empirically by a metamorphic test (§12) and optionally cross-checked by Z3 (§7.7).

Complexity: K ≤ (3m+2m+2)·7·7·5·2·128 in the worst case. For the demo policies, K is in the low tens of thousands, a few seconds in pure Python at most (measure in #35). `max_cells` defaults to 2,000,000. If it is exceeded, the result is marked `complete: false` and is never presented as equivalence.

**Witness vs proof.**
- A **witness** is a concrete request that was re-evaluated and differs. It is *always* trustworthy as long as the evaluator is the reference semantics.
- **"No difference found, complete=true"** is a proof *only within the modelled fragment and bounds*, and only as reliable as the partition code.
- **"No difference found, complete=false"** proves nothing. The UI says "Search incomplete: no difference found in X of Y cells."

### 7.6 Witness validation (independent re-evaluation)
```
def verify(w):
    req = PurchaseRequest.model_validate_json(canonical(w.request))   # round-trip through the schema
    b, p = evaluate(load(base_hash), req), evaluate(load(proposed_hash), req)  # fresh load from the stored version
    assert diff(b, p) == w.change_classes and b.policy_hash == base_hash and p.policy_hash == proposed_hash
    w.verified = True
```
The API also exposes `POST /api/evaluate` so a reviewer can re-run any witness by hand. The UI has a **Re-verify** button.

### 7.7 Z3 backend (P2): symbolic cross-check
Encode `amount: Int` with `0 ≤ amount ≤ max`, each enum as a Z3 `EnumSort`, and `new: Bool`. For each policy and role: `req_role_X(policy) = OR(match(rule) for rules requiring X)`, `stage_X = min over matching rules` (encoded with nested `If`s), `blocked = OR(block rules)`. Assert `blocked_B ≠ blocked_P ∨ ∃X: req_X_B ≠ req_X_P ∨ (req_X_B ∧ req_X_P ∧ order-differs…)`. `sat` returns a model, which is materialized and **verified by the Python evaluator** (§7.6). `unsat` must agree with the enumerator's "complete, no difference". Disagreement is a bug and fails CI. Value: a second, independent implementation of the semantics. Cost: encoding reorder semantics is the fiddly part, so scope it to decision plus role membership first.

### 7.8 Invariant checking — O(I·C) per request
```
def violations(invset, req, result):
    return [inv for inv in invset if pred_holds(inv.when, req) and not assertion_holds(inv.assert, req, result)]
def classify(invset, req, B, P):
    vb, vp = ids(violations(.., B)), ids(violations(.., P))
    return NEW=vp-vb, PRE_EXISTING=vp&vb, FIXED=vb-vp
```
It runs in three places: replay (historical), counterexample search (cells, finding violating witnesses even with no B/P difference), and single-request evaluate.

### 7.9 Workload simulation (P2): clearly labeled forecast
Inputs: per-role arrival rate λ_r, **derived from replay counts** of requests whose path contains role r ÷ dataset time span. Reviewer count c_r and service-time distribution are **user-declared assumptions**. Model each role as a SimPy `Resource(capacity=c_r)`, with requests flowing through stages sequentially and roles within a stage in parallel. Run `n_reps=30` seeded replications and report median and p90 wait **with a sensitivity sweep** (service time ×0.5, ×1, ×2). Validation: an M/M/1 configuration matches the analytic `Wq = ρ/(μ−λ)` within 5% over long runs. The UI banner says "Simulated estimate under the assumptions below. Not an observation."

---

## 8. System architecture

### 8.1 Diagram (modular monolith)
```
┌───────────────────────── frontend/ (React + TS + Vite) ─────────────────────────┐
│ PoliciesPage · VersionTimeline · DraftEditor · ReviewWorkspace{Summary,Rules,   │
│ Replay,Counterexamples,Invariants,Decision} · AuditPage                         │
└───────────────▲─────────────────────────────────────────────────────────────────┘
                │ JSON over HTTP (OpenAPI-generated TS types)
┌───────────────┴──────────── backend/src/antegraph ──────────────────────────────┐
│ api/        FastAPI routers, auth dependency, error mapping (no business logic) │
│ services/   orchestration: submit_draft, run_analysis, decide_review (tx + audit)│
│ store/      SQLAlchemy models, repositories, Alembic migrations                 │
│ ── pure core (no IO, no DB, no clock) ──────────────────────────────────────────│
│ domain/     pydantic models, enums, money formatting                            │
│ dsl/        validation, semantic checks, canonical hashing, rule-level diff     │
│ engine/     evaluator, path normalization                                       │
│ analysis/   diff, replay, partition, counterexample, invariants, (z3_backend)   │
│ data/       synthetic generator                     sim/ (SimPy, optional)      │
│ cli.py      Typer CLI over the pure core (evaluate/diff/replay/search/check)    │
└───────────────┬─────────────────────────────────────────────────────────────────┘
                │ SQLAlchemy 2.x (psycopg 3)
           PostgreSQL 16  (append-only triggers on versions/decisions/audit)
```
Rule: **`api` → `services` → (`store`, core)**. The core never imports `store` or `api`; `import-linter` enforces this in CI.

### 8.2 Dependencies (each justified)
| Dep | Why |
|---|---|
| Python 3.12 | Current; the user has 3.12.7 |
| pydantic v2 | Strict validation, JSON Schema generation, fast |
| FastAPI + uvicorn | Typed endpoints built on pydantic, automatic OpenAPI |
| SQLAlchemy 2 + Alembic + psycopg 3 | Standard, typed ORM, explicit migrations |
| PostgreSQL 16 | jsonb, triggers for append-only, arrays. Run via Docker Compose |
| Typer | CLI with little code (engineer persona, demo before UI exists) |
| pytest, Hypothesis, pytest-cov | Unit, property and metamorphic tests |
| ruff, mypy (strict on core), import-linter | Quality gates |
| uv | Fast, reproducible lockfile (`uv.lock`). pip still works |
| React 18 + TS + Vite | Requested stack, fast dev server |
| TanStack Query, React Router | Server state and routing. No Redux needed |
| openapi-typescript | Types generated from the backend: one source of truth |
| Vitest + Testing Library, Playwright | Component tests and E2E demo test |
| *(P2)* z3-solver, simpy | Only with their stretch tickets |

Not used, deliberately: Celery/Redis (no async need ≤10k), an LLM SDK (core must work without one), OPA/Cedar runtime (§2).

### 8.3 Database schema (DDL sketch)
```sql
create table users (id uuid primary key, username text unique not null,
  display_name text not null, app_role text not null check (app_role in ('author','reviewer','admin')),
  created_at timestamptz not null default now());

create table policies (id uuid primary key, slug text unique not null, name text not null,
  created_at timestamptz not null default now());

create table policy_drafts (id uuid primary key, policy_id uuid not null references policies,
  base_version_id uuid references policy_versions, author_id uuid not null references users,
  content jsonb not null, updated_at timestamptz not null default now());

create table policy_versions (id uuid primary key, policy_id uuid not null references policies,
  version_label text not null, schema_version text not null, content jsonb not null,
  content_hash text not null, parent_version_id uuid references policy_versions,
  author_id uuid not null references users, created_at timestamptz not null default now(),
  unique (policy_id, content_hash), unique (policy_id, version_label));
create index on policy_versions (policy_id, created_at desc);

create table invariant_sets (id uuid primary key, label text not null, content jsonb not null,
  content_hash text unique not null, created_at timestamptz not null default now());

create table datasets (id uuid primary key, label text unique not null, generator_version text not null,
  seed bigint not null, profile text not null, request_count int not null,
  content_hash text not null, created_at timestamptz not null default now());
create table purchase_requests (dataset_id uuid references datasets, id text,
  payload jsonb not null, request_hash text not null, primary key (dataset_id, id));

create table analysis_runs (id uuid primary key, kind text not null check (kind in ('replay','search')),
  base_version_id uuid not null references policy_versions, proposed_version_id uuid not null references policy_versions,
  dataset_id uuid references datasets, invariant_set_id uuid references invariant_sets,
  evaluator_version text not null, params jsonb not null, status text not null,
  summary jsonb, result_hash text, started_at timestamptz not null, finished_at timestamptz);
create index on analysis_runs (proposed_version_id, base_version_id, started_at desc);

create table replay_results (run_id uuid references analysis_runs, request_id text,
  change_classes text[] not null, invariant_new text[] not null default '{}',
  base_result jsonb not null, proposed_result jsonb not null, primary key (run_id, request_id));
create index on replay_results using gin (change_classes);

create table counterexamples (id uuid primary key, run_id uuid not null references analysis_runs,
  kind text not null, request jsonb not null, base_result jsonb not null, proposed_result jsonb not null,
  change_classes text[] not null, invariant_id text, region_signature text not null, verified boolean not null);

create table review_decisions (id uuid primary key, proposed_version_id uuid not null references policy_versions,
  base_version_id uuid not null references policy_versions, reviewer_id uuid not null references users,
  decision text not null check (decision in ('ACCEPT','REJECT','REQUEST_CHANGES')),
  rationale text not null check (char_length(rationale) between 20 and 4000),
  acknowledged_violations text[] not null default '{}', evidence_run_ids uuid[] not null,
  evidence_hash text not null, created_at timestamptz not null default now());
create index on review_decisions (proposed_version_id, created_at desc);

create table audit_events (seq bigserial primary key, id uuid unique not null, actor_id uuid references users,
  event_type text not null, entity_type text not null, entity_id text not null, payload jsonb not null,
  created_at timestamptz not null default now(), prev_hash text not null, event_hash text not null);
create index on audit_events (entity_type, entity_id, seq);

-- append-only enforcement
create function forbid_mutation() returns trigger language plpgsql as
  $$ begin raise exception 'append-only table: %', tg_table_name; end $$;
create trigger t_versions_ro  before update or delete on policy_versions  for each row execute function forbid_mutation();
create trigger t_decisions_ro before update or delete on review_decisions for each row execute function forbid_mutation();
create trigger t_audit_ro     before update or delete on audit_events     for each row execute function forbid_mutation();
```
(Also apply the trigger to `invariant_sets`, `datasets`, `purchase_requests`, `analysis_runs` once finished.)

### 8.4 REST endpoints (prefix `/api`, JSON, errors `{"error": {code, message, details[]}}`)
| Method & path | Purpose |
|---|---|
| `GET /health`, `GET /meta` | liveness. `{evaluator_version, schema_versions, git_sha}` |
| `GET/POST /policies` | list / create policy container |
| `GET /policies/{id}/versions` | version timeline with latest review status |
| `POST /policies/{id}/drafts` | new draft (optionally from `base_version_id`) |
| `PUT /drafts/{id}` | update draft content |
| `POST /drafts/{id}/validate` | `{valid, errors[], warnings[]}` |
| `POST /drafts/{id}/submit` | freeze to version → `201 {version}` |
| `GET /versions/{id}` | content + hash |
| `GET /versions/{a}/rule-diff/{b}` | structural rule diff (F14) |
| `POST /evaluate` | `{version_id, request}` → EvaluationResult |
| `POST /compare` | `{base_version_id, proposed_version_id, request}` → both results + ChangeSet |
| `GET /datasets`, `POST /datasets` | list / generate `{seed, n, profile}` |
| `POST /runs` | `{kind: replay\|search, base_version_id, proposed_version_id, dataset_id?, invariant_set_id?, params}` → run |
| `GET /runs/{id}` | status + summary |
| `GET /runs/{id}/results?class=APPROVAL_REMOVED&role=finance&limit=50&cursor=` | paged per-request diffs |
| `GET /runs/{id}/counterexamples` | witnesses |
| `POST /reviews` | decision (reviewer only) |
| `GET /versions/{id}/reviews` | decisions |
| `GET /audit?entity_id=&limit=` | events + `chain_valid` |

Example:
```http
POST /api/compare
{"base_version_id": "7c1e…", "proposed_version_id": "a94b…",
 "request": {"id": "manual-1", "requester_id": "emp_0042", "requester_roles": [],
   "department": "engineering", "category": "software", "amount_minor": 1250000,
   "currency": "USD", "vendor_id": "ven_0007", "vendor_risk": "low",
   "is_new_vendor": false, "requested_at": "2026-11-10T15:00:00Z"}}
```
```json
{"base":     {"decision": "NEEDS_APPROVAL", "policy_hash": "sha256:3f9a…",
              "stages": [{"index": 1, "roles": [{"role": "manager", "rule_ids": ["manager-baseline"]}]},
                         {"index": 2, "roles": [{"role": "finance", "rule_ids": ["finance-software-threshold"]}]}],
              "evidence": [], "blockers": []},
 "proposed": {"decision": "NEEDS_APPROVAL", "policy_hash": "sha256:b21c…",
              "stages": [{"index": 1, "roles": [{"role": "manager", "rule_ids": ["manager-baseline"]}]}],
              "evidence": [], "blockers": []},
 "changes":  [{"class": "APPROVAL_REMOVED", "role": "finance", "severity": "high",
               "provenance": {"base_rule_ids": ["finance-software-threshold"], "proposed_rule_ids": []}}]}
```
```http
POST /api/reviews
{"proposed_version_id": "a94b…", "base_version_id": "7c1e…", "decision": "REJECT",
 "rationale": "Finance threshold is set by control FC-7; changes need CFO sign-off.",
 "evidence_run_ids": ["r-replay-…", "r-search-…"], "acknowledged_violations": []}
→ 201 {"id": "…", "evidence_hash": "sha256:…", "created_at": "…"}
→ 403 {"error": {"code": "SELF_REVIEW_FORBIDDEN", …}} | 409 {"error": {"code": "STALE_EVIDENCE", …}}
```

### 8.5 Async jobs
Not in MVP. Replay of 10k and search run synchronously. If a benchmark shows more than about 3 s, move to FastAPI `BackgroundTasks` with `status=running` and polling (`GET /runs/{id}`). This needs no new infrastructure. Celery is only justified beyond about 100k requests, which is out of scope.

### 8.6 Frontend component map
```
src/
  api/ client.ts, schema.d.ts (generated), hooks.ts (TanStack Query)
  app/ App.tsx, routes.tsx, Layout.tsx (nav: Policies · Reviews · Audit)
  pages/ PoliciesPage, PolicyDetailPage (VersionTimeline), DraftEditorPage,
         ReviewWorkspacePage (tabs), AuditPage, NotFound
  components/
    path/ ApprovalPathColumn, StageLane, RoleChip(changeClass), PathSideBySide
    diff/ ChangeClassBadge, RuleDiffTable, ThresholdText ("> $10,000.00")
    replay/ ReplaySummaryCards, ChangedRequestsTable (filters), RequestDrawer
    cx/ CounterexampleList, CounterexampleCard, CompletenessBanner, ReverifyButton
    invariants/ InvariantTable (NEW / PRE_EXISTING / FIXED)
    review/ DecisionForm, EvidenceHashPanel, AcknowledgeViolations
    common/ HashChip, Money, EmptyState, ErrorState, Spinner
```

### 8.7 Future extension points (no dependency now)
- **Policy-as-code engines:** a `PolicyBackend` protocol (`evaluate(request) -> EvaluationResult`). A Cedar or Rego adapter could implement it for **replay** only. Exhaustive search still requires the native fragment, so search is disabled for foreign backends, with a clear message.
- **NL drafting:** a `suggest_draft(prose) -> PolicyDraft` service that writes only to `policy_drafts` and tags `origin: "assistant"`. It goes through the identical validation, submit and review pipeline. The core never calls an LLM.

---

## 9. UI/UX specification

**Navigation:** top bar with **Policies · Reviews · Audit**, plus the current user and app role (dev user switcher).

| Page | Content | Empty state | Error state |
|---|---|---|---|
| Policies | table: name, active version, pending proposals | "No policies yet. Load demo data (`make seed`)." | API down banner with retry |
| Policy detail | version timeline (label, hash chip, author, status badge: Proposed / Accepted / Rejected / Changes requested) | "No versions submitted" | — |
| Draft editor | JSON editor (textarea MVP, CodeMirror P1) + live validation list (clickable pointer) + read-only **rule table** preview | template pre-filled from base version | invalid JSON highlighted, submit disabled |
| **Review workspace** `/reviews/:proposed?base=` | header: v1 → v2, both hashes, analysis freshness. Tabs below | "No analysis run yet: **Run analysis**" | "Evidence stale (policy or dataset changed): re-run" |
| ↳ Summary | cards: changed N / M (x%), new critical violations, witnesses, search completeness | | |
| ↳ Rule changes | structural diff table: rule id, field, before, after, rendered in plain English with operators | "Rules identical (behavioral check still runs)" | |
| ↳ Replay | filters (class, role, category). Table of changed requests. Row → drawer with **side-by-side path** | "No historical request changed. This does *not* mean the policies are equivalent; see Counterexamples." | |
| ↳ Counterexamples | witness cards: request fields, amount highlighted, both paths, classes, ✔ verified, **Re-verify**, region description ("software, amount in ($10,000.00, $15,000.00]") | "Complete search: no behavioral difference within the modelled domain (K cells)." | Incomplete banner (amber) |
| ↳ Invariants | table grouped NEW / PRE_EXISTING / FIXED with severity, message, example request link | "All invariants hold" | |
| ↳ Decision | evidence hash panel, Accept / Reject / Request changes, rationale (min 20), acknowledgement checkbox per critical NEW violation. Disabled for the author | | 403 / 409 messages inline |
| Audit | chronological events, filters, **chain valid ✔ / broken ✖** | | |

**Side-by-side path visualization:** two columns (Base | Proposed) with horizontal stage lanes, aligned by stage index. Role chips carry **icon + text + color** (never color alone): `＋ finance` (added, green), `− finance` (removed, red, struck-through ghost chip in the proposed column), `↕ security` (reordered, amber), plain (unchanged, neutral). Clicking a chip opens the **provenance panel**, which shows the rule IDs, rule explanation, and the conditions with the request's actual values (e.g. `amount_minor 1250000 > 1000000 ✔`).

**Accessibility:** semantic tables, `aria-live` for validation results, keyboard-navigable tabs (WAI-ARIA tabs pattern), contrast ≥ 4.5:1, focus rings, money always written out (never only "12.5k"). Test with axe in Playwright.

**Demo data:** `acme-procurement` v1 (accepted), v2 (proposed), v2-reorder (proposed), dataset `synthetic-2026-11-seed42` (5,000 requests), users `priya` (author), `marcus` (reviewer), `admin`.

---

## 10. Security & trust

**Threat model (prototype scope)**
| Threat | Mitigation | Limitation |
|---|---|---|
| Author approves own change | `reviewer_id ≠ version.author_id` enforced in service + DB check via trigger | Dev auth is trivial to bypass locally |
| Silent edit of an accepted version | `policy_versions` immutable (trigger). Edits create new versions | A DB superuser can drop triggers |
| Rewriting history of decisions | append-only tables + hash-chained audit. `GET /audit` verifies the chain | Tamper-evident, not tamper-proof (no external anchoring) |
| Deciding on stale evidence | `evidence_hash` must match runs for exactly the (base, proposed) hashes. Otherwise `409 STALE_EVIDENCE` | — |
| Malicious policy JSON (code exec, DoS) | closed interpreter, size limits (64 KB, ≤200 rules, ≤10 conditions), strict parsing, `max_cells` bound | — |
| Injection | ORM parameterization only. React escapes output. No `dangerouslySetInnerHTML` | — |
| PII leakage | synthetic pseudonymous IDs only. No names, emails, or bank data in the schema | Users could paste real data; README warns against it |
| Misreading forecasts as facts | simulation banner + separate tab + assumption table | — |
| Real-money action | no payment or ERP integration exists; "Accept" only records a decision | — |

**Authorization (MVP):** dev-mode auth via a signed session cookie for seeded users (`POST /api/dev/login {username}`), gated by `ANTEGRAPH_ENV=dev`. Role checks: author creates drafts and versions; reviewer decides; admin manages users and datasets. Documented as **not production auth**. OIDC is a later swap behind the same dependency.

**Determinism & reproducibility:** pure core; `evaluator_version` constant bumped on any semantic change (CI checks that golden outputs changing requires a version bump); runs store all input hashes and the seed.

---

## 11. Data strategy

**Generator** (`antegraph.data.generator`, version `gen-1.0`): `generate(seed:int, n:int, profile:str) -> Iterator[PurchaseRequest]` using `random.Random(seed)` only (no global RNG, no numpy needed). Output is JSONL plus `manifest.json` `{generator_version, seed, n, profile, content_hash, created_at}`. `created_at` is excluded from the hash.

**Profile `acme-default`** (illustrative assumptions, documented as invented):
| Dimension | Distribution |
|---|---|
| category | software 30%, services 20%, hardware 15%, marketing 10%, travel 10%, office 10%, facilities 5% |
| department | engineering 35%, sales 15%, marketing 15%, operations 15%, finance 8%, hr 7%, legal 5% |
| amount | log-normal per category (e.g. software median $3,000, σ=1.2), clipped to [$1, $500,000], rounded to whole dollars 70% of the time |
| vendor | pool of 400 vendors with a Zipf-like frequency. 12% of requests to a new vendor. Risk low 60 / medium 25 / high 8 / unknown 5 / prohibited 2 |
| requester | 300 employees. 8% hold a role (manager/finance/…) matching their department |
| time | uniform business hours over 180 days |

**Boundary & adversarial injection** (`profile acme-boundaries`, about 2% of rows plus a dedicated fixture file): amounts at every rule and invariant threshold `t-1, t, t+1`, `0`, max, prohibited + high-amount combos, requester holding every path role, all `unknown` risk.

**Labels / ground truth:** the boundary profile emits `labels.jsonl` with the **expected change classes** for v1→v2, computed by a *separate, deliberately naive* oracle (`tests/oracles/naive_v1_v2.py`, hand-written logic for this specific pair, not the engine). Recall and precision of replay are measured against it.

**Rule:** never use real or private procurement data without explicit written permission. The repo ships only synthetic data, and seeds are versioned (`datasets/manifests/*.json`).

---

## 12. Testing

**Layout:** `backend/tests/{unit,property,metamorphic,integration,golden,negative,perf}` and `frontend/{src/**/*.test.tsx, e2e/}`.

**Golden cases** (`fixtures/golden/acme_v1_v2.json`, hand-verified; ✱ = demo). Default request: `engineering`, `low` risk, existing vendor, `requester_roles: []`.

| # | Request | v1 path | v2 path | Classes | New invariant violations (v2) |
|---|---|---|---|---|---|
| G1✱ | software $12,500.00 | manager → finance | manager | APPROVAL_REMOVED(finance) | INV-FIN-001 |
| G2 | software $10,000.00 (exact) | manager | manager | UNCHANGED | — |
| G3 | software $10,000.01 | manager → finance | manager | APPROVAL_REMOVED(finance) | INV-FIN-001 |
| G4 | software $15,000.00 (exact) | manager → finance | manager | APPROVAL_REMOVED(finance) | INV-FIN-001 |
| G5 | software $15,000.01 | manager → finance | manager → finance | UNCHANGED | — |
| G6 | hardware $12,500.00 | manager | manager | UNCHANGED | — |
| G7 | software $12,500.00, new vendor | manager → security → finance | manager → security | APPROVAL_REMOVED(finance) | INV-FIN-001 |
| G8 | software $60,000.00, new vendor, high risk | manager → security → {finance, legal}; evidence questionnaire | same | UNCHANGED | — |
| G9 | hardware $500.00, prohibited | BLOCKED | BLOCKED | UNCHANGED | — |
| G10 | office $0.00 | AUTO_APPROVED | AUTO_APPROVED | UNCHANGED | — |
| G11 | software $12,500.00, requester_roles {manager, finance} | manager → finance | manager | APPROVAL_REMOVED(finance) | INV-FIN-001 (new), INV-SOD-001 pre-existing |
| G12 | (v1 vs v2_reorder) software $20,000.00, new vendor | manager → security → finance | manager → finance → security | APPROVAL_REORDERED(security), APPROVAL_REORDERED(finance) | — |

Plus `acme_v1_dup_finance`: software $20,000 gives finance **once**, at stage 1, with rule IDs from both rules.

**Unit:** each condition op at boundaries. Normalization (dedupe, dense renumbering, sorting). Each diff class. Each invariant assertion. Hash stability. Money formatting (`1250000 → "$12,500.00"`).

**Property-based (Hypothesis)** with strategies for valid requests and valid random policies (≤8 rules):
1. *Determinism:* `evaluate(p, r) == evaluate(p, r)` and the result is JSON-identical across a process restart (subprocess check).
2. *Order invariance:* permuting rules or changing priorities never changes outcome fields.
3. *Self-diff:* `diff(evaluate(p,r), evaluate(p,r)) == UNCHANGED`.
4. *Diff antisymmetry:* ADDED in diff(B,P) ⇔ REMOVED in diff(P,B).
5. *Block dominance:* adding any matching block rule gives BLOCKED.
6. *Hash:* `hash(canonical(x)) == hash(canonical(json.loads(json.dumps(x, indent=2))))`.
7. *Witness validity:* every witness from `search` re-validates and differs.

**Metamorphic (the completeness check):**
- **Representative equivalence:** for random valid request `r`, `cell(r)` gives the partition representative `rep`. Then `diff(B,P)(r) == diff(B,P)(rep)` and invariant violations are equal. If this ever fails, the partition is wrong.
- **Search vs random sampling:** for random policy pairs, if 100k random requests find a difference, the search must too. If the search says `complete & equivalent`, random sampling must never find one.
- **Threshold shift:** moving a threshold by +Δ changes outcomes only for amounts in the shifted interval.
- **Known pairs:** 5 equivalent pairs (shuffled rules, priority changes, `gte 1000001` ≡ `gt 1000000`, `in [a]` ≡ `eq a`, redundant duplicate rule) → `complete, no difference`. 5 different pairs → a witness each.

**Negative:** `fixtures/invalid/*.json`, each with `expected_errors.json`: float amount, unknown field, unknown op, bad enum, duplicate rule ID, empty `all`, >200 rules, wrong currency, stage 0, missing field, extra field, unsupported schema_version.

**Integration (API + Postgres):** submit → evaluate → run → review happy path; idempotent submit; immutability (raw `UPDATE` raises); self-review 403; stale evidence 409; audit chain verifies, and manual tampering in the test DB is detected.

**E2E (Playwright):** the demo script (§17) as a test, plus an axe accessibility scan of the review workspace.

**Performance:** `pytest -m perf` and `bench/run.py` (§13). Not run in normal CI; nightly or manual.

**Commands**
```bash
make test        # cd backend && uv run pytest -m "not perf" --cov=antegraph
make lint        # ruff check, ruff format --check, mypy src, lint-imports
make test-fe     # cd frontend && npm test && npm run typecheck
make e2e         # docker compose up -d && npx playwright test
make bench       # uv run python bench/run.py --sizes 100 1000 5000 10000
```

**CI (GitHub Actions `.github/workflows/ci.yml`):** jobs `backend` (uv sync → lint → unit, property and golden tests with Hypothesis profile `ci` at 500 examples), `backend-integration` (Postgres 16 service container), `frontend` (typecheck, lint, vitest, build), `e2e` (on PRs to main and nightly). Coverage gate: core packages ≥ 90% lines.

---

## 13. Evaluation

Reports go in `docs/evaluation/*.md` using the templates below. **No numbers are entered until measured.**

| Dimension | Metric | Method | Baseline |
|---|---|---|---|
| Evaluator correctness | golden pass rate. Property tests: 0 failures over N examples | §12 | — (must be 100%) |
| Changed-route detection | precision and recall vs the naive oracle labels | boundary profile, v1→v2 and v1→v2_reorder | *text diff baseline*: "rule changed" flags all requests matching the rule's **old or new** predicate (over-approximation). Report its precision for contrast |
| Replay-only blind spots | # of known behavior differences found by search but absent from history | 10 policy pairs × dataset | replay-only |
| Witness validity | % of witnesses that re-verify (target 100%) and that pass schema validation | §7.6 over all pair fixtures | — |
| Search completeness | agreement with metamorphic sampling and with Z3 (if built) | §12 | random sampling at 100k |
| Scalability | wall time and peak RSS for replay at 100 / 1k / 5k / 10k. Search time vs K | `bench/run.py`, 5 runs, report median and IQR, `tracemalloc` + `resource.getrusage` | — |
| Human comprehension | correct-interpretation rate and time-to-decision | 3–5 volunteers, consented, think-aloud. Task: "Should this change be accepted? Why?" with the UI vs with a raw JSON diff | raw JSON diff + changelog |
| Simulation (P2) | M/M/1 error vs analytic | §7.9 | analytic formula |

**Benchmark report template**
```
## Replay benchmark — <date>, commit <sha>
Hardware: <CPU model>, <cores>, <RAM>, <OS>; Python <ver>; evaluator <ver>
Policies: acme_v1 (<hash>), acme_v2 (<hash>); dataset seed <n>, profile <p>
| N requests | median s | IQR s | peak MiB | changed | 
| 100 | _ | _ | _ | _ |
| 1,000 | … |
Search: K=<cells>, time=<s>, witnesses=<n>, complete=<bool>
Notes / limitations:
```

**Usability report template:** participants (n, roles, no identities), protocol, task, metrics (correct verdict y/n, time, # of misinterpretations), quotes (anonymized), limitations ("small n, convenience sample, not generalizable").

**Limitations to state upfront:** synthetic data, a toy-size language, single currency, the evaluator is the reference semantics (bugs in it propagate, which Z3 and the naive oracle mitigate), and a small usability sample.

---

## 14. Implementation roadmap

### 14.1 Six-week plan (milestones M1–M6)

**Week 1 · M1 Evaluator core** (Nov 10–16)
| Days | Packet | Tickets |
|---|---|---|
| 1 | Scaffolding, CI, SEMANTICS.md | #1, #2 |
| 2–3 | Domain models, DSL validation, hashing | #3, #4, #5 |
| 3–4 | Evaluator + normalization | #6 |
| 5 | Fixtures, golden, boundary, property tests, `antegraph evaluate` | #7, #8, #9 |
- **Deliverable:** CLI evaluates v1/v2 on golden requests. **Exit:** 12 golden + boundary + property tests green in CI.
- **Risk:** semantics churn. **Fallback:** freeze SEMANTICS.md on day 1. Changes require an ADR.

**Week 2 · M2 Versioning, API & replay** (Nov 17–23)
| Days | Packet | Tickets |
|---|---|---|
| 1 | Semantic diff + classes | #10 |
| 2 | Synthetic generator + replay engine + CLI diff/replay | #11, #12, #13 |
| 3–4 | Postgres, migrations, immutable version store | #14, #15 |
| 5 | FastAPI endpoints, replay run persistence | #16, #17 |
- **Exit:** two versions replayed against the same stored dataset via the API. Counts match the CLI.
- **Risk:** DB plumbing eats the week. **Fallback:** keep the DB to versions + runs only, store per-request results as one jsonb blob.

**Week 3 · M3 Inspection UI** (Nov 24–30)
| Days | Packet | Tickets |
|---|---|---|
| 1 | Frontend scaffold, generated types, layout | #18 |
| 2 | Policies + version timeline | #19 |
| 2–3 | Rule-level structural diff (API + UI) | #20 |
| 3–4 | Replay summary + changed-requests table | #21 |
| 5 | Side-by-side paths + provenance panel | #22 |
- **Exit:** a user can inspect changed paths and rule provenance in the browser.
- **Risk:** UI polish rabbit hole. **Fallback:** plain CSS, no component library, no editor widget.

**Week 4 · M4 Counterexamples & invariants** (Dec 1–7)
| Days | Packet | Tickets |
|---|---|---|
| 1 | Invariant DSL + checker + classification | #23 |
| 2 | Partition builder | #24 |
| 3 | Search + witness verification | #25 |
| 4 | Metamorphic + known-pair tests | #26 |
| 4–5 | API endpoints + explorer / invariant UI | #27, #28 |
- **Exit:** the $12,500 witness is generated and verified. INV-FIN-001 is flagged NEW. 5/5 equivalent pairs are reported equivalent.
- **Risk:** partition bugs. **Fallback:** the metamorphic test is the safety net. Ship with `complete` hidden (always "search found / not found") if not yet trusted.

**Week 5 · M5 Human review & audit** (Dec 8–14)
| Days | Packet | Tickets |
|---|---|---|
| 1 | Users, dev auth, role checks | #29 |
| 2 | Append-only audit + hash chain | #30 |
| 3 | Review decision endpoint + evidence hash + staleness | #31 |
| 4–5 | Decision UI + audit page | #32 |
| (opt) | SimPy workload | #33 |
- **Exit:** the full proposal → analysis → review → audit workflow works in the UI.

**Week 6 · M6 Hardening & demo** (Dec 15–21)
| Days | Packet | Tickets |
|---|---|---|
| 1–2 | Integration + Playwright E2E | #34 |
| 2 | Benchmarks, real numbers | #35 |
| 3 | Security review + threat model doc | #36 |
| 4–5 | README, architecture doc, demo seed, recording | #37 |
| (opt) | Z3 cross-check, export | #38, #39 |
- **Exit:** a fresh clone runs `make demo` and reproduces the demo. All docs have measured results.

### 14.2 Aggressive four-week plan
| Week | Scope | Cuts |
|---|---|---|
| 1 | #1–#13: core + diff + generator + replay, all CLI | — |
| 2 | #23–#26: invariants + search + metamorphic tests (CLI `check`) | Search moves before the DB, since it is the core value |
| 3 | #14–#17, #29–#31: DB, API, review + audit (minimal) | single-table results; no rule-diff endpoint (shown as a JSON side-by-side) |
| 4 | #18, #21, #22, #27, #28, #32, #34 (happy-path E2E only), #37 | No #19/#20 polish, no #33/#35 report/#38/#39. Bench numbers in README only |

---

## 15. GitHub project structure

### 15.1 Directory tree
```
AnteGraph/
├── README.md                     # pitch, demo GIF, quickstart, results (measured)
├── Makefile                      # setup, test, lint, run, seed, demo, bench
├── docker-compose.yml            # postgres:16, api, web
├── .github/
│   ├── workflows/ci.yml
│   ├── ISSUE_TEMPLATE/{feature.md,bug.md}
│   └── pull_request_template.md
├── docs/
│   ├── PROPOSAL.md  ROADMAP.md  SEMANTICS.md  ARCHITECTURE.md  SECURITY.md  DEMO.md
│   ├── decisions/ADR-0001-own-evaluator.md …
│   ├── evaluation/{benchmarks.md, usability.md}
│   └── research/competitors.md
├── fixtures/
│   ├── policies/{acme_v1,acme_v2,acme_v2_reorder,acme_v1_shuffled,acme_v1_dup_finance}.json
│   ├── invariants/acme_guarantees.json
│   ├── golden/acme_v1_v2.json
│   ├── pairs/{equivalent,different}/*.json
│   └── invalid/*.json (+ expected_errors.json)
├── backend/
│   ├── pyproject.toml  uv.lock  alembic.ini
│   ├── src/antegraph/
│   │   ├── __init__.py  version.py (EVALUATOR_VERSION)  cli.py
│   │   ├── domain/{enums.py, models.py, money.py}
│   │   ├── dsl/{policy.py, invariants.py, validate.py, canonical.py, rule_diff.py}
│   │   ├── engine/{evaluator.py, normalize.py}
│   │   ├── analysis/{diff.py, replay.py, partition.py, search.py, invariants.py, z3_backend.py}
│   │   ├── data/generator.py
│   │   ├── sim/workload.py
│   │   ├── store/{db.py, tables.py, repositories.py}
│   │   ├── services/{policies.py, runs.py, reviews.py, audit.py}
│   │   └── api/{main.py, deps.py, errors.py, routers/*.py}
│   ├── migrations/versions/*.py
│   └── tests/{unit,property,metamorphic,golden,negative,integration,perf,oracles}/
├── frontend/
│   ├── package.json  vite.config.ts  tsconfig.json  playwright.config.ts
│   ├── src/{api,app,pages,components}/
│   └── e2e/demo.spec.ts
├── bench/{run.py, results/}
└── datasets/manifests/*.json     # generated JSONL is gitignored, manifests committed
```

**Naming:** Python `snake_case` modules, `PascalCase` models. Rule IDs `kebab-case`. Invariant IDs `INV-<AREA>-NNN`. Error codes `UPPER_SNAKE`. TS components `PascalCase.tsx`.

### 15.2 Workflow: commits, issues, milestones
- **Trunk-based on `main`.** Small, focused commits in Conventional Commit style: `feat(engine): normalize duplicate approvers (#6)`.
- **Every commit references its issue** (`(#n)`). The final commit for an issue uses `Closes #n`, or the issue is closed with `gh issue close n -c "<brief note>"`.
- **Issue lifecycle:** opened from this backlog with a milestone, then a brief comment when work starts ("Starting: approach …"), then a brief closing comment summarising what landed and how it was tested.
- Larger features (#25, #31, #32) may use a short-lived branch `feat/<n>-<slug>` + PR with `Closes #n`.
- **Milestones:** `M1 · Evaluator core` … `M6 · Hardening & demo` (due Sundays, §14).

**Labels:** `type:feature` `type:test` `type:docs` `type:infra` · `area:engine` `area:analysis` `area:api` `area:db` `area:frontend` `area:data` `area:review` · `P0` `P1` `P2` · `stretch`.

### 15.3 Prioritized backlog (= GitHub issues)
Effort: S ≤ ½ day, M ≈ 1 day, L ≈ 2 days.

| # | Title | Milestone | Labels | Est | Deps |
|---|---|---|---|---|---|
| 1 | Scaffold backend package, tooling, Makefile, CI | M1 | infra, P0 | S | — |
| 2 | Write SEMANTICS.md (normative evaluator spec) | M1 | docs, engine, P0 | S | — |
| 3 | Domain enums & PurchaseRequest model with strict validation | M1 | engine, P0 | M | 1 |
| 4 | Policy DSL models + semantic validator with error codes | M1 | engine, P0 | M | 3 |
| 5 | Canonical JSON + SHA-256 content hashing | M1 | engine, P0 | S | 4 |
| 6 | Deterministic evaluator + path normalization | M1 | engine, P0 | M | 4 |
| 7 | Policy fixtures + golden & boundary tests | M1 | test, P0 | M | 6 |
| 8 | Property-based evaluator tests (Hypothesis) | M1 | test, P0 | S | 6 |
| 9 | CLI: `antegraph evaluate` / `validate` / `hash` | M1 | engine, P1 | S | 6 |
| 10 | Semantic diff + change classification | M2 | analysis, P0 | M | 6 |
| 11 | Synthetic dataset generator (seeded, manifest, boundary profile) | M2 | data, P0 | M | 3 |
| 12 | Historical replay engine + summary + result hash | M2 | analysis, P0 | S | 10, 11 |
| 13 | CLI: `antegraph diff` / `replay` / `generate` | M2 | analysis, P1 | S | 12 |
| 14 | Postgres via Docker Compose, SQLAlchemy tables, Alembic, append-only triggers | M2 | db, infra, P0 | M | 1 |
| 15 | Immutable policy version store: drafts, submit, idempotent hashing | M2 | db, P0 | M | 5, 14 |
| 16 | FastAPI app: policies, versions, evaluate, compare | M2 | api, P0 | M | 15 |
| 17 | Datasets + replay runs API with persisted results & paging | M2 | api, P0 | M | 12, 16 |
| 18 | Frontend scaffold: Vite/React/TS, router, layout, generated API types | M3 | frontend, P0 | S | 16 |
| 19 | Policies page & version timeline | M3 | frontend, P1 | S | 18 |
| 20 | Rule-level structural diff (API + UI) | M3 | analysis, frontend, P1 | M | 18 |
| 21 | Replay summary cards + changed-requests table with filters | M3 | frontend, P0 | M | 17, 18 |
| 22 | Side-by-side approval path view + provenance panel | M3 | frontend, P0 | M | 21 |
| 23 | Invariant DSL + checker with NEW / PRE_EXISTING / FIXED | M4 | analysis, P0 | M | 6 |
| 24 | Partition builder (thresholds, midpoints, enums, role subsets) | M4 | analysis, P0 | M | 4 |
| 25 | Bounded exhaustive counterexample search + witness verification | M4 | analysis, P0 | M | 10, 23, 24 |
| 26 | Metamorphic & known-pair tests for search completeness | M4 | test, P0 | M | 25 |
| 27 | Search runs + invariant API endpoints, CLI `check` with exit codes | M4 | api, P0 | S | 17, 25 |
| 28 | Counterexample explorer + invariants tab UI | M4 | frontend, P0 | M | 22, 27 |
| 29 | Seeded users, dev auth, role-based permissions | M5 | api, review, P0 | M | 16 |
| 30 | Hash-chained append-only audit log + verification endpoint | M5 | db, review, P0 | M | 14 |
| 31 | Review decisions: evidence hash, staleness, self-review guard | M5 | review, api, P0 | M | 27, 29, 30 |
| 32 | Review & sign-off UI + audit history page | M5 | frontend, review, P0 | M | 28, 31 |
| 33 | (Stretch) SimPy workload simulation with assumption panel | M5 | analysis, P2, stretch | L | 17 |
| 34 | API integration suite + Playwright E2E demo flow + axe | M6 | test, P0 | M | 32 |
| 35 | Benchmarks 100–10k requests + report | M6 | test, P1 | S | 17 |
| 36 | Security review & threat model doc | M6 | docs, P1 | S | 31 |
| 37 | README, ARCHITECTURE, DEMO script, `make demo` seed | M6 | docs, P0 | M | 34 |
| 38 | (Stretch) Z3 cross-check backend | M6 | analysis, P2, stretch | L | 25 |
| 39 | (Stretch) JSON/CSV impact report export | M6 | analysis, P2, stretch | S | 27 |

---

## 16. Initial implementation sprint

**First 10 tasks**
1. Create `backend/` with `uv init --package`, add deps, configure ruff, mypy and pytest (#1).
2. Makefile targets `setup test lint`, plus a CI workflow running them (#1).
3. Write `docs/SEMANTICS.md` from §5 (#2).
4. `domain/enums.py`, `domain/models.py` (PurchaseRequest, strict) (#3).
5. `dsl/policy.py` (Condition, Predicate, Effect, Rule, Policy) + `dsl/validate.py` (#4).
6. `dsl/canonical.py` → `canonical_json`, `content_hash` (#5).
7. `engine/evaluator.py` + `engine/normalize.py` (#6).
8. Fixtures `acme_v1.json`, `acme_v2.json`, `golden/acme_v1_v2.json` (#7).
9. Golden + boundary tests G1–G12 (#7) and Hypothesis determinism / order invariance (#8).
10. `cli.py evaluate --policy P --request R` printing EvaluationResult JSON (#9).

**Scaffolding commands**
```bash
brew install uv                     # or: pipx install uv
mkdir backend && cd backend
uv init --package --name antegraph --python 3.12
uv add pydantic typer
uv add --dev pytest pytest-cov hypothesis ruff mypy import-linter
uv run pytest
```

**Evaluator signature**
```python
# backend/src/antegraph/engine/evaluator.py
def evaluate(policy: Policy, request: PurchaseRequest) -> EvaluationResult:
    """Pure, deterministic evaluation per docs/SEMANTICS.md §5.6–5.8.
    No IO, clock, or randomness. Rule order and priority never affect outcome fields."""
```

**Initial test**
```python
# backend/tests/golden/test_acme_v1_v2.py
import pytest
from antegraph.engine.evaluator import evaluate
from tests.helpers import load_policy, load_golden, roles_by_stage

CASES = load_golden("acme_v1_v2.json")

@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden(case):
    v1, v2 = load_policy("acme_v1.json"), load_policy("acme_v2.json")
    assert roles_by_stage(evaluate(v1, case["request"])) == case["expected"]["v1"]
    assert roles_by_stage(evaluate(v2, case["request"])) == case["expected"]["v2"]
```

**First runnable vertical slice (end of Week 1)**
```bash
uv run antegraph evaluate --policy ../fixtures/policies/acme_v1.json --request ../fixtures/requests/g1.json
uv run antegraph evaluate --policy ../fixtures/policies/acme_v2.json --request ../fixtures/requests/g1.json
# Week 2 adds: uv run antegraph diff --base … --proposed … --request …
```

---

## 17. Demo & recruiter narrative

**3-minute demo script**
| t | Show | Say |
|---|---|---|
| 0:00 | Policies page | "Procurement teams change approval rules all the time. A text diff tells you a number changed. Antegraph tells you what happens to purchases." |
| 0:20 | Draft editor: `1000000 → 1500000`, Validate, Submit | "Raising the software finance threshold from $10k to $15k. The version is now immutable and hashed." |
| 0:40 | Rule changes tab | "Here's the structural change, in plain English: '> $10,000.00' becomes '> $15,000.00'." |
| 0:55 | Replay tab | "Replaying our synthetic history of N requests: X changed routes, all losing finance approval. Here's one side by side, with provenance." |
| 1:30 | Counterexamples tab | "History is incomplete, so Antegraph searches every behaviorally distinct input region. Here's a verified witness: a $12,500 software request. v1 routes manager → finance, v2 just manager. The search is complete within the modelled domain." Click **Re-verify**. |
| 2:05 | Invariants tab | "Separately, compliance owns invariants. INV-FIN-001 says software over $10k needs finance. v2 newly violates it. That's different from simply differing from v1." |
| 2:25 | Decision tab as `marcus` | "Antegraph never deploys. A human decides. Marcus rejects with a rationale, and the decision is bound to the policy hashes and evidence hash." |
| 2:45 | Audit page | "Every step is in an append-only, hash-chained audit log. Chain valid." |

**Engineering tradeoffs to explain:** own a tiny DSL instead of OPA/Cedar, which buys exhaustive search but costs expressiveness. Partition enumeration vs SMT: simpler and complete for this fragment, with Z3 as a cross-check. A synchronous modular monolith instead of queues. Tamper-evident audit rather than tamper-proof. Synthetic data with stated distributions.

**Resume bullets (fill only with measured values)**
- Built Antegraph, a predeployment verification engine for procurement approval policies (Python/FastAPI, PostgreSQL, React/TS), comparing ordered multi-stage approval paths across policy versions with rule-level provenance.
- Designed a bounded-exhaustive counterexample search that partitions the request space by policy thresholds. It found behavioral differences missed by historical replay in [__ of __] test policy pairs, and all [__] generated witnesses were independently re-verified.
- Replayed [__]k synthetic requests in [__] s (median, [hardware]). Reached [__]% coverage with [__] property-based and metamorphic tests guarding determinism and search completeness.
- Implemented evidence-bound human review with an append-only, hash-chained audit log and separation of duties (author ≠ reviewer).

---

## 18. Risks & decision log

| Risk | Likelihood / impact | Mitigation | Kill / pivot criterion |
|---|---|---|---|
| Semantic ambiguity (reorder, dedupe, blocks) | High / High | SEMANTICS.md first, golden tests, ADRs | If semantics still churn by the end of week 2 → freeze to the current version and document the open points |
| Complexity creep (UI, OR predicates, more fields) | High / Med | Cut lines in §4. New constructs need an ADR plus partition support | Any feature that breaks exhaustive search is deferred |
| Partition / search bugs give false "equivalent" | Med / High | Metamorphic tests, known pairs, optional Z3 | If metamorphic tests fail and can't be fixed in 2 days → ship "witness search" without completeness claims |
| Solver integration (Z3 install, encoding of order) | Med / Low | Stretch only. Encode membership before order | Drop if more than 2 days |
| Language too weak to be convincing | Med / Med | Pick demo scenarios that fit. Document an extension path (OR, date windows) | — |
| Simulation mistaken for fact | Low / Med | Labels, sensitivity, separate tab | Drop simulation entirely if time is short |
| Differentiation vs Cedar SymCC | Med / Med | Cite it honestly. The emphasis is ordered paths + replay + review | Never claim novelty without research (§2 pending task) |
| Time overrun | Med / High | Four-week plan, weekly exit criteria | At the end of week 4 without M4 done → switch to the four-week cut |

**Decision log (ADRs to write)**
- ADR-0001: Own evaluator over OPA/Cedar (§2).
- ADR-0002: All matching rules fire, block dominates, priority is presentational.
- ADR-0003: Partition enumeration as the primary search, Z3 as cross-check.
- ADR-0004: Synchronous runs for ≤10k requests.
- ADR-0005: Tamper-evident hash-chained audit.

---

## 19. Open questions (with defaults; work proceeds on defaults)

1. **License?** Default: **MIT**. Apache-2.0 if a patent grant is preferred.
2. **Multi-currency?** Default: no (USD only, A1).
3. **OR / `any` predicates in MVP?** Default: no. Revisit after M4, since partition support is straightforward.
4. **Blocked requests: show suppressed stages?** Default: list matched rules with `suppressed_by_block`, `stages = []`.
5. **Should accepting with critical NEW violations be allowed?** Default: yes, with explicit per-violation acknowledgement.
6. **Who owns invariant sets?** Default: admin/reviewer only. Authors can view but not edit.
7. **Max amount bound for search?** Default: $10B (`10^12` minor units).
8. **Hosting the demo?** Default: local `docker compose` + recorded GIF/video. A free-tier deploy is optional.
9. **Frontend styling?** Default: plain CSS modules. No UI kit (keeps bundle and focus small).
10. **Second reviewer (two-person rule) for critical changes?** Default: no. Single reviewer; noted as an extension.

---

## 20. Immediate next steps (today)

1. `#1` Scaffold `backend/` with uv, ruff, mypy, pytest, Makefile, CI.
2. `#2` Write `docs/SEMANTICS.md`.
3. `#3` Enums + `PurchaseRequest` with strict validation and its negative tests.
4. `#4` Policy models + validator.
5. `#6` Evaluator. Then `#7` golden G1–G12.

---

## Definition of MVP completion

Antegraph's MVP is complete when, from a fresh clone, `make demo` lets a user:
1. submit v2 as an immutable, hashed version;
2. see a replay over a seeded synthetic dataset with correct change classes and provenance;
3. see at least one **independently re-verified** counterexample (the $12,500 witness) and a completeness statement;
4. see invariant violations classified NEW / PRE_EXISTING / FIXED, independent of the diff;
5. record a human ACCEPT/REJECT with rationale, bound to policy and evidence hashes, by a reviewer who is not the author;
6. view an append-only audit log whose hash chain verifies;

and CI passes the golden, property, metamorphic, negative, integration and E2E suites, and every number in the README was measured.

**Recommended build order:** semantics → models/validation → evaluator → golden/property tests → diff → generator → replay → invariants → partition/search → metamorphic tests → DB/version store → API → review/audit → UI (inspection → explorer → decision) → E2E → benchmarks → docs/demo → stretch (Z3 → export → simulation).
