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
- `openclaw_gateway_http`
- `deepseek_api`, `groq_api`, `gmi_api`, `novita_api`, `huggingface_api`, `kilocode_gateway`
- `xai_api`, `perplexity_api`, `together_ai`, `fireworks_api`, `deepinfra_api`
- `arcee_api`, `chutes_api`, `qianfan_api`, `stepfun_api`, `stepfun_plan_api`
- `volcengine_api`, `volcengine_plan_api`, `xiaomi_api`, `xiaomi_token_plan_api`
- `minimax_api`, `inferrs_local`
- `ollama_local`
- `ollama_cloud`
- `lm_studio_local`
- `vllm_local`, `sglang_local`, `litellm_gateway`
- `deterministic_local`
- `bigram_local`
- `transformers_local`
- `llama_cpp_local`

`openclaw_gateway_http`를 선택하면 Paideia는 OpenClaw Gateway의 `openclaw/default` agent target으로 요청을 보내고, 실제 backend provider/model은 `x-openclaw-model` 헤더로 넘깁니다. 즉 OpenClaw 쪽 provider 인증과 라우팅을 그대로 쓰면서 Paideia의 로컬 성장 기록과 Reasoning Ledger를 대화 context로 넣는 방식입니다.

Gateway를 실제 LLM 브리지로 쓰기 전에는 `doctor-openclaw-gateway-llm`을 실행해 employment record, config patch, `x-openclaw-model` 헤더, Gateway 인증 환경변수, `/v1/chat/completions` smoke test 준비 상태를 확인할 수 있습니다. 정적 doctor는 네트워크를 호출하지 않고, `--probe-gateway --probe-chat`을 붙인 경우에만 실행 중인 OpenClaw Gateway에 실제 probe를 보냅니다.

온보딩을 완료하면 `openclaw_runtime_bundle` 폴더가 함께 생성됩니다. 이 폴더에는 provider/channel doctor, API key/OAuth/local server/Gateway 준비 상태를 보는 provider auth doctor, QR/session/local bridge 준비 상태를 보는 channel pairing doctor, `openclaw_config_patch.json`, WebChat/channel gateway 설정, OpenClaw bridge setup kit, native OpenClaw handoff, 그리고 `openclaw_gateway_http` 선택 시 `openclaw_gateway_llm_doctor.json`이 포함됩니다.

외부 API 어댑터는 사용자의 API 키가 있어야 실사용됩니다. 로컬 모델 어댑터는 localhost 또는 로컬 모델 파일을 우선합니다. OpenClaw의 canonical `provider/model` 형식도 지원하므로 `kilocode/kilo/auto`, `gmi/google/gemini-3.1-flash-lite`, `ollama-cloud/kimi-k2.6`, `zai/glm-5.1`, `lmstudio/<local-model>` 같은 입력을 온보딩에서 해석합니다.

고용 이후의 업무 실행도 같은 LLM 선택값을 사용할 수 있습니다. 기본값은 안전한 `offline` 모드이며, provider API 키, 로컬 모델 서버, 또는 OpenClaw Gateway가 준비된 경우에만 `--live-llm` 또는 `--llm-mode live`를 붙여 실제 LLM 호출을 수행합니다.

```powershell
ai22b-talent-foundry run-hired-agent `
  --employment-record "<employment_record.json>" `
  --task "가치평가 메모 초안을 작성해줘" `
  --live-llm

ai22b-talent-foundry run-hired-agent-job `
  --employment-record "<employment_record.json>" `
  --job-spec "<job_spec.json>" `
  --workspace "$env:AI22B_STORAGE_ROOT\talent-foundry\workspaces\job-001" `
  --llm-mode live
```

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

제품형 smoke test를 한 번에 실행하려면 Graham Junior quickstart report를 사용합니다. 이 명령은 샘플을 육성하고, 성적표와 hiring dossier를 만들고, 첫 로컬 채팅을 실행하고, OpenClaw channel flow doctor까지 돌립니다.

```powershell
ai22b-talent-foundry run-graham-junior-quickstart `
  --llm-service "openclaw-gateway/openrouter/meta-llama/llama-3.1-8b" `
  --llm-model-path "http://127.0.0.1:18789" `
  --chat-surface openclaw-channel-webchat `
  --channel webchat
