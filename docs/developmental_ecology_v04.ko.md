# v0.4 Developmental Ecology / Life Trace

이 문서는 Paideia Agent v0.4에서 추가된 성장 환경 기록과 생애 사건 기록의 목적, 산출물, 안전 경계를 설명합니다.

## 목적

기존 파이프라인은 커리큘럼, 시험, 리포트, Reasoning Ledger를 중심으로 AI 인재를 육성했습니다. 그러나 보스가 지적한 것처럼 인간형 성장 프로그램에는 학교 공부 이전과 학교 밖의 경험도 필요합니다. `developmental_ecology.json`과 `life_trace.jsonl`은 다음 요소를 기록합니다.

- 가정 분위기, 돌봄 방식, 훈육과 회복 방식
- 또래 관계, 갈등, 사과, 화해, 협업 경험
- 동네, 학교, 도서관, 산책, 계절감 같은 환경 자극
- 미술, 음악, 독서, 운동, 게임, 여행 같은 비학업 경험
- 적절한 스트레스, 실수, 회복, 다음 행동
- 학습과 시험을 통과하며 형성되는 추론 습관의 재료

핵심은 성격 키워드를 직접 주입하지 않는 것입니다. 성장 조건과 경험 사건을 누적하고, LLM은 그 기록과 Reasoning Ledger를 읽어 답변합니다.

## 산출물

`raise` 실행 시 다음 파일이 함께 생성됩니다.

```text
<talent>_developmental_ecology.json
<talent>_life_trace.jsonl
<talent>_memory_substrate.json
```

`developmental_ecology.json`은 성장 환경의 기본 조건입니다.

- `residential_environment`
- `family_climate`
- `peer_world`
- `meaning_system`
- `aesthetic_profile`
- `emotional_development`
- `asymmetry_budget`

`life_trace.jsonl`은 생애 사건 로그입니다. 첫 줄은 manifest이고, 이후 줄은 사건입니다. 기본 밀도는 `monthly`이며 0세부터 20세까지 21년 x 12개월, 총 252개 사건을 만듭니다. 별도 CLI에서는 `daily` 밀도로 7,665개 사건도 만들 수 있습니다.

각 사건은 다음 필드를 가집니다.

- 나이와 성장 단계
- 사건 영역: 가족, 또래, 학교, 미감, 감정 회복, 환경 관찰, 의미 성찰, 전문분야 몰입
- 자극, 도전, 선택, 결과, 회복
- 스트레스 수준
- 기억기판 연결 대상
- 안전 정책

## CLI

개별 산출물을 직접 만들 수도 있습니다.

```powershell
ai22b-talent-foundry build-developmental-ecology `
  --blueprint .\blueprint.json `
  --output .\developmental_ecology.json

ai22b-talent-foundry build-life-trace `
  --blueprint .\blueprint.json `
  --ecology .\developmental_ecology.json `
  --density monthly `
  --output .\life_trace.jsonl
```

`raise` 명령은 위 산출물을 자동 생성하고 release bundle, installed manifest, employment record, memory substrate에 연결합니다.

## 채팅과 연결

채팅 런타임은 `memory_substrate.json`을 우선 읽습니다. v0.4부터 memory substrate는 다음 기록을 함께 노드화합니다.

- `developmental_ecology`: 성장 환경의 의미 기억
- `life_trace`: 성장 사건의 에피소드 기억
- `language_development_program`: 대화와 언어 발달
- `reasoning_kibo.jsonl`: 시험, 과제, 오류, 수정 원칙
- `learning_ledger.json`: 검증된 학습과 업무 경험

따라서 일반 대화, 성장 이야기, 친구와의 갈등, 부모/가족 질문, 학교 경험 질문에 대해 단순한 템플릿 답변이 아니라 누적 기록 기반의 답변을 만들 수 있습니다.

## 안전 경계

이 기능은 다음을 하지 않습니다.

- 실제 가족 개인정보, 실제 주소, 실제 사생활 기록 저장
- 사주를 결정론적 운명, 투자 예언, 성격 확정에 사용
- Benjamin Graham 또는 다른 롤모델의 인격을 복제하거나 사칭
- 숨은 chain-of-thought 저장
- 임상 진단 또는 차별적 분류

사주는 시뮬레이션 공백을 채우는 상징적 초기 조건으로만 사용됩니다. 롤모델은 답변 스타일을 주입하는 대상이 아니라, 공개 근거가 있는 학습 과정과 평가 압력을 제공하는 참고 경로입니다.

## 다음 단계

v0.4는 기본 골격입니다. 다음 개발에서는 다음을 보강합니다.

- 온보딩에서 life trace 밀도와 성장 환경 프리셋 선택
- 시험/과제 결과가 life trace와 Reasoning Ledger를 함께 갱신하는 학년별 루프
- 채팅 답변에서 life trace 사건 검색 결과를 더 자연스럽게 요약하는 live LLM 브리지
- Graham 외 롤모델별 전용 생애/학습 사건 템플릿
- 사용자 제공 로컬 교재와 공개 자료를 구분하는 curriculum ingest 정책 강화

## v0.8 보완: grade learning records

`grade_learning_records.json`은 위의 다음 단계 중 "시험/과제 결과가 life trace와 Reasoning Ledger를 함께 갱신하는 학년별 루프"를 구현한 산출물입니다.

- 초등학교부터 대학원/박사급 연구, 고용 후 성장까지 각 `year_id`별 기록을 만듭니다.
- 각 기록은 `learning_data`, `assignments`, `required_exams`, `observed_assessments`, `life_trace_links`, `reasoning_ledger_updates`, `feedback_loop`를 가집니다.
- 숨은 chain-of-thought는 저장하지 않고, 시험 결과와 생활 스트레스가 다음 학습 습관을 어떻게 수정했는지 검토 가능한 요약만 남깁니다.
- `raise` 실행 시 release bundle, installed manifest, employment record, `memory_substrate.json`에 함께 연결됩니다.
