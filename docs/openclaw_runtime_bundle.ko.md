# OpenClaw식 실행 준비 bundle

Paideia Agent는 OpenClaw처럼 LLM provider와 chat channel을 선택할 수 있지만, 중심은 고용된 인재의 로컬 성장 기록입니다. 그래서 실행 준비 단계는 기존 OpenClaw 설정을 바로 덮어쓰지 않고, 보스가 검토해서 병합할 수 있는 bundle과 bridge setup kit로 내보냅니다.

## 목적

- 고용 기록의 `llm_service`, `llm_runtime`, `chat_surface`를 읽어 선택된 `provider/model`과 channel을 확인합니다.
- OpenClaw의 `openclaw.json`에 붙일 수 있는 설정 patch를 생성합니다.
- `channels.modelByChannel`로 채널이나 대화방별 모델을 지정할 수 있게 합니다.
- `bindings[]`로 특정 채널, 대화방, peer를 특정 Paideia 인재에게 연결할 수 있게 합니다.
- API key, bot token, QR pairing 세션 같은 민감한 값은 저장하지 않고 환경변수 이름만 템플릿에 담습니다.
- provider doctor, channel doctor, LLM health check를 함께 생성해 무엇이 바로 실행 가능하고 무엇이 플러그인/bridge 준비가 필요한지 확인합니다.
- import/runtime bundle 이후에는 bridge setup kit를 만들어 provider plugin/OAuth, channel bridge, deny-by-default 접근제어, smoke test payload를 한 번에 점검합니다.

## 기존 OpenClaw 설정 가져오기

이미 OpenClaw를 사용하고 있다면 먼저 기존 `openclaw.json`을 import할 수 있습니다. Paideia는 `provider/model`, `channels.*`, `channels.modelByChannel`, `bindings[]`를 읽어서 Paideia 선택값과 setup plan으로 바꾸고, API key나 bot token은 저장하지 않습니다.

```powershell
ai22b-talent-foundry import-openclaw-config `
  --config "$env:USERPROFILE\.openclaw\openclaw.json" `
  --output-dir "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_import"
```

생성 파일은 `paideia_openclaw_config_import.json`, `openclaw_config.redacted.json`, `openclaw_import_setup_plan.json`, `paideia_onboarding.answers.suggested.json`입니다.

기존 OpenClaw 설정을 온보딩 기본값으로 바로 사용할 수도 있습니다. `--answers` 파일에 적힌 값이 import 기본값보다 우선하므로, 사용자는 원하는 인재/롤모델 요청은 유지하면서 OpenClaw의 LLM과 첫 chat channel 선택만 가져올 수 있습니다.

```powershell
ai22b-talent-foundry start-console `
  --answers examples\graham_junior_onboarding.answers.json `
  --openclaw-config "$env:USERPROFILE\.openclaw\openclaw.json" `
  --output-dir "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_prefilled_onboarding"
```

## 실행 bundle 만들기

고용된 Paideia 인재를 OpenClaw식 실행 bundle로 연결할 때는 다음 명령을 사용합니다.

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

`--channel`을 생략하면 고용 기록의 chat surface에서 OpenClaw channel을 추론하고, 추론할 수 없으면 로컬 `webchat`을 기본값으로 사용합니다.

`--channel-model`은 `CHANNEL[:TARGET]=PROVIDER/MODEL` 형식입니다. `TARGET`을 생략하면 해당 channel의 기본 모델로 기록합니다. 예를 들어 `telegram:family=openrouter/meta-llama/llama-3.1-8b`는 Telegram의 `family` 대화방에 OpenRouter 모델을 우선 적용하라는 의미입니다.

`--binding`은 `CHANNEL[:CONVERSATION]=AGENT_ID` 형식입니다. OpenClaw의 `bindings[]`에 들어가며, 특정 채널이나 대화방으로 들어온 메시지를 어떤 Paideia 인재가 맡을지 결정합니다.

`--import-manifest`를 사용하면 `import-openclaw-config`가 만든 `paideia_openclaw_config_import.json`의 `channels.modelByChannel`과 `bindings[]`를 그대로 런타임 번들에 이어붙일 수 있습니다.

`--config-action`은 OpenClaw wizard의 기존 설정 처리 방식에 맞춰 `keep`, `modify`, `reset` 중 하나를 사용합니다. Paideia는 어떤 경우에도 기존 `openclaw.json`을 직접 삭제하거나 덮어쓰지 않습니다.

## Bridge setup kit 만들기

runtime bundle이나 import manifest를 만든 뒤에는 다음 명령으로 실제 연결 준비물을 생성합니다.

```powershell
ai22b-talent-foundry build-openclaw-bridge-setup-kit `
  --import-manifest "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_import\paideia_openclaw_config_import.json" `
  --provider qwen-oauth `
  --channel webchat `
  --channel telegram `
  --output-dir "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_bridge_setup"
```

