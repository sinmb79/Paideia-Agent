# 폐쇄형 보완 교육과정 피드백 루프

릴리즈 목표: 2026-Q3  
코드명: Adaptive Curriculum Feedback Loop

Paideia Agent는 이제 검토된 실패를 재교육 루프로 전환하는 로컬 CLI 흐름을 제공합니다.

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

`kibo-plan`은 `--weakness-path`를 받을 수 있습니다. 활성 고심각도 또는 반복 약점은 reuse confidence를 낮추고, 보완 학습 증거가 기록되기 전까지 direct reuse를 차단합니다.

## 안전 경계

- 로컬 JSON/JSONL만 사용합니다.
- 외부 DB를 추가하지 않습니다.
- hidden chain-of-thought를 재사용하지 않습니다.
- WeaknessRecord는 evidence 기반의 검토 가능한 산출물입니다.

## 검증

- 전체 테스트: `329 passed`
