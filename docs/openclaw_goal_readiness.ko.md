# OpenClaw 목표 준비 감사

`audit-openclaw-goal-readiness`는 보스가 요청한 현재 목표, 즉 Paideia Agent가 OpenClaw처럼 LLM 서비스와 채팅 채널을 선택하고 실제 연결 전까지 검증 가능한지를 한 번에 확인하는 명령입니다.

```powershell
ai22b-talent-foundry audit-openclaw-goal-readiness `
  --employment-record "<employment_record.json>" `
  --channel webchat `
  --output openclaw_goal_readiness.json `
  --summary-output OPENCLAW_GOAL_READINESS.md
```

이 감사가 확인하는 항목은 다음과 같습니다.

- OpenClaw provider/channel catalog parity
- 선택된 `provider/model` 또는 OpenClaw Gateway agent target 보존
- OpenClaw식 채팅 채널 선택
- WebChat의 메시지별 `offline`, `auto`, `live` 모드와 `provider/model` override
- 설치된 OpenClaw CLI/config/Gateway/model/channel의 읽기 전용 상태
- live smoke plan에 CLI, Gateway, LLM, channel probe가 포함되는지
- provider key, bot token, OAuth session, QR material, private training file을 저장하지 않는 정책

이 명령은 유료 provider 호출, OAuth pairing, QR login, 외부 채널 발송을 하지 않습니다. 실제 네트워크 사용은 보스가 생성된 live smoke 명령을 명시적으로 실행할 때만 일어납니다.

결과 상태가 `ready_for_live_operator_validation`이면 코드와 설정 산출물의 연결 경로는 준비된 상태이고, 남은 일은 보스 컴퓨터의 실제 provider 인증, OpenClaw Gateway 실행, 채널 pairing을 live smoke test로 확인하는 것입니다.
