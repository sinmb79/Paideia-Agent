# Paideia Agent

[English](README.md) | [한국어](README.ko.md)

Paideia Agent는 로컬 우선 AI 인재 육성 프로그램이자 설치형 에이전트 런타임입니다. 단순히 프롬프트 프로필을 만드는 것이 아니라, 공개 근거가 있는 커리큘럼, 시험, 과제, 피드백, 이력서형 dossier, Reasoning Ledger를 거쳐 고용 가능한 로컬 AI 인재를 만드는 것을 목표로 합니다.

## 핵심 차이

- **먼저 육성하고, 나중에 고용합니다.** 에이전트는 출발점이 아니라 교육을 마친 뒤의 실행 형태입니다.
- **LLM은 엔진입니다.** ChatGPT/Codex, Claude, Gemini, Mistral, OpenRouter, Ollama, LM Studio, GGUF/Transformers 모델은 언어 생성과 추론 엔진으로 연결됩니다. 정체성은 로컬 학습 기록, 성적표, 메모리 기판, Reasoning Ledger에서 옵니다.
- **롤모델은 인격 주입이 아닙니다.** 특정 인물의 성격을 흉내 내는 것이 아니라, 공개적으로 확인 가능한 학습 경로와 과제 압력을 커리큘럼으로 재구성합니다.
- **Reasoning Ledger / Ariadne Thread**는 숨은 chain-of-thought가 아닙니다. 가설, 근거, 반례, 오답, 수정된 원칙, 공부 습관, 업무 경험을 검토 가능한 요약으로 축적하는 성장 기록입니다. 내부 호환 파일명은 `reasoning_kibo.jsonl`입니다.
- **공개 저장소에는 메타데이터만 둡니다.** 개인 학습자료, 로컬 기억, 생성된 에이전트 번들, 모델 체크포인트, 비공개 교재 본문은 GitHub에 올리지 않습니다.

## 온보딩에서 선택할 수 있는 롤모델

첫 직접 테스트 샘플은 `graham_value_investing` 기반의 `grham-junior`입니다. 여기에 더해 에이전트로 자주 쓰이는 분야의 공개 메타데이터 롤모델을 추가했습니다.

| 분야 | 롤모델 프로세스 | 추천 용도 |
| --- | --- | --- |
| `securities_research` | `graham_value_investing` | 증권 리서치, 가치평가, 공시 분석 |
| `software_agent_engineering` | `hopper_software_tooling`, `dijkstra_verified_programming` | 코딩, 디버깅, 개발도구, 정확성 검토 |
| `data_analysis_bi` | `tukey_data_analysis` | 데이터 분석, BI, 실험 해석 |
| `customer_support_quality_ops` | `deming_quality_ops` | 고객지원 품질, 운영개선, 장애 회고 |
| `cybersecurity` | `anderson_security_engineering` | 위협모델링, 보안 리뷰, 개인정보/리스크 분석 |
| `marketing_sales` | `ogilvy_research_copywriting` | 마케팅 리서치, 카피라이팅, 캠페인 테스트 |
| `healthcare_operations` | `nightingale_healthcare_statistics` | 의료 운영/안전 대시보드, 의학적 조언은 제외 |
| `education_tutoring` | `montessori_learning_design` | 튜터링, 학습자 진단, 커리큘럼 설계 |
| `management_productivity` | `drucker_management_knowledge_work` | 의사결정 메모, 경영 보조, 생산성 시스템 |
| `legal_compliance_research` | `ginsburg_legal_research` | 법률/컴플라이언스 리서치, 법률 조언은 제외 |
| `blockchain_protocol_research` | `finney_blockchain_protocol` | 블록체인 프로토콜, 지갑 안전, 투자 조언은 제외 |
| `information_systems_research` | `shannon_information_theory` | 정보이론, 압축, 통신/불확실성 모델링 |

## LLM 선택

온보딩은 OpenClaw/Hermes처럼 먼저 LLM 서비스와 채팅 표면을 고르게 합니다.

지원 선택지:

- `openai_chatgpt_codex`
- `anthropic_claude_api`
- `google_gemini_api`
- `mistral_api`
- `openrouter_api`
- `ollama_local`
- `lm_studio_local`
- `deterministic_local`
- `bigram_local`
- `transformers_local`
- `llama_cpp_local`

외부 API 어댑터는 사용자의 API 키가 있어야 실사용됩니다. 로컬 모델 어댑터는 localhost 또는 로컬 모델 파일을 우선합니다.

## 빠른 실행

```powershell
python -m pip install -e .
$env:PYTHONPATH = "src"
$env:AI22B_STORAGE_ROOT = "$env:USERPROFILE\Documents\22B-AI-local-storage"
```

롤모델 목록:

```powershell
ai22b-talent-foundry list-role-models
ai22b-talent-foundry list-role-models --domain software_agent_engineering
```

Graham Junior 샘플:

```powershell
ai22b-talent-foundry start-console `
  --answers examples\graham_junior_onboarding.answers.json
```

Hopper Junior 예시:

```powershell
ai22b-talent-foundry onboard-agent `
  --request "디버깅, 컴파일러, 테스트, 문서화를 통해 배우는 개발도구 에이전트를 육성한다." `
  --talent-name "hopper-junior" `
  --gender "male" `
  --owner "Boss" `
  --domain software_agent_engineering `
  --role-model hopper_software_tooling `
  --llm-service ollama_local `
  --llm-model "llama3.1:8b" `
  --llm-model-path "http://localhost:11434" `
  --chat-surface codex-bridge-chat
```

## 산출물

육성 후에는 다음과 같은 파일들이 로컬 저장소에 생성됩니다.

- `role_model_profile.json`
- `saju_narrative_seed.json`
- `curriculum_manifest.json`
- `assessment_transcript.json`
- `reasoning_kibo.jsonl`
- `developmental_ecology.json`: 가정/또래/환경/감정회복/미감/문화 경험을 담은 성장 환경 seed
- `life_trace.jsonl`: 0세부터 20세까지의 월별 성장 사건 기록
- `hiring_dossier.json`
- `HIRING_DOSSIER.ko.md`
- `learning_ledger.json`
- `memory_substrate.json`
- `22b_paideia_agent_program.json`
- Hermes/OpenClaw 스타일 어댑터 manifest

## 공개 저장소 규칙

공개 GitHub에는 코드, 문서, 공개 메타데이터, 테스트 픽스처만 올립니다. 아래 항목은 제외합니다.

- `data/private/**`
- `runs/**`
- `apps/*/runs/**`
- 모델 체크포인트
- API 키와 토큰
- 개인 음성/이미지/문서
- 생성된 에이전트 번들

검사:

```powershell
.\scripts\check_public_repo_hygiene.ps1
```

## 더 보기

- [English README](README.md)
- [연구 근거](docs/research_basis.ko.md)
- [Research Basis](docs/research_basis.md)
- [Tesla 기판 벤치마킹](docs/tesla_board_benchmark.ko.md)
- [기존 22B-AI 시스템 통합](docs/legacy_system_integration.ko.md)
