# Paideia Agent 연구 근거와 반영 내용

이 문서는 참고한 프로그램, 연구논문, 보고서가 Paideia Agent의 어떤 설계로 이어졌는지 정리합니다. 단순 참고 목록이 아니라, 실제 제품에 반영된 내용을 함께 기록합니다.

## 에이전트 프로그램

| 출처 | 확인한 점 | Paideia Agent 반영 |
| --- | --- | --- |
| OpenClaw 온보딩 | 첫 실행에서 provider/model, gateway, 채팅/채널, 스킬, 다음 단계를 선택하게 해야 합니다. | `start-console`이 LLM 서비스와 채팅 표면을 먼저 묻고, `paideia_onboarding.template.json`에 선택값과 카탈로그를 기록합니다. 또한 runtime bundle은 `OPENCLAW_NATIVE_ONBOARDING_RUNBOOK.md`를 생성해 `openclaw onboard` -> model/auth -> workspace -> Gateway -> channel pairing -> `openclaw agents add` -> health/smoke test 흐름을 그대로 따라가게 합니다. `doctor-openclaw-installed-runtime`은 실제 설치된 OpenClaw CLI/config/Gateway/model/channel 상태를 읽되, 홈 경로, 이메일, secret-like 값을 가린 진단 JSON만 남깁니다. |
| OpenClaw 모델 provider 문서 | 에이전트는 provider/model 선택, provider 인증, 로컬 모델, fallback 정책, canonical provider ID, provider plugin 경계를 명확히 해야 합니다. | `llm_service_catalog`에 OpenAI/Codex, Claude, Gemini, Mistral, OpenRouter, Ollama/Ollama Cloud, LM Studio(`lmstudio`), DeepSeek/Groq/GMI/Novita/Hugging Face/Kilo/xAI/Perplexity/Together/Fireworks/DeepInfra/Arcee/Chutes/Qianfan/StepFun/Volcengine/Xiaomi/vLLM/SGLang 같은 OpenAI-compatible provider, Synthetic/MiniMax 같은 Anthropic-compatible provider, 그리고 provider plugin/OAuth/custom runner가 필요한 manifest-only provider를 분리했습니다. `openclaw_cli_local`은 Gateway HTTP를 켜지 않고도 설치된 `openclaw agent --local --model provider/model` 런타임에 live chat/work 턴을 넘길 수 있게 합니다. `list-openclaw-provider-connectors`, `doctor-openclaw-provider-connectors`, `doctor-openclaw-provider-auth`가 live adapter, local server, API key env 준비, OAuth/account-session provider, cloud profile, CLI-owned execution, OpenClaw Gateway handoff 상태를 API 키 값이나 로컬 config 경로 값 없이 확인합니다. |
| OpenClaw 채널 문서 | 채팅 채널은 gateway가 플랫폼 메시지를 표준 envelope로 바꾸고, 플랫폼별 전송은 별도 플러그인이 맡는 구조가 필요합니다. 답변은 원래 들어온 채널/세션으로 돌아가야 하며, 모델이 목적지 채널을 고르지 않아야 합니다. | `openclaw-channel-*` 카탈로그, `build-openclaw-gateway-config`, `run-openclaw-channel-message`, `doctor-openclaw-channel-flow`, `run-openclaw-channel-gateway-server`, `run-openclaw-webchat-server`를 추가해 Telegram/Discord/Slack/WebChat, BlueBubbles, legacy iMessage 흐름을 로컬에서 먼저 검증할 수 있게 했습니다. 또한 `doctor-openclaw-channel-pairing`으로 QR session, local CLI bridge, enterprise bot, legacy migration 준비 상태를 비밀값/session/path 값 없이 분리하고, `build-openclaw-channel-delivery-config`, `send-openclaw-channel-outbound`로 dry-run 우선 delivery adapter를 추가했습니다. |
| Telegram/Discord/Slack API 문서 | 실제 외부 전송은 Telegram Bot API `sendMessage`, Discord webhook/bot channel message, Slack Web API `chat.postMessage`처럼 플랫폼별 토큰과 target이 필요합니다. | OpenClaw conversation/session key에서 chat/channel/thread/topic 힌트를 추출해 payload를 만들고, 토큰은 환경변수에서만 읽으며, `--mode live`를 명시할 때만 네트워크 전송을 수행하게 했습니다. |
| Telegram Update, Discord MESSAGE_CREATE, Slack Events API 문서 | inbound 플랫폼 payload는 구조가 서로 달라서 AI 인재에게 넣기 전에 표준화와 허용목록 검사가 필요합니다. | `build-openclaw-channel-access-config`로 deny-by-default allowlist를 만들고, `translate-openclaw-platform-event`로 raw event를 Paideia OpenClaw channel message schema로 변환합니다. gateway는 `/openclaw/platform-event/{channel}`에서 허용된 sender/conversation만 라우팅합니다. |
| OpenClaw 전체 채널 디렉터리 | OpenClaw는 mainstream, developer/self-hosted, regional, WebChat, voice call 채널을 제공하며, 최신 문서는 신규 iMessage 경로로 BlueBubbles를 권장합니다. | `list-openclaw-channel-connectors`, `doctor-openclaw-channel-connectors`, `doctor-openclaw-channel-pairing`이 OpenClaw manifest의 모든 채널을 커버합니다. doctor는 Paideia 직접 adapter, normalized gateway 전용 채널, BlueBubbles migration, WhatsApp/WeChat/Zalo Personal QR pairing, signal-cli, imsg, Matrix 계정, Twilio, 지역 플랫폼 토큰 같은 준비 요구사항을 분리해 기록합니다. |
| OpenClaw agent runtime 문서 | OpenAI/Codex는 런타임 표면일 수 있지만, 그 자체가 에이전트 정체성은 아닙니다. | `llm_identity_policy: application_engine_not_identity`를 기록하고, 정체성은 로컬 교육 산출물에서 오도록 했습니다. |
| Hermes Agent | 설치, 모델 전환, CLI 채팅, 도구, 스킬, 메모리, 게이트웨이, OpenClaw 마이그레이션을 강조합니다. | 설치 키트, doctor 검사, 스킬 마이그레이션 wrapper, adapter manifest, Reasoning Ledger를 추가했습니다. |
| OpenHands | 워크스페이스 에이전트는 계획, 결과, trace 같은 검증 가능한 파일을 남겨야 합니다. | 고용 에이전트의 workspace/dataflow 실행이 계획, 결과, trace, 학습 승격 기록을 남깁니다. |
| Agent ID Card | 에이전트 신원은 display name, owner, role, scope, credential, verification status와 연결되어야 합니다. | 계획 반영: hiring dossier와 설치 매니페스트에서 Agent ID Card payload를 export하되, 등록은 사용자가 명시적으로 실행할 때만 수행합니다. |

