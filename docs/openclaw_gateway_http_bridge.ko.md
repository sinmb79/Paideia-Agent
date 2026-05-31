# OpenClaw Gateway HTTP LLM Bridge

Paideia Agent는 `openclaw_gateway_http` LLM 서비스를 통해 설치된 OpenClaw Gateway의 OpenAI 호환 HTTP endpoint를 사용할 수 있습니다.

이 경로의 목적은 Paideia가 OpenClaw provider를 다시 구현하지 않고, OpenClaw가 이미 지원하는 provider 인증과 backend model routing을 그대로 쓰는 것입니다.

## 전제

- OpenClaw Gateway가 실행 중이어야 합니다.
- OpenClaw 설정에 `gateway.http.endpoints.chatCompletions.enabled=true`가 있어야 합니다.
- Gateway auth가 `token` 또는 `password`라면 `OPENCLAW_GATEWAY_TOKEN` 또는 `OPENCLAW_GATEWAY_PASSWORD`를 로컬 shell에 설정합니다.
- loopback에서 auth mode가 `none`인 경우에는 token 없이도 테스트할 수 있지만, public internet에 노출하면 안 됩니다.

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

Paideia는 OpenAI-compatible request의 `model`에는 `openclaw/default`를 넣고, 실제 backend provider/model은 `x-openclaw-model` 헤더로 보냅니다. 따라서 OpenClaw의 agent-first model contract를 유지하면서 Paideia의 local memory substrate, hiring dossier, Reasoning Ledger를 대화 context로 전달합니다.

## Runtime bundle과의 연결

`build-openclaw-runtime-bundle`은 생성하는 `openclaw_config_patch.json`에 다음 설정을 포함합니다.

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
- Paideia 보고서에는 token 값을 저장하지 않습니다.
- Gateway endpoint는 loopback, tailnet, private ingress 같은 안전한 네트워크 안에서만 사용합니다.
- 외부 메시징 network 사용자는 HTTP LLM bridge가 아니라 channel plugin, pairing, allowlist 경로로 연결합니다.
