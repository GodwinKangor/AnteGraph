# Antegraph

> See the consequences before they happen.

Antegraph is a predeployment verification and impact-analysis engine for **procurement approval policies**. Given a current and a proposed policy, it:

- evaluates approval paths deterministically,
- replays historical (synthetic) purchase requests,
- generates verified counterexample requests that expose behavioral differences,
- checks independent business invariants,
- and records an evidence-backed human review decision.

It never deploys anything automatically.

**Status:** early development. See the [roadmap](docs/ROADMAP.md) and the [project proposal](docs/PROPOSAL.md). Progress is tracked as GitHub milestones (M1–M6) and issues.

Antegraph is an independent portfolio prototype. It is not affiliated with any procurement vendor and uses synthetic data only.