```

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

채널 연결을 한 번에 점검하려면 flow doctor를 실행합니다. 이 명령은 Paideia chat runtime을 실제로 통과시킨 뒤, Telegram/Discord/Slack은 외부 전송 없이 dry-run outbound payload까지 생성합니다.

```powershell
ai22b-talent-foundry doctor-openclaw-channel-flow `
  --employment-record "<employment_record.json>" `
  --channel telegram `
  --channel webchat `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_channel_flow_doctor.json"
```

이 서버는 `POST /openclaw/channel-message`를 받아 Paideia 인재에게 전달하고, 원래 들어온 채널/세션으로 되돌려 보낼 outbound envelope를 반환합니다. 실제 플랫폼 토큰, 페어링, 허용목록, 최종 전송은 채널 플러그인이 담당합니다.

실제 플랫폼 webhook/event payload는 먼저 deny-by-default ingress layer에서 표준 envelope로 번역합니다.

```powershell
ai22b-talent-foundry build-openclaw-channel-access-config `
  --channel telegram `
  --allow-sender "telegram:12345" `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\channel_access.json"

ai22b-talent-foundry translate-openclaw-platform-event `
  --channel telegram `
  --event ".\telegram_update.json" `
  --access-config "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\channel_access.json" `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\telegram_translation.json"
```

## OpenClaw native 설정 병합

`prepare-openclaw-native-config`는 Paideia의 `openclaw_native_handoff.json`과 `openclaw_config_patch.json`을 기존 OpenClaw 설정에 안전하게 합치는 명령입니다. 기본 `plan` 모드는 설정 파일을 쓰지 않고 secret이 제거된 병합 보고서만 만듭니다. `write-copy`는 `--merged-output`을 명시했을 때만 로컬 병합본을 만들며, `apply`는 `--confirm-apply`가 있을 때만 백업 후 실제 OpenClaw 설정에 씁니다.

```powershell
ai22b-talent-foundry prepare-openclaw-native-config `
  --handoff "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_handoff.json" `
  --mode plan `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_config_merge.plan.json"
```

고용된 인재를 OpenClaw식 실행 환경으로 넘기려면 runtime bundle을 생성합니다. 이 번들은 선택된 `provider/model`, `models.providers`, `agents.list`, gateway URL, enabled channels, `channels.modelByChannel`, `bindings[]`를 담은 검토용 `openclaw_config_patch.json`, provider/channel plugin 계획과 smoke-test payload를 담은 `openclaw_bridge_setup/`, 실제 OpenClaw CLI/gateway로 넘길 때 볼 수 있는 `openclaw_native_handoff.json`을 만듭니다.

```powershell
ai22b-talent-foundry build-openclaw-runtime-bundle `
  --employment-record "<employment_record.json>" `
  --channel webchat `
  --channel telegram `
  --channel-model "telegram:boss-thread=openrouter/meta-llama/llama-3.1-8b" `
  --binding "telegram:boss-thread=paideia-graham-junior" `
  --existing-openclaw-config "$env:USERPROFILE\.openclaw\openclaw.json" `
  --config-action modify `
  --output-dir "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle"
```

실제 사용 전에 runtime preflight를 실행하면 현재 provider 인증, 채널 QR/session/local bridge 준비, native handoff 계획, Gateway LLM 계약, 선택적 channel-flow dry run을 한 번에 점검할 수 있습니다. 기본 실행은 네트워크를 호출하지 않고, `--probe-openclaw`, `--probe-gateway`, `--probe-chat`을 명시했을 때만 설치된 OpenClaw 또는 Gateway에 probe를 보냅니다.

```powershell
ai22b-talent-foundry doctor-openclaw-runtime-preflight `
  --runtime-bundle "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_runtime_bundle.json" `
  --run-channel-flow `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_runtime_preflight.json"
```

OpenClaw 설치본에 넘기기 전에는 native handoff doctor를 먼저 실행합니다. 기본값은 비파괴 점검이며 OpenClaw 명령을 실행하지 않습니다. 설치된 OpenClaw CLI의 읽기성 상태까지 확인하려면 `--probe-openclaw`를 추가합니다.

```powershell
ai22b-talent-foundry doctor-openclaw-native-handoff `
  --handoff "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_handoff.json" `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_handoff_doctor.json"
```

