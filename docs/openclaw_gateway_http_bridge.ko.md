# OpenClaw Gateway HTTP LLM Bridge

Paideia Agent는 `openclaw_gateway_http` LLM 서비스를 통해 설치된 OpenClaw Gateway의 OpenAI 호환 HTTP endpoint를 사용할 수 있습니다.

이 경로의 목적은 Paideia가 OpenClaw provider를 다시 구현하지 않고, OpenClaw가 이미 지원하는 provider 인증과 backend model routing을 그대로 따르는 것입니다. Paideia는 성장 기록, 이력서, 학습 로그, Reasoning Ledger를 정리해 context로 넣고, 실제 LLM 호출은 OpenClaw Gateway가 담당합니다.

## 전제

- OpenClaw Gateway가 실행 중이어야 합니다.
- OpenClaw 설정에 `gateway.http.endpoints.chatCompletions.enabled=true`가 있어야 합니다.
- Gateway auth가 `token` 또는 `password`라면 `OPENCLAW_GATEWAY_TOKEN` 또는 `OPENCLAW_GATEWAY_PASSWORD`를 로컬 shell에 설정합니다.
- loopback에서 auth mode가 `none`인 경우에는 token 없이도 smoke test를 할 수 있지만, public internet에 노출하면 안 됩니다.

## 고용 시 선택

```powershell
ai22b-talent-foundry hire-installed `
  --installed-manifest "<installed_agent_manifest.json>" `
  --role "Research agent" `
  --llm-service openclaw_gateway_http `
  --llm-model "openrouter/meta-llama/llama-3.1-8b" `
  --llm-model-path "http://127.0.0.1:18789/v1" `
  --chat-surface openclaw-channel-webchat
```

Paideia의 OpenAI-compatible request에서 `model` 필드는 `openclaw/default` agent target으로 고정됩니다. 실제 backend provider/model은 `x-openclaw-model` 헤더로 보냅니다. 이 구조는 OpenClaw의 agent-first HTTP contract를 따르면서 Paideia의 local memory substrate, hiring dossier, Reasoning Ledger를 대화 context에 붙이는 방식입니다.

## Gateway LLM Doctor

먼저 정적 doctor를 실행하면 employment record, Gateway base URL, OpenClaw config patch, backend model header, 인증 환경변수 이름을 확인합니다. 이 모드는 네트워크를 호출하지 않습니다.

```powershell
ai22b-talent-foundry doctor-openclaw-gateway-llm `
  --employment-record "<employment_record.json>" `
  --config-patch "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_config_patch.json" `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_gateway_llm_doctor.json"
```

OpenClaw Gateway를 실행한 뒤에는 실제 `/v1/models`와 `/v1/chat/completions` smoke test를 할 수 있습니다.

```powershell
ai22b-talent-foundry doctor-openclaw-gateway-llm `
  --employment-record "<employment_record.json>" `
  --probe-gateway `
  --probe-chat `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_gateway_llm_doctor.live.json"
```

doctor 보고서는 token/password 값을 저장하지 않습니다. `Authorization` 헤더는 `<redacted>`로 기록되고, 실제 확인 결과에는 endpoint, agent target, backend model header, probe 성공 여부만 남깁니다.

## Runtime Bundle과의 연결

`build-openclaw-runtime-bundle`이 생성하는 `openclaw_config_patch.json`에는 다음 설정이 포함됩니다.

```json
{
  "gateway": {
    "mode": "local",
    "http": {
      "endpoints": {
        "chatCompletions": {
          "enabled": true
        }
      }
    }
  }
}
```

그 다음 `prepare-openclaw-native-config --mode plan`으로 병합 계획을 검토하고, 보스가 승인하면 `--mode apply --confirm-apply`로 실제 OpenClaw 설정에 적용할 수 있습니다.

## 보안 경계

- Gateway token/password는 owner/operator credential로 취급합니다.
- Paideia 보고서는 token 값을 저장하지 않습니다.
- Gateway endpoint는 loopback, tailnet, private ingress 같은 안전한 네트워크 안에서만 사용합니다.
- 채널별 사용자 인증과 allowlist는 HTTP LLM bridge가 아니라 channel plugin, pairing, access config 경로에서 처리합니다.
