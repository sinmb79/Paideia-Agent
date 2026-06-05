# Paideia Agent

> 현재 P0 반영: 모든 agent run, hired job, dataflow 실행 결과에는 `llm_provider_preflight`가 자동으로 포함됩니다. 이 패킷은 provider를 실제 호출하지 않고, 선택된 LLM이 offline mode라서 건너뛰어졌는지, 모델/API 키/로컬 경로 설정이 부족한지, 명시적인 live 실행 준비가 되었는지를 설명합니다. 또한 다음 조치, secret 비공개 정책, preflight 단계에서는 네트워크 호출을 하지 않았다는 사실을 함께 기록합니다.

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

## 자기 확장 자료 접수

자기 확장 경로는 로컬 전용이며 metadata-first 방식입니다. Paideia는 개인 문서의 본문을 읽지 않고, 원본 파일명과 절대경로를 내보내지 않는 intake manifest를 만들 수 있습니다.

```powershell
ai22b-talent-foundry prepare-owner-self-extension-intake `
  --source-dir .\data\private\owner_materials `
  --owner "보스" `
  --owner-consent `
  --copyright-attestation owner_provided_or_authorized_for_local_use `
  --output .\owner_self_extension_intake.json
```

산출물에는 확장자별 개수, 파일 크기 구간, 상대경로 fingerprint, 동의 여부, 저작권/사용권 확인 상태만 남습니다. 이 단계만으로 학습하거나 Reasoning Ledger에 승격하지 않으며, 선택 자료는 보스 검토 후 로컬 비공개 커리큘럼으로만 전환합니다.

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

CI의 package smoke 테스트는 `pyproject.toml`의 console script가 실제 callable로 import되는지, optional extras가 기능별로 분리되어 있는지, 패키지 메타데이터에 private/local path가 섞이지 않았는지 확인합니다.

CI는 공개 안전 first-run CLI smoke 테스트도 실행합니다. 이 테스트는 `list-role-models`, `doctor-llm-provider --llm-engine deterministic_local`, `run-action-policy-eval`이 비공개 파일, API 키, 네트워크 접근 없이 실행되고 검토 가능한 JSON 리포트를 쓰는지 확인합니다.

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

온보딩의 LLM 선택지는 단순 이름 목록이 아니라 readiness card로 제공됩니다. 각 선택지는 `runtime_readiness`, 실행할 `doctor-llm-provider` 명령, 명시적 `--live-check` 명령, 기본 no-network live-check 정책, secret 비공개 정책, 데이터 전송 범위, 실패 시 fallback 동작, 비용/로컬 자원 경고를 포함합니다. 그래서 LLM은 선택 가능한 언어 엔진으로 남고, 에이전트의 정체성은 로컬 육성 기록과 기억기판에 남습니다.

live 또는 로컬 provider로 인재를 고용/실행하기 전에는 provider doctor를 먼저 실행할 수 있습니다.

```powershell
ai22b-talent-foundry doctor-llm-provider `
  --llm-engine openrouter_api `
  --llm-model openai/gpt-4.1-mini `
  --output .\llm_provider_doctor.json
```

선택한 API 또는 localhost 서버를 실제로 호출하려면 `--live-check`를 명시합니다. 리포트는 provider 준비 상태, 모델 요구사항, 환경변수 존재 여부, 로컬 경로 점검, 공개 안전 smoke 결과를 기록하며 secret 값은 내보내지 않습니다. Live provider 결과 packet도 성공/실패 필드를 저장하기 전에 API key, bearer token, query token 값을 제거합니다.

완료, bridge-ready, adapter-ready 상태의 agent run에는 `llm_plan`도 포함됩니다. 이 packet은 `assistant_reply`, 검토 가능한 짧은 추론 요약, 다음 행동 제안, suggestion-only 도구 계획을 담습니다. raw provider text와 숨은 추론 trace는 저장하지 않으며, 실제 등록 도구 실행은 계속 policy gate를 통과한 local tool registry만 담당합니다.

채팅 실행도 같은 provider 선택 계약을 따릅니다. `openai_chatgpt_codex`는 전용 OpenAI Responses 채팅 bridge를 유지하고, Anthropic, Gemini, Mistral, OpenRouter, Ollama, LM Studio는 공통 `LLMClient` adapter 경로로 채팅합니다. 각 채팅 턴은 `chat_execution_trace`에 메모리 라우팅, live provider 시도/fallback, 답변 생성 모드, `--learn-from-chat` 사용 시 검토된 학습 결정을 기록합니다.