gateway 서버를 `--access-config`와 함께 실행하면 `/openclaw/platform-event/telegram`, `/discord`, `/slack` 경로로 들어온 raw event도 처리합니다. 허용목록에 없는 sender/conversation은 403으로 차단됩니다.

import나 runtime bundle 이후 실제 연결 준비를 한 번에 점검하려면 bridge setup kit를 생성합니다. 이 명령은 provider 환경변수 템플릿, OpenClaw provider plugin/OAuth 계획, provider auth doctor, channel bridge 계획, QR/session/local bridge pairing doctor, 기본 차단 접근제어, smoke test payload를 함께 만듭니다.

```powershell
ai22b-talent-foundry build-openclaw-bridge-setup-kit `
  --import-manifest "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_import\paideia_openclaw_config_import.json" `
  --provider qwen-oauth `
  --channel webchat `
  --channel telegram `
  --output-dir "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_bridge_setup"
```

OpenClaw 전체 채널의 준비 상태는 connector catalog/doctor로 확인합니다.

```powershell
ai22b-talent-foundry audit-openclaw-parity `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_parity_audit.json" `
  --fail-on-missing

ai22b-talent-foundry audit-openclaw-parity `
  --refresh-docs `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_parity_live_docs.json" `
  --fail-on-missing

ai22b-talent-foundry build-openclaw-support-matrix `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_support_matrix.json"

ai22b-talent-foundry build-openclaw-onboarding-menu `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_onboarding_menu.json" `
  --markdown-output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\OPENCLAW_ONBOARDING_MENU.md"

ai22b-talent-foundry doctor-openclaw-selection `
  --llm-service "openclaw-gateway/openrouter/meta-llama/llama-3.1-8b" `
  --llm-model-path "http://127.0.0.1:18789/v1" `
  --chat-surface openclaw-channel-webchat `
  --channel telegram `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_selection_doctor.json" `
  --summary-output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\OPENCLAW_SELECTION_SUMMARY.md"

ai22b-talent-foundry list-openclaw-provider-connectors `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\provider_connectors.json"

ai22b-talent-foundry doctor-openclaw-provider-connectors `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\provider_connector_doctor.json"

ai22b-talent-foundry doctor-openclaw-provider-auth `
  --provider qwen-oauth `
  --provider arcee `
  --openclaw-config "$env:USERPROFILE\.openclaw\openclaw.json" `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\provider_auth_doctor.json"

ai22b-talent-foundry list-openclaw-channel-connectors `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\channel_connectors.json"

ai22b-talent-foundry doctor-openclaw-channel-connectors `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\channel_connector_doctor.json"

ai22b-talent-foundry doctor-openclaw-channel-pairing `
  --channel whatsapp `
  --channel signal `
  --channel imessage `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\channel_pairing_doctor.json"
