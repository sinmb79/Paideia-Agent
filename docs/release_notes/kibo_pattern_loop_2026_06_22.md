# Human-Style Learning Loop and Pattern Reinforcement

Release date: 2026-06-22

This release upgrades Paideia's Kibo Reuse Router from simple case reuse into a human-style learning loop:

```text
learning -> exam -> validation -> real-world application -> outcome evaluation -> reinforcement or weakening
```

Kibo records remain concrete, reviewable cases. The new Pattern Layer extracts reusable `PatternCandidate` strategies above those cases and routes them through exam validation, field outcome tracking, failure-memory checks, user-decision fit scoring, self-critic gates, and skill-gap detection before stronger reuse is allowed.

## Highlights

- Added Pattern Candidate contracts for reusable strategies extracted from Kibo records.
- Added deterministic pattern exam results, real-world outcome tracking, reinforcement scoring, and weakened/quarantined pattern states.
- Added FailureMemory integration so similar past failures reduce reuse confidence or block direct reuse.
- Added UserDecisionModel scoring based on evidence-backed preferences only, without sensitive personal attributes.
- Added Self-Critic reports and high-risk gates. High-risk tasks require field validation and critic approval before strong reuse.
- Added SkillGraph MVP to identify missing or weak capabilities and route them to LLM assistance or further learning.
- Extended `ReuseDecision` with pattern status, validation flags, failure warnings, critic requirements, and user-fit score.
- Added local-first CLI commands:
  - `pattern-extract`
  - `pattern-exam`
  - `pattern-outcome`
  - `pattern-reinforce`
  - `failure-search`
  - `critic-report`
- Added JSON Schema validators, sample artifacts, documentation, and regression tests.

## Runtime Policy

- Draft patterns cannot use direct reuse.
- Exam-validated patterns can support partial reuse.
- Field-validated or reinforced patterns can support stronger reuse only when other risk gates pass.
- Quarantined patterns do not influence runtime decisions except as warnings or blockers.
- Hidden chain-of-thought is never stored or reused.
- All MVP storage remains local JSON/JSONL. No external database dependency was added.

## Validation

- `Paideia-Agent`: 317 tests passed.
- Pattern Layer targeted tests: 21 tests passed.
- Sample CLI flow verified with local JSON/JSONL artifacts.

<details>
<summary>한국어 설명 보기</summary>

# Human-Style Learning Loop / Pattern Reinforcement

릴리즈 일자: 2026-06-22

이번 릴리즈는 Paideia의 Kibo Reuse Router를 단순한 과거 사례 재사용 구조에서 인간식 학습 루프로 확장합니다.

```text
학습 -> 시험 -> 검증 -> 실전 적용 -> 결과 평가 -> 패턴 강화 또는 약화
```

Kibo record는 검토된 구체 사례로 유지됩니다. 그 위에 새 Pattern Layer를 두어 여러 Kibo에서 공통 전략인 `PatternCandidate`를 추출하고, 시험 검증, 실전 결과 기록, 실패 메모리, 사용자 의사결정 적합도, self-critic gate, skill gap 검사를 거친 뒤에만 더 강한 재사용을 허용합니다.

## 주요 변경

- Kibo 기록 위에 Pattern Candidate 계약을 추가했습니다.
- Pattern exam, real-world outcome, reinforcement score, weakened/quarantined 상태를 추가했습니다.
- FailureMemory가 유사 실패를 찾아 reuse confidence를 낮추거나 direct reuse를 차단합니다.
- UserDecisionModel은 민감정보 없이 evidence-based preference만 사용합니다.
- Self-Critic report와 high-risk gate를 추가했습니다.
- SkillGraph MVP로 부족한 능력을 찾아 LLM 보조 또는 추가 학습 대상으로 분리합니다.
- `ReuseDecision`에 pattern 상태, exam/field validation, failure warning, critic 필요 여부, user-fit score를 추가했습니다.
- 모든 저장은 로컬 JSON/JSONL 기반이며 외부 DB 의존성을 추가하지 않았습니다.

## 검증

- `Paideia-Agent`: 전체 317개 테스트 통과
- Pattern Layer targeted test: 21개 통과
- 로컬 JSON/JSONL 샘플 CLI 흐름 검증 완료

</details>