## 하드웨어와 데이터플로우 벤치마크

| 출처 | 확인한 점 | Paideia Agent 반영 |
| --- | --- | --- |
| Tesla AI & Robotics | AI 시스템은 높은 throughput, 낮은 latency, determinism, correctness, memory-efficient 데이터 처리가 중요합니다. | 선택된 LLM은 계산 엔진으로 두고, `memory_substrate`와 Codex bridge가 현재 질문에 필요한 hot context만 가까이 배치합니다. |
| Tesla Hot Chips 31 FSD Computer 발표 | FSD Chip 발표는 data aligner, local SRAM, weight buffer, data sharing, DRAM/SRAM 접근 감소, in-place reuse를 강조합니다. | 보스의 기판 비유를 **Memory Board Architecture**로 정리했습니다. inline context formatter, hot/evidence/safety lane, staged learning update, 검증된 Reasoning Ledger 경로 재사용으로 번역했습니다. |
| Computing's Energy Problem | 현대 계산에서는 연산 자체보다 데이터 이동과 에너지 비용이 병목이 될 수 있습니다. | 전체 기록을 프롬프트에 쏟아붓지 않고, 선택, 압축, staging, promotion을 거치는 소프트웨어 데이터플로우 기판으로 설계합니다. |

상세 문서: [Tesla식 데이터플로우 기판 벤치마킹](tesla_board_benchmark.ko.md).