```

`build-openclaw-support-matrix`는 설치자가 보는 한 장짜리 지원범위 표입니다. OpenClaw provider와 channel을 Paideia 직접 지원, OpenClaw Gateway 준비, 로컬 서버 준비, 플러그인/OAuth/bridge 필요 항목으로 나누고 Graham Junior quickstart, provider doctor, channel flow doctor, Gateway LLM doctor, parity audit 명령을 함께 기록합니다. `build-openclaw-onboarding-menu`는 이 전체 matrix를 첫 실행 선택 메뉴로 바꿉니다. 터미널에는 추천 선택지만 짧게 보여주고, `OPENCLAW_ONBOARDING_MENU.md`에는 모든 OpenClaw provider/channel을 남깁니다. 이제 모든 온보딩 실행은 `openclaw_support_matrix.json`, `openclaw_onboarding_menu.json`, markdown menu를 자동으로 만들고, 사용자가 고른 provider/channel 지원 등급을 `onboarding_session.json` 안에 함께 저장합니다. `doctor-openclaw-selection`은 온보딩 전에 특정 provider/model과 채팅 채널 조합을 미리 확인하는 명령이며, 외부 네트워크 호출과 비밀값 저장을 하지 않습니다. `--bridge-setup-dir <dir>`을 붙이면 해당 선택 조합에 맞는 env 템플릿, provider plugin/OAuth 계획, channel plugin 계획, 기본 차단 접근제어, smoke-test payload까지 함께 생성합니다. guided console은 인재 육성 전에 `openclaw_selection_doctor.json`, `OPENCLAW_SELECTION_SUMMARY.md`, `openclaw_bridge_setup/` kit를 먼저 생성하고, 터미널에도 provider, LLM health, channel support level, bridge setup kit path, summary path를 짧게 출력합니다.

`audit-openclaw-parity`는 Paideia의 로컬 provider/channel catalog가 확인된 OpenClaw 공식 문서 snapshot을 빠짐없이 덮는지 검사합니다. `--refresh-docs`를 붙이면 현재 OpenClaw 공식 문서를 다시 가져와 drift를 계산하고, 새 provider/channel 문서 URL이 생겼는데 Paideia 매핑에 없으면 unknown doc slug로 보고해 조용히 누락되지 않게 합니다. provider doctor는 OpenClaw Provider directory의 `provider/model` 항목을 Paideia live adapter, 로컬 서버, OpenClaw 플러그인/OAuth/custom runner 필요 항목으로 나눕니다. API 키 값은 저장하지 않고 환경변수 이름과 준비 여부만 기록합니다.

`doctor-openclaw-provider-auth`는 LLM 쪽 channel pairing doctor입니다. 직접 API key provider, 로컬 모델 서버, Codex host bridge, OpenClaw OAuth/account-session provider, cloud profile provider, media/custom-runner plugin을 분리합니다. Paideia가 직접 호출하지 않고 OpenClaw가 소유해야 하는 provider는 `openclaw onboard`, model auth 검토, Gateway 실행, `doctor-openclaw-gateway-llm` 순서로 안내합니다. 이 doctor는 환경변수 존재 여부, redacted config hint, readiness category만 기록하며 비밀값과 로컬 config 절대경로 값은 저장하지 않습니다.

사용자가 `qwen-oauth/qwen3-coder-plus`, `github-copilot/<model>`, `opencode/<model>`처럼 Paideia가 직접 호출하지 않고 OpenClaw provider plugin/OAuth/custom runner가 필요한 `provider/model`을 입력하면, Paideia는 이를 `openclaw_gateway_http`로 자동 라우팅합니다. 원래 입력한 selector는 `openclaw_model`로 보존되므로 OpenClaw가 provider 인증과 실제 backend 호출을 맡고, Paideia는 로컬 인재 context와 Reasoning Ledger를 Gateway 요청에 붙이는 방식으로 동작합니다.

OpenClaw식 key resolution도 반영합니다. Paideia는 `OPENCLAW_LIVE_<PROVIDER>_KEY`, `<PROVIDER>_API_KEYS`, `<PROVIDER>_API_KEY`, 그리고 `ARCEEAI_API_KEY`, `VOLCANO_ENGINE_API_KEY`, `DASHSCOPE_API_KEY`, `XIAOMI_TOKEN_PLAN_API_KEY` 같은 provider별 환경변수를 확인합니다. 쉼표/세미콜론 key list가 있으면 첫 번째 non-empty key를 live smoke test에 사용합니다.

Telegram, Discord, Slack, Google Chat, LINE, Matrix, Mattermost, SMS, Synology Chat, WebChat은 Paideia 직접 adapter가 있습니다. 일반 HTTP API나 webhook을 제공하는 채널은 검토된 inbound/outbound gateway flow로 바로 테스트할 수 있습니다. 현재 OpenClaw iMessage 지원은 `imessage`/`imsg` 경로가 기준이며, `bluebubbles`는 기존 설정을 옮기기 위한 legacy migration 대상으로만 표시합니다. `clickclack`과 `qa-channel`도 catalog에 포함되어 각각 bot-token plugin, deterministic QA scenario plugin으로 표시됩니다. 나머지 OpenClaw 채널은 normalized gateway envelope를 사용할 수 있지만 WhatsApp QR pairing, signal-cli, Bot Framework, 지역 계정/session plugin처럼 raw platform bridge가 필요한 항목은 doctor가 별도 준비 단계로 표시합니다.

`doctor-openclaw-channel-pairing`은 일반 webhook만으로 끝나지 않는 채널의 실사용 준비 상태를 따로 보여줍니다. WhatsApp, WeChat, Zalo Personal 같은 QR session 채널, Signal/iMessage 같은 local bridge 채널, Microsoft Teams 같은 enterprise bot 설정, BlueBubbles 같은 legacy migration 경로를 분리합니다. 이 doctor는 환경변수 존재 여부, path 존재 여부의 불리언, 다음 조치만 기록하며 QR session, 전화번호, 토큰, 쿠키, 로컬 절대경로 값은 저장하지 않습니다.

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

## OpenClaw 설정으로 바로 고용하기

기존 OpenClaw 설정을 그대로 이어서 고용하려면 `hire-installed --openclaw-config`를 사용합니다. Paideia는 OpenClaw의 `provider/model` 선택과 첫 채팅 채널을 읽어 고용 기록의 LLM/채팅 런타임에 반영하고, API 키와 봇 토큰은 저장하지 않습니다.

```powershell
ai22b-talent-foundry hire-installed `
  --installed-manifest "<installed_agent_manifest.json>" `
  --role "Research agent" `
  --openclaw-config "$env:USERPROFILE\.openclaw\openclaw.json"
```

