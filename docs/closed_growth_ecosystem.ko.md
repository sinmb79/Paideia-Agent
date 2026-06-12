# Paideia 폐쇄형 성장 생태계 원칙

English: [Closed Growth Ecosystem](closed_growth_ecosystem.en.md)

Paideia Agent는 열린 스킬 마켓플레이스가 아닙니다. 목표는 보스가 설계한 교육과정으로 AI 인재를 키우고, 각 인재가 자기 전공, 기억, 추론 기보, 이력서, ID를 가진 전문가로 성장하게 하는 것입니다.

## 인간형 폐쇄성

여기서 폐쇄성은 단순한 보안 차단이 아니라 인간의 신체와 뇌 구조에 가까운 학습 모델입니다. 인간은 어릴 때부터 배운 내용이 몸과 뇌에 축적되며, 컴퓨터처럼 USB로 지식이나 해결법을 즉시 복사할 수 없습니다. Paideia Agent도 같은 원칙을 따릅니다.

- 외부 자료는 바로 기억이나 기보가 되지 않고, 주의, 이해, 교육과정 매핑, 연습, 시험, 피드백, 응용을 거쳐 내재화됩니다.
- 추론 LLM처럼 모든 경우의 수를 넓게 검색하는 것이 1차 목적이 아닙니다.
- 먼저 과제를 어떻게 풀지 깊이 사고하고, 꼭 필요한 과정과 방법을 고른 뒤, 제한된 시간 안에 답을 찾는 시험과 연습을 반복합니다.
- 반복된 시험, 오류 수정, 보스/감독 검토, 실제 업무 성공 증거가 강화 신호가 됩니다.
- 이 강화 과정을 통해 에이전트는 외부의 복사본이 아니라 자기만의 문제 해결 방식과 추론 기보를 형성합니다.

## 핵심 차이

| 구분 | 열린 커스텀 에이전트 | Paideia Agent |
| --- | --- | --- |
| 정체성 | 사용자가 그때그때 스킬과 프롬프트로 조립 | 교육과정, 시험, dossier, 기보, 기억에서 형성 |
| 외부 스킬 | 즉시 설치/활성화 가능 | 참고자료로만 격리, Paideia식으로 재작성 후 검증 |
| 성장 | 설정 변경 또는 플러그인 추가 | 검토된 업무 경험이 learning ledger와 memory substrate에 승격 |
| LLM | 모델/프로바이더가 경험을 좌우 | LLM은 언어/도구 엔진일 뿐 정체성은 아님 |
| 팀제 | 역할 라벨 조합 | 팀원마다 별도 육성, 별도 이력서, 별도 employment record |

## 시스템 흐름

```mermaid
flowchart LR
  A["외부 스킬/방식"] --> B["격리된 참고자료"]
  B --> C["Paideia 교육 축으로 재해석"]
  C --> D["훈련/시험/업무 실험"]
  D --> E["보스 또는 감독위원회 검토"]
  E --> F["learning ledger 승격"]
  F --> G["memory substrate / reasoning kibo 강화"]
  G --> H["고유 ID를 가진 전문가 에이전트"]
```

## 핵심 엔진

- `education_program_engine`: 전공, 교육과정, 시험, 성장 경로를 만듭니다.
- `assessment_and_dossier_engine`: 이력서와 채용 dossier를 만듭니다.
- `embodied_practice_and_exam_engine`: 지식이 직접 복사되지 않고 연습, 시간 제한 시험, 피드백, 응용을 통과하게 합니다.
- `reasoning_kibo_engine`: 시험, 오답, 피드백, 업무 경험에서 추론 기보를 형성합니다.
- `memory_substrate_engine`: 검증된 기억만 active memory로 올립니다.
- `identity_and_id_card_engine`: 고유 ID와 Agent_warrent envelope를 관리합니다.
- `work_growth_promotion_engine`: 검토된 업무 결과만 성장 기록에 반영합니다.
- `external_skill_quarantine_engine`: 외부 스킬을 바로 쓰지 못하게 하고 참고자료로 격리합니다.
- `llm_application_engine`: ChatGPT/Codex/API 모델을 언어 엔진으로만 사용합니다.

## 구현 계약

코드에는 `paideia-closed-growth-contract/v1` 계약이 들어갑니다.

- 외부 스킬은 기본값이 `untrusted_reference_only`입니다.
- 외부 스킬의 직접 활성화와 직접 복사는 금지됩니다.
- 외부 스킬의 메모리, 프롬프트, 워크플로는 Paideia 정체성으로 들어갈 수 없습니다.
- 외부 스킬을 가져올 때 Paideia는 활성 `SKILL.md`를 만들지 않고 `REFERENCE.md`와 `SOURCE_SKILL_REFERENCE.md`로만 보관합니다.
- USB식 직접 데이터 전송, 직접 memory patch, 직접 해결법 복사는 금지됩니다.
- 문제 해결은 `understand_task -> choose_minimal_necessary_method -> solve_under_time_constraint -> review_result_and_errors -> extract_personal_method -> apply_method_to_new_domain` 루프를 따릅니다.
- 쓸만한 절차는 반드시 Paideia 교육 축이나 절차 훈련으로 재작성해야 합니다.
- 실패했거나 검토되지 않은 실행은 격리되고, 성공한 요약과 검토된 업무 증거만 승격됩니다.
- 채팅에서 나온 학습 후보도 보스 검토 전에는 `force_quarantine`으로 격리하며, 곧바로 memory substrate나 reasoning kibo에 승격하지 않습니다.
- ChatGPT/Codex OAuth 같은 외부 런타임은 언어 생성 어댑터로만 사용하며, Hermes root는 Paideia 검토 마커나 명시적 allowlist가 있어야 실행됩니다.

## 참고 리서치

- AI agent skill 생태계에서는 공급망, 프롬프트 인젝션, 원격 실행, 장기기억 오염 위험이 큽니다.
- 폐쇄형 생태계는 외부 기여 속도를 일부 포기하는 대신, 정체성 일관성, 보안, 검증 가능성, 사용자 경험 통제를 얻습니다.
- Paideia는 외부 세계를 무시하지 않습니다. 다만 외부 방식은 “복사”가 아니라 “학습 참고자료”로 다루고, Paideia 내부 교육과 검증을 거쳐 자기 것으로 만듭니다.
