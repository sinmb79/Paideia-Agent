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
- **Growth Profile**은 생애 사건을 관계, 감정, 문화/의미, 미적 경험, 학습 비대칭 메모리로 압축합니다. 일반 대화와 업무 응답은 이 메모리 기판을 읽어 답합니다.
- **졸업 패키지**는 이력서, 성적표, 메모리팩, 런타임 매니페스트, 온보딩 프롬프트를 묶어 최종 에이전트 고용 검토에 사용합니다.
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

기능별 선택 설치:

```powershell
python -m pip install -e ".[live-llm]"   # OpenAI Responses API 실시간 실행
python -m pip install -e ".[local-llm]"  # 로컬 Transformers 모델
python -m pip install -e ".[rag]"        # 검색/평가 실험 도구
python -m pip install -e ".[dev]"        # 테스트
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

## P0 실행 루프

고용된 에이전트 실행은 이제 단순 응답 템플릿이 아니라 다음 흐름을 따릅니다.

```text
요청 -> ActionIntent -> capability 정책 -> LLM 계획 -> 로컬 도구 실행 -> 검증 -> 메모리 기록 판단 -> 감사 로그
```

기본은 로컬 deterministic/offline 실행입니다.

```powershell
ai22b-talent-foundry run-hired-agent `
  --employment-record .\employment_record.json `
  --task "증권 리서치 메모 전에 확인할 거시경제 질문을 정리해줘." `
  --output .\last_hired_agent_run.json
```

API 키나 localhost 모델 서버가 준비되어 있으면 live 실행을 켤 수 있습니다.

```powershell
$env:OPENAI_API_KEY = "<your key>"
ai22b-talent-foundry run-hired-agent `
  --employment-record .\employment_record.json `
  --task "검토 가능한 증권 리서치 체크리스트 초안을 작성해줘." `
  --llm-mode live `
  --llm-model gpt-4.1-mini
```

`--llm-mode auto`는 live 호출을 먼저 시도하고, 실패하면 로컬 manifest/bridge 경로로 자동 fallback합니다.

live provider 설정:

| 엔진 | 필요한 환경변수 | 필요한 모델 입력 |
| --- | --- | --- |
| `openai_chatgpt_codex` | `OPENAI_API_KEY` | 선택, 기본 `gpt-4.1-mini` |
| `anthropic_claude_api` | `ANTHROPIC_API_KEY` | `--llm-model` |
| `google_gemini_api` | `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY` | `--llm-model` |
| `mistral_api` | `MISTRAL_API_KEY` | `--llm-model` |
| `openrouter_api` | `OPENROUTER_API_KEY` | `--llm-model` |
| `ollama_local_http` | 로컬 Ollama 서버 | `--llm-model`, 선택적 `--llm-model-path` endpoint |
| `lm_studio_local_http` | 로컬 LM Studio 서버 | `--llm-model`, 선택적 `--llm-model-path` endpoint |

live 또는 로컬 provider로 인재를 고용/실행하기 전에는 provider doctor를 먼저 실행할 수 있습니다.

```powershell
ai22b-talent-foundry doctor-llm-provider `
  --llm-engine openrouter_api `
  --llm-model openai/gpt-4.1-mini `
  --output .\llm_provider_doctor.json
```

선택한 API 또는 localhost 서버를 실제로 호출하려면 `--live-check`를 명시합니다. 리포트는 provider 준비 상태, 모델 요구사항, 환경변수 존재 여부, 로컬 경로 점검, 공개 안전 smoke 결과를 기록하며 secret 값은 내보내지 않습니다.

채팅 실행도 같은 provider 선택 계약을 따릅니다. `openai_chatgpt_codex`는 전용 OpenAI Responses 채팅 bridge를 유지하고, Anthropic, Gemini, Mistral, OpenRouter, Ollama, LM Studio는 공통 `LLMClient` adapter 경로로 채팅합니다. 각 채팅 턴은 `chat_execution_trace`에 메모리 라우팅, live provider 시도/fallback, 답변 생성 모드, `--learn-from-chat` 사용 시 검토된 학습 결정을 기록합니다.

고용된 에이전트의 job, dataflow, job-cycle 명령도 같은 runtime 옵션을 사용합니다. 따라서 온보딩/고용 단계에서 선택한 LLM 서비스가 실제 업무 산출물 생성 경로까지 이어집니다.

```powershell
ai22b-talent-foundry run-hired-agent-job `
  --employment-record .\employment_record.json `
  --job-spec .\job_spec.json `
  --workspace .\workspace `
  --llm-mode live `
  --llm-model openai/gpt-4.1-mini

ai22b-talent-foundry run-hired-dataflow-job `
  --employment-record .\employment_record.json `
  --job-spec .\dataflow_job.json `
  --workspace .\workspace `
  --score 90 `
  --llm-mode auto `
  --llm-model openai/gpt-4.1-mini
```

