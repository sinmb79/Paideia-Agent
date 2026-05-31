# Paideia Agent

[English](README.md) | [한국어](README.ko.md)

Paideia Agent는 로컬 우선 AI 인재 육성 프로그램이자 설치형 에이전트 런타임입니다. 단순히 프롬프트 프로필을 만드는 것이 아니라, 공개 근거가 있는 커리큘럼, 시험, 과제, 피드백, 이력서형 dossier, Reasoning Ledger를 거쳐 고용 가능한 로컬 AI 인재를 만드는 것을 목표로 합니다.

## 발단

Paideia Agent는 "나 자신을 확장한 AI 에이전트가 있다면?", "내가 존경하는 분야별 롤모델의 학습 과정을 따라 AI 인재를 키울 수 있다면?"이라는 질문에서 출발했습니다.

이 프로젝트는 특정 인물을 그대로 복제하거나 흉내 내겠다는 뜻이 아닙니다. 공개적으로 확인 가능한 성장 조건, 학습 경로, 시험, 과제, 실패, 회복, 업무 경험을 커리큘럼으로 재구성하고, AI가 그 과정을 통과하면서 자기만의 Reasoning Ledger를 쌓게 하는 실험입니다.

자세한 설명:

- [프로젝트 선언문](docs/project_manifesto.ko.md)
- [Project Manifesto](docs/project_manifesto.md)
- [설명문 기준 구현 정합성 검토](docs/manifesto_alignment_review.ko.md)

## 핵심 차이

- **먼저 육성하고, 나중에 고용합니다.** 에이전트는 출발점이 아니라 교육을 마친 뒤의 실행 형태입니다.
- **LLM은 엔진입니다.** ChatGPT/Codex, Claude, Gemini, Mistral, OpenRouter, Ollama, LM Studio, GGUF/Transformers 모델은 언어 생성과 추론 엔진으로 연결됩니다. 정체성은 로컬 학습 기록, 성적표, 메모리 기판, Reasoning Ledger에서 옵니다.
- **롤모델은 인격 주입이 아닙니다.** 특정 인물의 성격을 흉내 내는 것이 아니라, 공개적으로 확인 가능한 학습 경로와 과제 압력을 커리큘럼으로 재구성합니다.
- **Reasoning Ledger / Ariadne Thread**는 숨은 chain-of-thought가 아닙니다. 가설, 근거, 반례, 오답, 수정된 원칙, 공부 습관, 업무 경험을 검토 가능한 요약으로 축적하는 성장 기록입니다. 내부 호환 파일명은 `reasoning_kibo.jsonl`입니다.
- **군체능력은 본체 제어 분신입니다.** 별도 의식을 만드는 것이 아니라, 하나의 고용된 인재가 역할별 작업 투영체를 띄우고 본체가 결과를 합성합니다.
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
- `deepseek_api`, `groq_api`, `gmi_api`, `novita_api`, `huggingface_api`, `kilocode_gateway`
- `xai_api`, `perplexity_api`, `together_ai`, `fireworks_api`, `deepinfra_api`
- `ollama_local`
- `ollama_cloud`
- `lm_studio_local`
- `vllm_local`, `sglang_local`, `litellm_gateway`
- `deterministic_local`
- `bigram_local`
- `transformers_local`
- `llama_cpp_local`

외부 API 어댑터는 사용자의 API 키가 있어야 실사용됩니다. 로컬 모델 어댑터는 localhost 또는 로컬 모델 파일을 우선합니다. OpenClaw의 canonical `provider/model` 형식도 지원하므로 `kilocode/kilo/auto`, `gmi/google/gemini-3.1-flash-lite`, `ollama-cloud/kimi-k2.6`, `zai/glm-5.1`, `lmstudio/<local-model>` 같은 입력을 온보딩에서 해석합니다.

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

대화형 첫 실행은 OpenClaw식 별칭을 사용할 수 있습니다.

```powershell
ai22b-talent-foundry onboard
```

이 wizard는 기존 설정 감지, QuickStart/Advanced, Model/Auth, Workspace, Gateway/Channels, Skills, Education Path, Runtime, Agent Identity, Health Check, Finish 순서로 진행합니다.