## OpenClaw 라이브 스모크 플랜

고용된 에이전트를 실제 OpenClaw Gateway, LLM, 채팅 채널과 연결하기 전에는 `build-openclaw-live-smoke-plan`으로 검증 순서를 먼저 뽑습니다. 이 명령 자체는 네트워크 호출을 하지 않고, 오프라인 컨텍스트 확인, 런타임 번들 생성, 정적 preflight, Gateway probe, live LLM chat, 채널 메시지 smoke test 명령을 한 파일로 정리합니다.

```powershell
ai22b-talent-foundry build-openclaw-live-smoke-plan `
  --employment-record "<employment_record.json>" `
  --channel webchat `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_live_smoke_plan.json" `
  --markdown-output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\OPENCLAW_LIVE_SMOKE_PLAN.md"
```

`start-console`과 `onboard`도 이제 고용이 끝난 직후 같은 smoke plan을 자동으로 생성합니다. 그래서 첫 실행 폴더 안에서 교육/고용 산출물과 OpenClaw 라이브 검증 순서를 함께 확인할 수 있습니다.

## WebChat 런타임 패널

WebChat 화면과 `/api/runtime`, `/api/smoke-plan`은 선택된 OpenClaw provider/model, 채팅 surface, 채널 경로, live smoke-test 순서를 함께 보여줍니다. API 키, 봇 토큰, OAuth refresh token, QR 세션, 비공개 학습 파일은 읽거나 저장하지 않습니다.

## 설치 Kit에서 바로 쓰는 OpenClaw식 실행 흐름

`build-paideia-agent-kit`으로 만든 설치 폴더에는 이제 저장소 CLI를 다시 찾아가지 않아도 되는 PowerShell 진입점이 함께 들어갑니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\doctor_paideia.ps1
powershell -ExecutionPolicy Bypass -File .\start_paideia_chat.ps1
powershell -ExecutionPolicy Bypass -File .\refresh_openclaw_onboarding_menu.ps1
powershell -ExecutionPolicy Bypass -File .\build_openclaw_runtime_bundle.ps1 -Channel webchat
powershell -ExecutionPolicy Bypass -File .\build_openclaw_live_smoke_plan.ps1 -Channel webchat
powershell -ExecutionPolicy Bypass -File .\start_openclaw_webchat.ps1 -Port 8722
```

- `refresh_openclaw_onboarding_menu.ps1`: OpenClaw가 지원하는 provider/channel 목록을 kit 안의 `OPENCLAW_ONBOARDING_MENU.md`와 JSON으로 갱신합니다. `-RefreshDocs`를 붙이면 현재 공식 OpenClaw 문서와 비교합니다.
- `build_openclaw_runtime_bundle.ps1`: 고용 기록을 기준으로 OpenClaw provider/model/channel 선택과 gateway 설정 파일을 생성합니다.
- `build_openclaw_live_smoke_plan.ps1`: 실제 API 키나 외부 채널을 쓰기 전에 실행 순서, 필요한 준비물, live probe 명령을 no-secret 문서로 뽑습니다.
- `start_openclaw_webchat.ps1`: 외부 봇 토큰 없이 `127.0.0.1`에서 브라우저 채팅창을 열어 설치된 인재를 테스트합니다.

WebChat은 `/api/runtime`과 `/api/smoke-plan`을 함께 제공하므로, 사용자는 현재 선택된 LLM 서비스, 모델, 채널 경로, smoke-test 순서를 확인한 뒤 실제 Gateway나 외부 채널 연결을 진행할 수 있습니다.