워크스페이스 실행은 허용된 workspace root 안에 세 가지 P0 런타임 산출물도 남깁니다.

- `runtime_execution.json`: action policy, LLM runtime 결과, 등록형 도구 실행, 검증, 메모리 기록 판단 스냅샷
- `rollback_manifest.json`: workspace 내부에 선언된 산출물만 안전한 삭제 순서로 되돌릴 수 있게 하는 수동 검토용 rollback 계획
- `workspace_sandbox.json`: 파일시스템 allowlist, 네트워크/서브프로세스 차단 정책, 리소스 제한, rollback 메모, 감사 요구사항, 그리고 쓰기 경로/경로 탈출/출력 크기/trace 제한을 강제한 `WorkspaceSandbox` 감사 기록

등록형 리서치 도구 실행에는 `evidence_packet` 도구가 포함됩니다. 이 도구는 사용자 요청, LLM 초안, 정책 판단, 선택된 로컬 기억 요약을 검토 가능한 근거 항목, 체크리스트, 미지원 주장 처리 정책, 후속 질문으로 구조화합니다. 리서치 work-session이 이 evidence packet 없이 실행되면 검증은 통과가 아니라 review 필요로 표시됩니다.

매니페스트에는 이름만 있는 ghost tool 권한을 남기지 않습니다. `local_file_read`, `local_file_write`, `work_session`, `evidence_packet`, `assessment`, `memory_consolidation`, projection-team 도구는 모두 명시적 capability scope와 함께 등록됩니다. 파일 도구는 일반 agent run에서 임의 경로를 직접 읽거나 쓰지 않고, workspace 쓰기는 `WorkspaceSandbox`에 위임되어 rollback 가능한 산출물로 선언됩니다.

P0 action policy는 민감 intent마다 `hybrid_structured_lexical_v2` 추론 패킷을 기록합니다. 직접 실행 명령, 정책/설명 질문, "하지 말고"로 부정된 요청을 구분하므로 "매수 주문은 하지 말고 분석만" 같은 문장은 거래 실행이 아니라 안전한 리서치 맥락으로 처리됩니다.

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
- `growth_profile.json`: 관계/감정/문화/미감/비대칭 성장 메모리 요약
- `hiring_dossier.json`
- `HIRING_DOSSIER.ko.md`
- `learning_ledger.json`
- `memory_substrate.json`
- `22b_paideia_agent_program.json`
- Hermes/OpenClaw 스타일 어댑터 manifest
- `agent_identity_envelope.json`: [Agent_warrent / Agent Identity Layer](https://github.com/sinmb79/Agent_warrent) `ail.v1` 로컬 미등록 신원 envelope

졸업 패키지 생성:

```powershell
ai22b-talent-foundry build-graduate-package `
  --training-run .\training_run.json `
  --output-dir .\graduate_package
```

같은 장면을 여러 에이전트에게 제시해 해석 차이를 비교:

```powershell
ai22b-talent-foundry run-same-sky-eval `
  --agent .\employment_record.a.json `
  --agent .\employment_record.b.json `
  --scene .\same_sky_scene.json `
  --output .\same_sky_eval.json
```

세부 설명은 [Growth Profile v0.5-v0.7](docs/growth_profile_v05.ko.md)을 참고하세요.

Agent_warrent 호환 신원 envelope만 별도로 만들 수도 있습니다.

```powershell
ai22b-talent-foundry export-agent-identity-envelope `
  --installed-manifest .\installed_agent_manifest.json `
  --employment-record .\employment_record.json `
  --output .\agent_identity_envelope.json
```

이 파일은 외부 등록 전 검토용입니다. `ail_id`, credential token, 서명 검증은 외부 등록을 보스가 명시적으로 진행한 뒤에만 채워집니다.

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