## 학습과 기억 연구

| 출처 | 확인한 점 | Paideia Agent 반영 |
| --- | --- | --- |
| Reflexion | 언어 피드백과 작업 결과가 모델 가중치 변경 없이 다음 행동을 개선할 수 있습니다. | `learning_ledger.json`에 검토된 업무 결과와 피드백을 승격합니다. |
| Generative Agents | 관찰, 기억 검색, reflection, planning이 장기 일관성에 중요합니다. | `memory_substrate.json`, active memory route, 최근 대화 요약, 성장 체크포인트를 분리했습니다. |
| CoALA | LLM 에이전트는 working/episodic/semantic/procedural memory와 action으로 나눠 볼 수 있습니다. | 기억기판을 episode store, semantic principle, procedural operator, action surface로 나눴습니다. |
| ACT-R | 인간형 인지는 선언기억과 절차기억의 조합으로 모델링할 수 있습니다. | 습관과 문제 해결 절차를 검토 가능한 procedural operator로 기록합니다. |
| Soar | 막힘과 chunking은 문제 해결에서 새 절차 지식을 만들 수 있습니다. | 실패한 시험, 막힌 업무, 정정, 복구 답변을 학습 후보로 남깁니다. |
| Complementary Learning Systems | 빠른 episodic 학습과 느린 구조화 학습은 역할이 다릅니다. | 원경험은 로컬에 두고, 검토된 요약과 원칙만 active memory로 승격합니다. |
| Retrieval practice / test-enhanced learning | 시험은 측정만이 아니라 학습 압력입니다. | 초중고 시험, 수능형 평가, 대학 시험, 리포트, 박사 심사가 Reasoning Ledger를 갱신합니다. |
| 자기조절학습 | 학습은 계획, 수행, 모니터링, 성찰의 반복입니다. | 장기 목표와 job cycle이 성공 기준, trace, 검토 라벨, 다음 학습 규칙을 저장합니다. |
| 통찰 문제 해결 연구 | 어려운 문제는 문제 표상의 재구성이 중요할 수 있습니다. | 반례, 재정의, 자료 탐색 결정, 수정 원칙을 최종 답과 분리해 저장합니다. |

## 피지컬 AI와 시뮬레이션

| 출처 | 확인한 점 | Paideia Agent 반영 |
| --- | --- | --- |
| NVIDIA Isaac Gym / Isaac Lab | 대량 병렬 시뮬레이션은 embodied policy 학습을 빠르게 합니다. | 같은 나이/학년 체크포인트에서 여러 episode rollout을 병렬로 돌리는 구조를 계획했습니다. |
| MuJoCo MJX / Playground | 벡터화된 환경은 다양한 변형을 빠르게 시험할 수 있습니다. | 대화, 학교생활, 스트레스, 친구 갈등, 리서치 상황을 다양화하되 성장 시간축은 유지합니다. |
| OpenAI dexterous manipulation / domain randomization | 시뮬레이션 변형은 실제 배포 전 reality gap을 줄입니다. | 질문 표현, API 실패, 파일 누락, 상충 자료, 사회적 스트레스를 승격 전 평가합니다. |
| GR00T 계열 로봇 보고서 | 시연, 합성 데이터, 시뮬레이션, 실제 피드백이 함께 필요합니다. | 생성 에피소드, 시험, 실제 대화, 실제 업무를 다른 evidence class로 구분하고 promotion/quarantine을 적용합니다. |

## 이번 제품 결정

