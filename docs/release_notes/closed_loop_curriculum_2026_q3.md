# Closed-Loop Curriculum Feedback Loop

Release target: 2026-Q3  
Codename: Adaptive Curriculum Feedback Loop

Paideia Agent now exposes a local CLI workflow for turning reviewed failures into remediation:

```text
FailureMemory -> WeaknessRecord -> CurriculumPlan -> AdaptiveExam -> CurriculumCompletion
```

## CLI

```bash
ai22b-talent-foundry weakness-detect
ai22b-talent-foundry curriculum-generate
ai22b-talent-foundry adaptive-exam
ai22b-talent-foundry curriculum-complete
ai22b-talent-foundry curriculum-report
```

`kibo-plan` also accepts `--weakness-path`. Active high-severity or repeated weaknesses reduce reuse confidence and block direct reuse until remediation evidence is recorded.

## Safety

- Local JSON/JSONL only.
- No external database.
- No hidden chain-of-thought reuse.
- Weakness records are evidence-based, reviewable artifacts.

## Validation

- Full test suite: `329 passed`
