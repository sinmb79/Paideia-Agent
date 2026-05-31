# OpenClaw식 실행 준비 bundle

Paideia Agent는 OpenClaw처럼 LLM provider와 chat channel을 선택할 수 있지만, Paideia의 중심은 고용된 인재의 로컬 성장 기록입니다. 그래서 실행 준비 단계는 기존 OpenClaw 설정을 바로 덮어쓰지 않고, 보스가 검토해서 병합할 수 있는 bundle로 내보냅니다.

## 목적

- 고용 기록의 `llm_service`, `llm_runtime`, `chat_surface`를 읽어 선택된 provider/model과 channel을 확인합니다.
- OpenClaw식 `openclaw.json`에 붙일 수 있는 설정 patch를 생성합니다.
- API key, bot token, QR pairing 같은 민감한 값은 저장하지 않고 환경변수 이름만 템플릿에 남깁니다.
- provider doctor, channel doctor, LLM health check를 함께 생성해 무엇이 바로 실행 가능하고 무엇이 플러그인/bridge 준비가 필요한지 확인합니다.

## 명령

```powershell
ai22b-talent-foundry build-openclaw-runtime-bundle `
  --employment-record "<employment_record.json>" `
  --channel webchat `
  --channel telegram `
  --output-dir "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle"
```

`--channel`을 생략하면 고용 기록의 chat surface에서 OpenClaw channel을 추론하고, 추론할 수 없으면 로컬 `webchat`을 기본값으로 사용합니다.

## 산출물

- `openclaw_runtime_bundle.json`: 전체 실행 준비 manifest입니다.
- `openclaw_config_patch.json`: OpenClaw식 agent/model/channel 설정 patch입니다.
- `openclaw.env.example.ps1`: 로컬 환경변수 템플릿입니다. 실제 secret 값은 들어가지 않습니다.
- `openclaw_provider_doctor.json`: 선택 provider의 live adapter, secret, plugin 필요 상태입니다.
- `openclaw_channel_doctor.json`: 선택 channel의 gateway, delivery, bridge/plugin 필요 상태입니다.
- `llm_service_health.json`: Paideia LLM runtime 상태입니다.
- `openclaw_gateway_config.json`: 로컬 loopback gateway 설정입니다.
- `openclaw_channel_access_config.json`: deny-by-default 접근 제어 설정입니다.

## 남은 개발 방향

1. 실제 OpenClaw provider plugin/OAuth 흐름과의 연결을 더 직접화합니다.
2. WhatsApp, Signal, Matrix, iMessage, Teams 같은 외부 channel bridge 설치 UX를 강화합니다.
3. channel별 live send를 WebChat 수준으로 쉽게 테스트할 수 있게 합니다.
4. 기존 OpenClaw 설정 감지, 유지, 검토 후 병합, reset 범위를 더 세밀하게 구현합니다.
5. Paideia의 교육/시험/업무경험 기반 Reasoning Ledger를 OpenClaw식 active memory와 더 자연스럽게 연결합니다.