이 명령은 선택된 provider와 channel을 기준으로 다음 파일을 만듭니다.

- `openclaw_bridge_setup_kit.json`: 전체 bridge 준비 manifest입니다.
- `openclaw_bridge.env.example.ps1`: provider/channel 환경변수 템플릿입니다. 실제 secret 값은 들어가지 않습니다.
- `openclaw_provider_plugin_plan.json`: Paideia direct adapter로 바로 가능한 provider와 OpenClaw plugin/OAuth가 필요한 provider를 구분합니다.
- `openclaw_channel_plugin_plan.json`: channel별 direct ingress, delivery, 외부 bridge/plugin, pairing/allowlist 필요 상태를 정리합니다.
- `openclaw_bridge_channel_access_config.json`: 기본 차단 정책의 channel 접근제어 설정입니다.
- `openclaw_bridge_smoke_tests.json`: gateway 시작, normalized payload 전송, Telegram/Discord/Slack raw event 변환을 위한 smoke test 명령과 payload 경로입니다.
- `smoke_test_payloads/*.json`: 실제 gateway에 넣어볼 수 있는 샘플 payload입니다.

## OpenClaw parity 감사

OpenClaw가 지원하는 provider와 channel 목록이 바뀌면 Paideia catalog도 같이 따라가야 합니다. 다음 명령은 확인된 OpenClaw 공식 문서 snapshot과 Paideia의 로컬 catalog를 비교해 누락된 provider/channel이 있는지 검사합니다.

```powershell
ai22b-talent-foundry audit-openclaw-parity `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_parity_audit.json" `
  --fail-on-missing
```

현재 snapshot은 OpenClaw `providers`, `channels`, `llms.txt`, `gateway/config-channels` 문서를 기준으로 합니다. 이 감사는 catalog/selector parity를 증명하지만, 모든 외부 OAuth나 channel plugin이 이미 보스 컴퓨터에서 인증되었다는 뜻은 아닙니다. 실제 live 연결은 bridge setup kit와 doctor 명령으로 따로 확인합니다.

## iMessage/BlueBubbles 주의

현재 OpenClaw 문서는 iMessage 지원을 `imessage`/`imsg` 경로로 안내합니다. `channels.bluebubbles`는 기존 설정을 `channels.imessage`로 옮기는 마이그레이션 대상으로만 남겨두었습니다. Paideia도 이 기준에 맞춰 `bluebubbles`는 legacy migration, `imessage`는 현재 OpenClaw식 imsg bridge로 표시합니다.

## 산출물

- `openclaw_runtime_bundle.json`: 전체 실행 준비 manifest입니다.
- `openclaw_config_patch.json`: OpenClaw식 agent, model, channel, `channels.modelByChannel`, `bindings[]` 설정 patch입니다.
- `openclaw.env.example.ps1`: 로컬 환경변수 템플릿입니다. 실제 secret 값은 들어가지 않습니다.
- `openclaw_provider_doctor.json`: 선택 provider의 live adapter, secret, plugin 필요 상태입니다.
- `openclaw_channel_doctor.json`: 선택 channel의 gateway, delivery, bridge/plugin 필요 상태입니다.
- `llm_service_health.json`: Paideia LLM runtime 상태입니다.
- `openclaw_gateway_config.json`: 로컬 loopback gateway 설정입니다.
- `openclaw_channel_access_config.json`: deny-by-default 접근 제어 설정입니다.
- `openclaw_existing_config_review.json`: 기존 OpenClaw 설정 감지 결과입니다.
- `openclaw_existing_config.redacted.json`: 기존 설정의 secret 값을 제거한 검토용 snapshot입니다.
- `openclaw_config_merge.preview.json`: `modify` 선택 시 생성되는 redacted 병합 preview입니다.
- `openclaw_config_reset_plan.json`: `reset` 선택 시 생성되는 계획 파일입니다. 실제 reset은 수행하지 않습니다.

## 다음 개발 방향

1. 실제 OpenClaw provider plugin/OAuth 흐름과의 연결을 더 직접화합니다.
2. WhatsApp, Signal, Matrix, iMessage, Teams 같은 외부 channel bridge 설치 UX를 강화합니다.
3. channel별 live send를 WebChat 수준으로 쉽게 테스트할 수 있게 합니다.
4. 기존 OpenClaw 설정 감지, 유지, 검토 후 병합, reset 범위를 더 세밀하게 구현합니다.
5. Paideia의 교육/시험/업무경험 기반 Reasoning Ledger를 OpenClaw의 active memory와 더 자연스럽게 연결합니다.