고용된 에이전트를 브라우저 채팅으로 바로 테스트하려면 로컬 WebChat 서버를 실행합니다.

```powershell
ai22b-talent-foundry run-openclaw-webchat-server `
  --employment-record "<employment_record.json>" `
  --port 8722
```

기본 바인딩은 `127.0.0.1`이며, 메시지는 OpenClaw식 `webchat` 채널 envelope를 거쳐 Paideia 인재의 로컬 기억/추론 자료를 읽고 답합니다.

Telegram/Discord/Slack 같은 외부 채널 플러그인이 붙을 때는 로컬 channel gateway 서버를 실행합니다.

```powershell
ai22b-talent-foundry run-openclaw-channel-gateway-server `
  --employment-record "<employment_record.json>" `
  --channel telegram `
  --channel discord `
  --channel slack `
  --port 8722
```

이 서버는 `POST /openclaw/channel-message`를 받아 Paideia 인재에게 전달하고, 원래 들어온 채널/세션으로 되돌려 보낼 outbound envelope를 반환합니다. 실제 플랫폼 토큰, 페어링, 허용목록, 최종 전송은 채널 플러그인이 담당합니다.

반환된 outbound envelope는 기본 dry-run delivery adapter로 먼저 검토할 수 있습니다.

```powershell
ai22b-talent-foundry build-openclaw-channel-delivery-config `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\channel_delivery_config.json"

ai22b-talent-foundry send-openclaw-channel-outbound `
  --channel-run "<channel_run.json>" `
  --mode dry-run `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\channel_delivery_dry_run.json"
```

`--mode live`를 명시하고 필요한 환경변수(`TELEGRAM_BOT_TOKEN`, `SLACK_BOT_TOKEN`, `DISCORD_WEBHOOK_URL` 또는 `DISCORD_BOT_TOKEN`)가 있을 때만 외부 전송을 시도합니다. 토큰 값은 산출물에 저장하지 않습니다.

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
- [프로젝트 선언문](docs/project_manifesto.ko.md)
- [설명문 기준 구현 정합성 검토](docs/manifesto_alignment_review.ko.md)
- [연구 근거](docs/research_basis.ko.md)
- [Research Basis](docs/research_basis.md)
- [OpenClaw식 온보딩](docs/openclaw_style_onboarding.ko.md)
- [Tesla 기판 벤치마킹](docs/tesla_board_benchmark.ko.md)
- [기존 22B-AI 시스템 통합](docs/legacy_system_integration.ko.md)

## 이번 보완 개발

- 온보딩은 선택한 LLM에 대해 `llm_service_health.json`을 생성합니다. API 키가 필요한지, 로컬 모델 경로가 빠졌는지, Codex bridge만 준비된 상태인지 확인하며 비밀값은 저장하지 않습니다.
- `ingest-owner-self-extension` 명령은 보스가 승인한 로컬 자료 폴더를 스캔해 상대경로, 해시, 파일 크기, 분류, 짧은 키워드만 저장합니다. 기본값은 본문을 저장하지 않으므로 공개 저장소에 올릴 데이터와 분리됩니다.
- `run-simulation-rollouts` 명령은 채용된 에이전트가 여러 스트레스 상황을 시뮬레이션으로 연습한 뒤, 검증된 에피소드만 Reasoning Ledger에 승격합니다. 검토가 필요한 에피소드는 격리되어 보스의 리뷰를 기다립니다.

```powershell
ai22b-talent-foundry check-llm-service `
  --llm-service ollama_local `
  --llm-model "llama3.1:8b" `
  --llm-model-path "http://localhost:11434" `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\llm_service_health.json"

ai22b-talent-foundry ingest-owner-self-extension `
  --source-dir "C:\path\to\owner-approved-materials" `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\owner_self_extension_manifest.json"

ai22b-talent-foundry run-simulation-rollouts `
  --employment-record "<employment_record.json>" `
  --rollouts "<simulation_rollouts.json>" `
  --workspace "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\simulation_rollout_workspace" `
  --reviewed-by "보스" `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\simulation_rollout_execution.json"
```
