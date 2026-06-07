# OpenClaw식 Paideia 온보딩

Paideia의 기존 `start-console`은 질문과 선택지를 한 번에 길게 보여주는 형태라 처음 쓰는 사람이 흐름을 잡기 어려웠습니다. 이제 온보딩은 OpenClaw의 wizard 구조를 Paideia에 맞춰 적용합니다.

## 흐름

```mermaid
flowchart TD
    A["Existing config"] --> B["QuickStart / Advanced"]
    B --> C["Model / Auth"]
    C --> D["Workspace"]
    D --> E["Gateway / Channels"]
    E --> F["Web / Search"]
    F --> G["Skills"]
    G --> H["Education Path"]
    H --> I["Runtime"]
    I --> J["Agent Identity"]
    J --> K["Health Check"]
    K --> L["Launch Plan"]
    L --> M["Finish"]
```

## Paideia에 추가된 단계

- `Education Path`: 공개 롤모델, 자기 확장, 커스텀 롤모델 중 선택합니다.
- `Owner Self-Extension Intake`: 자기 확장 자료는 본문을 읽지 않는 metadata-only manifest로 먼저 접수하며, 원본 파일명과 절대경로를 내보내지 않습니다.
- `Runtime`: 단일 에이전트, 본체 제어 분신 군체, 별도 전문팀, simulation rollout을 선택합니다.
- `Agent Identity`: Agent ID Card 등록용 payload와 Agent_warrent/Agent Identity Layer `ail.v1` envelope를 로컬 파일로만 생성합니다. 외부 등록은 자동으로 하지 않습니다.
- `Health Check`: 산출물, 로컬 전용 정책, 외부 채널 비활성화, LLM provider matrix, 선택 provider checklist, 다음 명령을 점검합니다.
- `Launch Plan`: 선택한 LLM, 채팅 표면, 교육 경로, Agent ID payload, 첫 채팅, live-readiness, 다음 업무 cycle, doctor 명령을 한 파일에 묶어 다음 행동을 보여줍니다.

## 실행

```powershell
ai22b-talent-foundry onboard
```

기존 명령도 유지됩니다.

```powershell
ai22b-talent-foundry start-console
```

비대화식 실행은 답변 JSON을 사용합니다.

```powershell
ai22b-talent-foundry onboard --answers examples\graham_junior_onboarding.answers.json
```

생성된 세션은 다시 doctor로 검증할 수 있습니다.

```powershell
ai22b-talent-foundry doctor-onboarding-session `
  --session console_session.json `
  --strict `
  --output onboarding_doctor.json
```

생성된 launch plan은 dashboard view로 바로 확인할 수 있습니다. 이 명령은 카드와 다음 액션 큐를 출력만 하며, launch plan 안의 shell 문자열을 실행하지 않습니다.

```powershell
ai22b-talent-foundry show-onboarding-dashboard `
  --launch-plan onboarding_launch_plan.json
```

## 산출물

- `console_session.json`: 전체 온보딩 세션과 health 요약
- `paideia_onboarding_config.json`: OpenClaw식 설정 요약
- `onboarding_launch_plan.json`: 온보딩 후 사용자가 따라갈 launch plan. `operator_dashboard`와 `next_action_queue`를 포함해 LLM 선택, 채팅 표면, 롤모델 교육 경로, Agent Identity, 첫 채팅, live-readiness suite, 다음 goal cycle, doctor 명령을 순서대로 담습니다.
- `llm_provider_matrix.json`: 선택 가능한 LLM/provider 전체의 no-network readiness matrix
- `onboarding/llm_onboarding_checklist.json`: 선택 provider의 doctor/live-check/runtime/chat 명령 체크리스트
- `onboarding/llm_connection_profile.json`: 선택 provider의 환경변수, 모델명, localhost endpoint, 검증 순서, live chat 템플릿
- `onboarding_doctor.json`: `doctor-onboarding-session`으로 생성하는 health 검증 보고서
- `agent_id_card_payload.json`: 외부 등록 전 검토할 Agent ID Card payload
- `agent_identity_envelope.json`: Agent_warrent `ail.v1` 로컬 미등록 envelope
- `agent_identity_verification.json`: Agent ID Card payload와 Agent_warrent envelope의 로컬 사전 검증 보고서
- `agent_warrent_registration_request.json`: Agent_warrent `POST /agents/register`용 로컬 등록 요청 초안. 서명과 외부 등록은 보스가 직접 수행합니다.
- `agent_identity_registration_receipt.json`: 보스가 외부에서 등록한 결과를 로컬 envelope에 연결한 receipt
- `simulation_rollouts.json`: 병렬 episode rollout 계획
- `simulation_rollout_evaluation.json`: episode 순위, winner, 승격 후보, 격리 후보, 보스 검토 gate
- `onboarding/onboarding_session.json`: 실제 육성, 설치, 고용, 첫 목표 사이클 기록

