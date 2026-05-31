# OpenClaw Native 설정 병합

Paideia Agent의 runtime bundle은 OpenClaw가 실제 provider 인증, channel plugin, gateway session, platform delivery를 맡을 수 있도록 `openclaw_native_handoff.json`과 `openclaw_config_patch.json`을 만듭니다.

`prepare-openclaw-native-config`는 이 두 파일을 기존 OpenClaw 설정과 안전하게 병합하는 명령입니다.

## 모드

- `plan`: 기본값입니다. OpenClaw 설정을 쓰지 않고 secret이 제거된 병합 보고서만 만듭니다.
- `write-copy`: `--merged-output`으로 지정한 로컬 파일에만 병합본을 씁니다. 기존 OpenClaw 설정의 API key나 bot token이 보존될 수 있으므로 공개 저장소에 넣으면 안 됩니다.
- `apply`: `--confirm-apply`가 있을 때만 대상 OpenClaw 설정에 씁니다. 쓰기 전에 백업 파일을 먼저 만듭니다.

## 사용 예

```powershell
ai22b-talent-foundry prepare-openclaw-native-config `
  --handoff "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_handoff.json" `
  --mode plan `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_config_merge.plan.json"

ai22b-talent-foundry prepare-openclaw-native-config `
  --handoff "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_handoff.json" `
  --mode write-copy `
  --merged-output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw.merged.local.json" `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_config_merge.copy.json"

ai22b-talent-foundry prepare-openclaw-native-config `
  --handoff "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_handoff.json" `
  --mode apply `
  --confirm-apply `
  --output "$env:AI22B_STORAGE_ROOT\talent-foundry\runs\openclaw_runtime_bundle\openclaw_native_config_merge.apply.json"
```

## 보안 경계

- 보고서에는 secret 값이 저장되지 않습니다.
- `write-copy`와 `apply`는 기존 로컬 OpenClaw 설정의 secret 값을 병합본 안에 보존할 수 있습니다.
- 공개 릴리스에는 `openclaw.merged.local.json`, 실제 `openclaw.json`, 백업 파일을 포함하지 않습니다.
- 적용 후에는 `openclaw doctor`를 실행해 OpenClaw 쪽 provider/channel 상태를 확인합니다.