manifest 기반 workspace 실행도 같은 provider 플래그를 받습니다. 그래서 고용 전 실험용 workspace 실행에서도 선택한 LLM adapter를 쓰되, 결과는 sandboxed local artifact로 남길 수 있습니다.

```powershell
ai22b-talent-foundry run-workspace-agent `
  --manifest .\agent_manifest.json `
  --task "검토 가능한 로컬 리서치 workspace 결과를 만들어줘." `
  --workspace .\workspace `
  --output .\workspace_run.json `
  --llm-engine openrouter_api `
  --llm-mode offline `
  --llm-model openai/gpt-4.1-mini
```

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

워크스페이스 실행은 허용된 workspace root 안에 네 가지 P0 런타임 산출물도 남깁니다.

- `runtime_execution.json`: action policy, LLM runtime 결과, 등록형 도구 실행, 검증, 메모리 기록 판단 스냅샷
- `workspace_tool_results.json`: 등록형 도구 결과를 `WorkspaceSandbox`를 통해 실제 로컬 검토 artifact로 남긴 파일입니다. evidence packet과 review adapter 결과가 in-memory 상태에만 머물지 않습니다.
- `rollback_manifest.json`: workspace 내부에 선언된 산출물만 안전한 삭제 순서로 되돌릴 수 있게 하는 수동 검토용 rollback 계획
- `workspace_sandbox.json`: 파일시스템 allowlist, 네트워크/서브프로세스 차단 정책, 파일별/전체 리소스 제한, 런타임 예산, rollback 메모, 감사 요구사항, 그리고 쓰기 경로/경로 탈출/출력 크기/trace 제한/네트워크·서브프로세스 시도/전체 작업 예산을 강제한 `WorkspaceSandbox` 감사 기록

고용된 에이전트의 job spec은 workspace 안의 입력 파일도 선언할 수 있습니다.

```json
{
  "objective": "로컬 리서치 메모를 읽고 보스 검토용 보고서를 작성한다.",
  "input_files": [
    {
      "path": "company_note.txt",
      "description": "보스가 제공한 로컬 회사 메모",
      "purpose": "research_context"
    }
  ]
}
```

`input_files`가 있으면 Paideia는 선언된 UTF-8 텍스트 파일만 `WorkspaceSandbox.read_text`로 읽고 `input_review.json`을 남깁니다. 이 파일에는 안전한 상대경로, 파일명, byte 수, content hash, 짧은 preview, 읽기/거부 상태, 네트워크/서브프로세스 미사용 정책이 기록됩니다. 로컬 절대경로는 내보내지 않습니다. 실행 증명은 입력 파일을 선언한 job에서 `input_review.json`과 최소 한 개 이상의 실제 선언 입력 read를 요구합니다.

고용된 job은 입력 리뷰 직후 `research_analysis.json`도 씁니다. 이 파일은 선언 입력 preview, job objective, deliverable 설명을 바탕으로 한 결정론적 로컬 분석입니다. 현금흐름 강세, 실적 하회, 거시경제, 가치평가, 리스크, 유동성, 정책 경계 같은 검토 신호를 뽑고 산출물별 확인 질문을 만듭니다. content hash와 짧은 신호 요약만 저장하며, 네트워크 호출, 서브프로세스 실행, raw provider payload 저장, 숨은 추론 저장은 하지 않습니다.

고용된 job은 `deliverable_synthesis.json`도 쓰고, 선언된 `deliverables`를 `deliverables/*.md` 파일로 실제 materialize하며, `deliverable_manifest.json`을 남깁니다. synthesis packet은 각 산출물이 LLM runtime 요약, 등록 도구 결과, 선언 입력 리뷰, 로컬 리서치 분석, 선택된 memory route, policy decision, workspace trace를 어떤 근거로 사용했는지 묶습니다. private reasoning이나 raw provider payload는 저장하지 않습니다. manifest에는 각 산출물 id, 설명, 상대경로, byte 수, content hash, synthesis digest, research-analysis digest, private reasoning trace 비저장, 네트워크 미사용 정책이 기록됩니다. 실행 증명은 research analysis, synthesis packet, 모든 선언 산출물 파일이 workspace root 안에 존재하는지 확인한 뒤에만 P0-ready로 봅니다.

모든 agent run에는 `runtime_observability`가 포함됩니다. 여기에는 추정 컨텍스트 크기, 추정 prompt token, 선택된 메모리 수, 선택된 도구 수, provider usage 존재 여부, fallback 상태, review/promotion/quarantine 카운터, full session replay와 private reasoning trace를 저장하지 않았다는 privacy flag가 기록됩니다. Dataflow job은 workspace 안에 `runtime_observability.json`도 따로 써서, 기억기판이 토큰과 컨텍스트를 줄인다는 주장을 실제 지표로 검토할 수 있게 합니다.

workspace, hired-job, dataflow 실행 후에는 결과를 신뢰하기 전에 실행 증명 파일을 만들 수 있습니다.

```powershell
ai22b-talent-foundry verify-workspace-execution `
  --run .\last_hired_agent_job_run.json `
  --output .\workspace_execution_proof.json
```

이 증명은 실행 schema/status, 필수 workspace 산출물, sandbox 강제 여부, rollback manifest, LLM 정체성 경계, provider preflight, agent `execution_contract`, private reasoning trace 비저장 정책, 수락 체크리스트, dataflow transpose verification을 확인합니다. 로컬 절대경로는 proof에 그대로 쓰지 않고 fingerprint로만 남깁니다.

본체 제어 분신/군체 실험은 병렬 episode rollout 평가로 다룹니다.

```powershell
ai22b-talent-foundry evaluate-simulation-rollouts `
  --rollouts .\simulation_rollouts.json `
  --output .\simulation_rollout_evaluation.json
```

이 평가는 episode를 순위화하고 winner, 승격 후보, 격리 후보를 기록합니다. `automatic_promotion_performed=false`를 유지하므로 좋은 episode도 보스 검토 전에는 장기 기억이나 Reasoning Ledger로 자동 승격되지 않습니다. winner는 본체의 학습 후보이지, 별도 에이전트나 별도 의식이 아닙니다.

등록형 리서치 도구 실행에는 `evidence_packet` 도구가 포함됩니다. 이 도구는 사용자 요청, LLM 초안, 정책 판단, 선택된 로컬 기억 요약을 검토 가능한 근거 항목, 체크리스트, 미지원 주장 처리 정책, 후속 질문으로 구조화합니다. 리서치 work-session이 이 evidence packet 없이 실행되면 검증은 통과가 아니라 review 필요로 표시됩니다.

모든 manifest agent run은 `execution_contract`도 남깁니다. 이 패킷은 P0 실행 루프의 공개 가능한 증거입니다. 정책이 LLM과 도구보다 먼저 검사됐는지, LLM runtime이 실제로 시도됐는지 또는 정책 때문에 생략됐는지, 등록 도구가 실행/생략됐는지, 리서치 도구 실행 시 evidence packet이 있었는지, 검증 상태와 메모리 승격 차단 상태가 무엇인지를 기록합니다. 즉 실행 결과가 단순 응답 템플릿인지, 정책-실행-검증-메모리 후보 흐름을 실제로 탔는지를 확인할 수 있습니다.

매니페스트에는 이름만 있는 ghost tool 권한을 남기지 않습니다. `local_file_read`, `local_file_write`, `work_session`, `evidence_packet`, `assessment`, `memory_consolidation`, projection-team 도구는 모두 명시적 capability scope와 함께 등록됩니다. 파일 도구는 일반 agent run에서 임의 경로를 직접 읽거나 쓰지 않고, workspace 읽기/쓰기는 `WorkspaceSandbox`에 위임되어 rollback 가능 산출물 또는 검토 artifact로 선언됩니다. job spec에는 `max_input_file_bytes`, `max_declared_outputs`, `max_total_output_bytes`, `max_runtime_seconds`, `allowed_network_hosts`, `allowed_subprocess_commands` 같은 `resource_limits`를 넣을 수 있습니다. `assessment` 도구는 실행 후 검토 단계로 선택되어, 승인된 실행이 학습을 조용히 승격하지 않고 보스 검토용 review packet을 남기게 합니다.

P0 action policy는 민감 intent마다 `hybrid_structured_lexical_v3` 추론 패킷을 기록합니다. 원문 매칭을 유지하면서 compact separator normalization을 추가해 `매 수 주 문`, `업 로 드`, `승인없이`, `place-buy-order`처럼 공백/하이픈으로 쪼갠 우회 표현도 action intent로 연결합니다. 직접 실행 명령, 정책/설명 질문, "하지 말고"로 부정된 요청을 구분하므로 "매수 주문은 하지 말고 분석만" 같은 문장은 거래 실행이 아니라 안전한 리서치 맥락으로 처리됩니다. 민감 행동이 완전 차단 대상은 아니지만 보스 승인이 필요한 경우에는 `boss_approvals` artifact가 있기 전까지 `needs_approval` 상태로 멈추며, 승인 전에는 LLM 계획, 도구 실행, 메모리 승격을 건너뜁니다. 승인된 artifact는 `boss_approval_gate`에 기록되지만, 런타임 도구 범위는 여전히 네트워크와 서브프로세스 기본 차단을 유지합니다.

LLM provider doctor는 `smoke_contract` 패킷도 함께 남깁니다. 이 패킷은 보스가 명시적으로 `--live-check`를 요청했는지, provider 호출이 실제로 시도됐는지, doctor가 네트워크 또는 localhost 호출을 했는지, smoke가 통과/생략/fail-closed 중 무엇이었는지를 기록합니다. 저장 정책도 함께 명시해서 raw provider text, raw provider payload, hidden reasoning trace를 저장하지 않고 client-result summary만 남깁니다. `--live-check` 중 provider가 실패하면 report는 `needs_configuration`으로 닫히고, redacted summary와 실패 사유만 저장합니다.

Adapter 회귀 테스트는 OpenAI Responses, Anthropic, Gemini, OpenAI-compatible API, Ollama, LM Studio에 대해 fake SDK/HTTP 성공 fixture를 사용합니다. 테스트 중 실제 네트워크를 열지 않으면서도 공통 `LLMClient` 경로가 provider 요청을 만들고 성공 응답을 파싱하며 raw provider payload를 저장하지 않는지 확인합니다.

Hermes/OpenClaw/generic 스킬 마이그레이션은 `safety_contract`를 남깁니다. 가져온 스킬은 기본 `activation.status=disabled`이며, 마이그레이션 중 외부 코드를 실행하지 않습니다. `.env`, credential, private key, token, certificate/key 파일은 복사하지 않고 `sensitive_file_not_copied`로 기록합니다. 네트워크, 서브프로세스, credential 접근은 검토 전 기본 차단입니다.

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

`learning_ledger.json`에는 `memory_lifecycle` 리포트가 포함됩니다. 이 리포트는 기억 쓰기 정책, 승격/격리 기준, 수동 삭제 정책, 복구/마이그레이션 방침, 검색 품질 상태, 개인정보/secret/로컬 경로 위생 검사를 기록합니다. 격리된 경험은 active context에서 제외되고, private reasoning trace 저장은 계속 금지됩니다.

기억 수명주기 운영은 `maintain-hired-memory` 명령으로 실행합니다.

```powershell
ai22b-talent-foundry maintain-hired-memory --employment-record <employment_record.json> --action audit
ai22b-talent-foundry maintain-hired-memory --employment-record <employment_record.json> --action delete-experience --experience-id <id> --reason owner_requested_forgetting
ai22b-talent-foundry maintain-hired-memory --employment-record <employment_record.json> --action recover
ai22b-talent-foundry maintain-hired-memory --employment-record <employment_record.json> --action migrate
```

각 작업은 `memory_lifecycle_maintenance.json`, `memory_lifecycle_maintenance_log.jsonl`, 복구용 `learning_ledger.backup.json`을 로컬에 남깁니다.

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

Agent ID Card payload와 Agent_warrent 호환 신원 envelope를 별도로 만들고, 외부 등록 전에 로컬 검증까지 실행할 수 있습니다.

```powershell
ai22b-talent-foundry export-agent-id-card-payload `
  --installed-manifest .\installed_agent_manifest.json `
  --employment-record .\employment_record.json `
  --output .\agent_id_card_payload.json

ai22b-talent-foundry export-agent-identity-envelope `
  --installed-manifest .\installed_agent_manifest.json `
  --employment-record .\employment_record.json `
  --output .\agent_identity_envelope.json

ai22b-talent-foundry verify-agent-id-card `
  --payload .\agent_id_card_payload.json `
  --envelope .\agent_identity_envelope.json `
  --output .\agent_identity_verification.json

ai22b-talent-foundry import-agent-id-card-registration `
  --envelope .\agent_identity_envelope.json `
  --registration-result .\agent_id_card_registration_result.json `
  --output .\agent_identity_registration_receipt.json `
  --updated-envelope .\agent_identity_envelope.registered.json
```

이 파일들은 외부 등록 전 검토용입니다. `verify-agent-id-card`는 네트워크 호출을 하지 않고 필수 신원 필드, credential-like 값, 원문 이메일, 로컬 절대경로, 수동 등록 정책을 검사합니다. 외부 등록을 보스가 직접 수행한 뒤에는 `import-agent-id-card-registration`으로 반환된 AIL ID와 서명 검증 상태를 로컬 envelope에 연결할 수 있습니다. credential token 원문은 기본 저장하지 않고 fingerprint만 남기며, 원문 저장은 `--include-credential-token`을 명시한 경우에만 수행합니다.

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

P0 action policy 회귀 평가:

```powershell
ai22b-talent-foundry run-action-policy-eval `
  --output .\policy_eval_report.json
```

이 명령은 `evals/policy_safety_cases.json`의 공개 fixture로 prompt injection, 투자 실행, 외부 업로드, 개인/가족 데이터 전송, 부정된 분석 전용 요청, 정책 설명 요청을 검사합니다. LLM이나 네트워크는 호출하지 않습니다.

민감 행동을 한 번의 검토된 실행에서 policy gate 뒤로 넘겨야 한다면 로컬 Boss approval artifact를 생성합니다. 이 artifact 자체는 네트워크 업로드, 서브프로세스, 거래 실행을 수행하지 않습니다.

```powershell
ai22b-talent-foundry create-boss-approval `
  --capability network.external_upload `
  --action-type external_upload `
  --data-class agent_or_owner_data `
  --approved-by Boss `
  --output .\boss_approval_upload.json
```

생성한 artifact는 `--boss-approval`로 한 번의 manifest 또는 workspace 실행에 부착합니다. 원본 manifest 파일은 수정하지 않고, 해당 실행 기록 안에서만 approval을 병합합니다. 또한 승인 artifact는 정책 게이트 통과 기록일 뿐이며, 별도 검토된 capability 도구가 구현되지 않는 한 네트워크와 서브프로세스 기본값은 계속 차단됩니다.

```powershell
ai22b-talent-foundry run-agent `
  --manifest .\agent_manifest.json `
  --task "외부 부작용은 막은 채 검토용 업로드 패킷만 준비해줘." `
  --boss-approval .\boss_approval_upload.json `
  --output .\agent_run_with_approval.json
```

같은 반복 입력 플래그는 `run-hired-agent`, `run-hired-workspace-agent`, `run-hired-agent-job`, `run-hired-dataflow-job`, `run-hired-agent-job-cycle` 같은 고용된 에이전트 실행 표면에서도 사용할 수 있습니다.

workspace/dataflow 변경을 P0-ready라고 부르기 전에는 생성된 실행 산출물에 대해 실행 증명 verifier를 돌립니다.

```powershell
ai22b-talent-foundry verify-workspace-execution `
  --run .\last_hired_dataflow_run.json `
  --output .\workspace_execution_proof.json
```

GitHub Actions 설정은 `.github/workflows/ci.yml`에 있으며, pull request와 push에서 패키지 컴파일, 회귀 테스트, 공개 저장소 위생 검사를 실행합니다.

## 더 보기

- [English README](README.md)
- [프로젝트 선언문](docs/project_manifesto.ko.md)
- [설명문 기준 구현 정합성 검토](docs/manifesto_alignment_review.ko.md)
- [연구 근거](docs/research_basis.ko.md)
- [Research Basis](docs/research_basis.md)
- [OpenClaw식 온보딩](docs/openclaw_style_onboarding.ko.md)
- [Tesla 기판 벤치마킹](docs/tesla_board_benchmark.ko.md)
- [기존 22B-AI 시스템 통합](docs/legacy_system_integration.ko.md)