Agent ID Card payload만 별도로 만들 수도 있습니다.

```powershell
ai22b-talent-foundry export-agent-id-card-payload `
  --installed-manifest <installed_agent_manifest.json> `
  --employment-record <employment_record.json> `
  --output agent_id_card_payload.json
```

Agent_warrent 호환 envelope만 별도로 만들 수도 있습니다.

```powershell
ai22b-talent-foundry export-agent-identity-envelope `
  --installed-manifest <installed_agent_manifest.json> `
  --employment-record <employment_record.json> `
  --output agent_identity_envelope.json
```

Agent_warrent 서버의 `POST /agents/register` 입력 형태에 맞춘 등록 요청 초안도 만들 수 있습니다. 이 명령은 canonical payload와 서명 안내만 만들고, 실제 owner signature 생성이나 외부 등록은 보스가 직접 수행해야 합니다.

```powershell
ai22b-talent-foundry export-agent-warrent-registration-request `
  --installed-manifest <installed_agent_manifest.json> `
  --employment-record <employment_record.json> `
  --owner-key-id <owk_...> `
  --output agent_warrent_registration_request.json
```

Agent_warrent / Agent ID Card SDK로 이어지는 connector kit도 만들 수 있습니다. 이 kit는 서명 템플릿과 manifest만 만들며, Paideia가 자동으로 외부 등록을 실행하지 않습니다.

```powershell
ai22b-talent-foundry build-agent-warrent-connector-kit `
  --registration-request agent_warrent_registration_request.json `
  --output-dir agent_warrent_connector `
  --server-url https://api.agentidcard.org
```

외부 등록 전에는 두 산출물을 함께 검증합니다. 이 명령은 네트워크를 사용하지 않고, 필수 필드, credential-like 값, 원문 이메일, 로컬 절대경로, 수동 등록 정책을 검사합니다.

```powershell
ai22b-talent-foundry verify-agent-id-card `
  --payload agent_id_card_payload.json `
  --envelope agent_identity_envelope.json `
  --output agent_identity_verification.json
```

보스가 외부 사이트에서 수동 등록을 완료한 뒤에는 결과 파일을 로컬 envelope에 연결할 수 있습니다. 이 명령도 네트워크를 호출하지 않으며, credential token 원문은 기본적으로 저장하지 않습니다.

```powershell
ai22b-talent-foundry import-agent-id-card-registration `
  --envelope agent_identity_envelope.json `
  --registration-result agent_id_card_registration_result.json `
  --output agent_identity_registration_receipt.json `
  --updated-envelope agent_identity_envelope.registered.json
```

## 중요한 차이

OpenClaw는 에이전트 런타임과 게이트웨이 설정이 중심입니다. Paideia는 여기에 교육 프로그램을 추가합니다. LLM/provider 선택은 시작일 뿐이고, 핵심 정체성은 curriculum, assessment transcript, hiring dossier, Reasoning Ledger, memory substrate에 남습니다.
