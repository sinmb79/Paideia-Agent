# Kibo Reuse Router

Kibo Reuse Router routes new work through reviewed local reasoning-kibo records before using a general LLM. It only reads reviewable summaries and promoted Kibo records. Quarantined, draft, candidate, and unreviewed records are excluded from runtime search.

## Pattern Layer

Kibo records are concrete reviewed cases. Pattern Candidates are abstract strategies extracted from one or more Kibo records and then improved through the Paideia learning loop:

```text
learning -> exam -> validation -> real-world application -> outcome evaluation -> reinforcement or weakening
```

Runtime rules:

- Draft patterns cannot direct-reuse.
- Exam-validated patterns can support partial reuse.
- High-risk tasks require field validation plus a passing self-critic gate.
- FailureMemory warnings reduce confidence and can block direct reuse.
- UserDecisionModel improves fit scoring from evidence-based preferences only.
- SkillGraph gaps are routed to `llm_required_parts` or further learning.

## CLI

```bash
ai22b-talent-foundry kibo-index --repo-root . --output runs/kibo_index.json
ai22b-talent-foundry kibo-search --task examples/investment_research_task.json --kibo-path examples/reasoning_kibo.sample.jsonl
ai22b-talent-foundry kibo-plan --task examples/investment_research_task.json --kibo-path examples/reasoning_kibo.sample.jsonl --output runs/kibo_plan.json
ai22b-talent-foundry kibo-run --task examples/investment_research_task.json --kibo-path examples/reasoning_kibo.sample.jsonl --output runs/kibo_run.json
ai22b-talent-foundry kibo-report --run runs/kibo_run.json --output runs/kibo_report.json
```

Pattern commands:

```bash
ai22b-talent-foundry pattern-extract --kibo-dir examples --output runs/patterns.jsonl
ai22b-talent-foundry pattern-exam --pattern-id PATTERN_ID --pattern-path runs/patterns.jsonl --output runs/pattern_exam.json
ai22b-talent-foundry pattern-outcome --pattern-id PATTERN_ID --task-id TASK_ID --success true --score 0.82 --output runs/pattern_outcomes.jsonl
ai22b-talent-foundry pattern-reinforce --pattern-id PATTERN_ID --pattern-path runs/patterns.jsonl --exam-path runs/pattern_exam.json --outcome-path runs/pattern_outcomes.jsonl --output runs/pattern_reinforcement.json
ai22b-talent-foundry failure-search --task examples/investment_research_task.json --failure-path examples/failure_memory.sample.jsonl
ai22b-talent-foundry critic-report --pattern-id PATTERN_ID --pattern-path runs/patterns.jsonl --output runs/critic_report.json
```

High-risk tasks can use only partial or weaker reuse. Freshness-sensitive parts, missing context, ambiguous intent, validation failures, and style rewrites remain LLM-eligible. Hidden chain-of-thought is never stored or reused.
