# Antegraph — Project Proposal

**Tagline:** See the consequences before they happen.

**Project type:** Open-source portfolio prototype / procurement workflow verification

## Executive summary

Antegraph is a **predeployment verification and impact-analysis engine for procurement approval policies**. Before an administrator activates a proposed policy, Antegraph compares the old and new policy behavior, replays historical purchasing requests, finds synthetic counterexamples that expose otherwise unseen changes, estimates review workload under stated assumptions, and presents evidence for human approval.

Antegraph is **not** an invoice processor, procurement chatbot, replacement for Zip, or a generic text diff. Its central question is: **What will this rule change do to purchasing workflows, and could it violate a business guarantee?**

## Example

**Old:** Software purchases above $10,000 require finance approval.
**Proposed:** Software purchases above $15,000 require finance approval.

Antegraph generates a counterexample: a $12,500 software request that required finance approval before but no longer does. It also reports the number of historical requests with changed approval routes. A reviewer decides whether the change is intentional.

## Intended users

- Procurement operations administrators proposing approval-rule changes.
- Finance, security, and compliance reviewers evaluating consequences.
- Engineers testing workflow configurations before release.

## Scope and differentiation

Existing systems such as Open Policy Agent, Cedar, and Z3 support policy evaluation or symbolic reasoning; PM4Py and SimPy support process analysis or simulation. Antegraph's proposed integration is procurement-specific approval-path comparison + historical replay + counterexample generation + human sign-off, with optional queue-impact simulation. This is a project hypothesis, **not a verified claim of market novelty**.

Antegraph is relevant to procurement orchestration companies such as Zip, but it is an independent prototype and is not affiliated with or integrated into Zip.

## Explicit non-goals

- Paying invoices, processing real funds, handling vendor banking data, or accessing live financial systems.
- Replacing enterprise policy engines or claiming formal proof for unsupported policy constructs.
- Autonomous policy deployment.
- Predicting employee behavior without an explicit validated model.
- Broad fraud detection or full contract interpretation.

See [ROADMAP.md](ROADMAP.md) for the implementation plan.
