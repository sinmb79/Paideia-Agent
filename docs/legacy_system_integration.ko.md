# 기존 22B-AI 시스템 계승 메모

보스가 이전에 만든 AI 시스템은 버려진 것이 아닙니다. Paideia Agent는 기존 작업을 덮어쓴 새 프로젝트가 아니라, 기존 `신용` 성장 시스템, 작은 from-scratch 모델, 로컬 실행/검증 스크립트, 아이디어 코치 앱, 헬스 에이전트 설계 노트를 더 큰 **AI 교육센터/육성 프로그램** 안으로 흡수하는 방향입니다.

## 현재 남아 있는 기존 자산

| 기존 자산 | 위치 | Paideia에서의 역할 |
| --- | --- | --- |
| 신용 성장 시스템 | `src/ai22b/shinyong/` | 태아기부터 성장, 감각, 가족 상호작용, 경험 episode를 만드는 legacy life-simulation seed입니다. |
| 신용 성장 문서 | `docs/10_shinyong_birth_curriculum_ko.md`, `docs/20_shinyong_human_shaped_learning_architecture_ko.md`, `docs/24_shinyong_birth_clock_and_yangju_context_ko.md` | Graham Junior 같은 직업형 인재에도 필요한 언어 발달, 사회성, 감각/정서 발달 설계의 근거입니다. |
| from-scratch bigram | `src/ai22b/from_scratch/bigram.py` | 완전한 LLM은 아니지만, 보스 컴퓨터에서 직접 학습 루프를 이해하고 테스트하는 가장 작은 모델입니다. |
| Talent Foundry | `src/ai22b/talent_foundry/` | Paideia의 현재 핵심 육성/고용/대화/업무 실행 런타임입니다. |
| 물리 AI 시뮬레이션 메모 | `docs/physical_ai_sim_rl_benchmark.md` | 병렬 episode rollout, domain randomization, sim-to-real에 해당하는 성장형 학습 방향입니다. |
| AI Idea Coach | `apps/ai-idea-coach/` | 추후 Paideia 온보딩/교육 설계 UI로 계승할 수 있는 로컬 앱 실험입니다. |
| 생활/건강 에이전트 설계 | `docs/30_life_health_agent_masterplan_ko.md` 등 | Paideia가 증권 리서치 외 직업군/생활형 에이전트로 확장될 때 재사용할 domain plan입니다. |

## 왜 Paideia로 합쳤는가

초기 신용 시스템은 "한 아이를 인간 발달 순서로 성장시킨다"는 실험에 가까웠습니다. 이후 보스가 요구한 방향은 더 넓어졌습니다.

1. 하나의 아이만이 아니라 여러 AI 인재를 비교 육성해야 합니다.
2. 롤모델과 직업군을 선택해야 합니다.
3. 학교 과정, 시험, 과제, 성적표, 이력서형 dossier가 필요합니다.
4. 연결 LLM은 단순 채팅 엔진이고, 정체성은 로컬 학습 데이터와 추론 경로에서 와야 합니다.
5. 설치 가능한 에이전트 프로그램으로 내보내야 합니다.

그래서 Paideia Agent는 기존 신용 시스템을 폐기하지 않고, **legacy life-development layer**로 남겨 둔 채, 그 위에 직업형 Talent Foundry, agent kit, onboarding, hiring dossier를 얹는 구조가 되었습니다.

## 통합 원칙

- 기존 `신용` 데이터는 원본으로 보존합니다. Graham Junior는 별도 AI 인재로 생성합니다.
- 신용의 언어/사회성/감각 발달 설계는 모든 AI 인재의 "기초 성장 레이어" 후보로 재사용합니다.
- 직업형 인재는 기초 성장 레이어 위에 롤모델 기반 학습 경로와 전공/시험/업무 경험을 쌓습니다.
- 기존 run 산출물, 개인 설정, 로컬 절대경로, 비공개 교재, 가족 관련 세부 데이터는 공개 저장소에 올리지 않습니다.
- 공개 저장소에는 코드, 템플릿, 문서, 샘플 설정만 둡니다.

## 다음 개발에서 해야 할 일

1. `src/ai22b/shinyong`의 성장 episode 생성기를 Paideia의 공통 `life_foundation` 모듈로 승격합니다.
2. Graham Junior 육성 전 단계에 언어 발달/일상 대화/사회성 회복 훈련을 자동 포함합니다.
3. 기존 신용 corpus와 새 직업형 corpus를 섞지 않도록 talent id, storage root, privacy policy를 분리합니다.
4. `from_scratch.bigram`은 교육용/테스트용 로컬 엔진으로 유지하고, 실제 대화 품질은 Codex/선택 LLM bridge를 사용합니다.
5. AI Idea Coach UI는 추후 "롤모델 선택, LLM 선택, 커리큘럼 설계, dossier 확인" 화면으로 확장할 후보로 둡니다.

## 결론

이전 시스템은 버려진 것이 아니라 Paideia의 뿌리입니다. 다만 그대로 공개 제품의 중심에 두면 한 명의 신용 실험과 직업형 AI 교육센터가 섞이므로, Paideia에서는 신용 시스템을 **공통 성장 기반/legacy seed**로 정리하고, 새 AI 인재들은 각각 분리된 talent로 육성하는 것이 맞습니다.