- 온보딩은 LLM 서비스 선택, 채팅 표면 선택, 롤모델 선택, 육성, 이력서 검토 순서로 명확히 바꿨습니다.
- 첫 테스트 샘플은 `examples/graham_junior_onboarding.answers.json`입니다.
- “추론기보”는 내부 파일명으로 유지하되, 공개 용어는 **Reasoning Ledger / Ariadne Thread**로 바꿨습니다.
- LLM은 연구원과 대화 엔진입니다. AI 인재의 정체성은 로컬 교육기록, 학습원장, 기억기판, dossier에서 옵니다.
- 이력서형 dossier를 제품의 핵심 산출물로 설명합니다.
- 외부 신원은 자동 업로드가 아니라 dossier/install manifest export 경로로 계획합니다.
- 외부 게이트웨이와 마이그레이션 스킬은 기본 비활성화이며, 보스 검토와 doctor 검사를 통과해야 합니다.
- 이전 신용 성장 시스템은 폐기하지 않고, 앞으로 Paideia 인재들이 공통으로 사용할 수 있는 legacy life-development foundation으로 계승합니다. 상세 내용은 [기존 22B-AI 시스템 계승 메모](legacy_system_integration.ko.md)에 정리했습니다.
- 보스의 Tesla 기판 비유는 Paideia가 Tesla 하드웨어를 구현한다는 주장이 아니라, Memory Board Architecture라는 소프트웨어 설계 원칙으로 반영했습니다.

## 주요 링크

- Tesla AI & Robotics: https://www.tesla.com/AI?redirect=no
- Tesla Hot Chips 31 FSD Computer presentation: https://old.hotchips.org/hc31/HC31_2.3_Tesla_Hotchips_ppt_Final_0817.pdf
- Mark Horowitz, Computing's Energy Problem: https://doi.org/10.1109/ISSCC.2014.6757323
- OpenClaw onboarding reference: https://docs.openclaw.ai/reference/wizard
- OpenClaw provider directory: https://docs.openclaw.ai/providers
- OpenClaw provider directory legacy path: https://docs.openclaw.ai/providers/index
- OpenClaw model providers: https://docs.openclaw.ai/concepts/model-providers
- OpenClaw channels: https://docs.openclaw.ai/channels
- OpenClaw channel routing: https://docs.openclaw.ai/channels/channel-routing
- Telegram Bot API sendMessage: https://core.telegram.org/bots/api#sendmessage
- Telegram Bot API Update: https://core.telegram.org/bots/api#update
- Discord Gateway MESSAGE_CREATE: https://docs.discord.com/developers/docs/topics/gateway-events#message-create
- Discord execute webhook: https://discord.com/developers/docs/resources/webhook#execute-webhook
- Slack Events API: https://docs.slack.dev/apis/events-api/
- Slack message event: https://docs.slack.dev/reference/events/message/
- Slack chat.postMessage: https://api.slack.com/methods/chat.postMessage
- OpenClaw agent runtimes: https://docs.openclaw.ai/concepts/agent-runtimes
- Agent ID Card: https://www.agentidcard.org/
- Hermes Agent repository: https://github.com/NousResearch/hermes-agent
- OpenHands overview: https://docs.openhands.dev/overview/introduction
- Reflexion: https://arxiv.org/abs/2303.11366
- Generative Agents: https://arxiv.org/abs/2304.03442
- CoALA: https://arxiv.org/abs/2309.02427
- ACT-R: https://act-r.psy.cmu.edu/
- Soar: https://soar.eecs.umich.edu/
- Complementary Learning Systems: https://pubmed.ncbi.nlm.nih.gov/7624455/
- Test-enhanced learning: https://pubmed.ncbi.nlm.nih.gov/16507066/
- Self-regulated learning review: https://pmc.ncbi.nlm.nih.gov/articles/PMC5408091/
- Insight problem-solving review: https://www.nature.com/articles/s44159-023-00257-x
- NVIDIA Isaac Gym paper: https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/file/28dd2c7955ce926456240b2ff0100bde-Paper-round2.pdf
- NVIDIA Isaac Lab: https://docs.isaacsim.omniverse.nvidia.com/6.0.0/isaac_lab_tutorials/index.html
- MuJoCo MJX: https://mujoco.readthedocs.io/en/latest/mjx.html
- OpenAI dexterous manipulation: https://journals.sagepub.com/doi/full/10.1177/0278364919887447
