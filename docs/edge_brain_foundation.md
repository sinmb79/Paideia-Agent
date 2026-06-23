# Paideia Edge Brain Foundation

This repository now contains the first PR-sized foundation for the independent
edge brain design: reviewable contracts and JSON Schemas under
`src/ai22b/edge_brain` and `schemas/edge_brain`.

PR-1 intentionally does not execute actions. It defines the durable artifact
boundary for later compiler, simulator, runtime, outcome, remediation, store,
and audit work:

- observations and world state
- capability contracts
- action patterns and action receipts
- behavioral exam results
- outcome evidence and step credit
- weakness records and remediation tickets
- deployment artifact manifests

The contracts keep `learning_status` separate from `deployment_status`, and
schemas reject extra unreviewed fields such as private reasoning traces.
