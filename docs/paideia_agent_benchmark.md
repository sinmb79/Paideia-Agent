# Paideia Agent Benchmark: Hermes/OpenClaw Lessons

작성일: 2026-05-31

## 목표

`Paideia Agent`는 Hermes/OpenClaw처럼 설치 가능한 로컬 에이전트 프로그램이어야 하지만, 단순히 에이전트 런타임을 복제하는 것이 아니라 AI 인재를 육성한 뒤 고용 가능한 실행체로 내보내는 구조를 유지해야 합니다.

## 벤치마킹해서 가져올 것

### Hermes 계열

- 설치 편의성: 의존성, 런타임, 도구를 사용자가 한 번에 준비할 수 있어야 합니다.
- 프로필 격리: 여러 인재/에이전트가 서로 다른 설정, 세션, 스킬, 기억을 가져야 합니다.
- 스킬 시스템: 절차 기억을 파일 단위로 관리하고, 필요한 도구 사용법을 확장할 수 있어야 합니다.
- 프로그램형 진입점: CLI뿐 아니라 다른 프로그램에서 호출 가능한 에이전트 인터페이스가 있어야 합니다.

### OpenClaw 계열

- 게이트웨이/채널 어댑터: WhatsApp/Telegram/웹/API 같은 외부 채널로 확장 가능한 매니페스트를 준비합니다.
- 로컬 스킬 폴더: 스킬을 독립 폴더로 두고, 범위와 권한을 분리합니다.
- 메모리 상태 점검: 메모리 인덱스, 파일 권한, gateway 상태를 doctor가 확인할 수 있어야 합니다.
- per-agent scoping: 스킬과 기억을 에이전트별/공유별로 분리할 수 있어야 합니다.

## 사용자 불만에서 반영할 것

최근 Hermes/OpenClaw류 사용자 피드백은 반복적으로 같은 문제를 말합니다.

- 장기 세션에서 토큰이 기억 재주입과 세션 replay에 과도하게 쓰입니다.
- MEMORY 파일이나 memory index가 커지면 오래된 규칙이 밀리거나 잘못된 기억이 다시 떠오릅니다.
- 여러 에이전트를 돌릴 때 프로필/메모리 드리프트가 생깁니다.
- 모델/API 오류가 나면 workflow가 멈추고 사용자가 수동 복구해야 합니다.
- 스킬이 너무 쉽게 설치되거나 많은 권한을 갖기 때문에 보안 위험이 큽니다.
- 게이트웨이를 외부에 노출하면 로컬 파일/토큰/계정 접근 위험이 커집니다.

## Paideia의 설계 반영

1. 설치 키트
   - `build-paideia-agent-kit`은 고용된 인재의 필수 기록을 별도 폴더로 복사합니다.
   - `README.md`, `start_paideia_chat.ps1`, `doctor_paideia.ps1`, `paideia_onboarding.template.json`을 포함합니다.

2. Doctor 우선
   - `doctor-agent-program`은 프로그램 스키마, 진입점, 기억 파일, 교육축, 보안 기본값, 어댑터 매니페스트를 검사합니다.
   - 첫 실행 전 doctor를 돌리는 것을 온보딩 기본값으로 둡니다.

3. 메모리 정책
   - 전체 세션 replay가 아니라 bounded selected summaries만 LLM 컨텍스트에 보냅니다.
   - 실패/API 오류/저품질 응답은 learning ledger에서 quarantine합니다.
   - 숨은 chain-of-thought는 저장하지 않고 검토 가능한 요약만 저장합니다.

4. 프로필 격리
   - 한 명의 고용 인재마다 하나의 Paideia Agent kit를 갖습니다.
   - sample talent, grham-쥬니어, 미래 전문 인재는 서로 다른 install kit와 기억 파일을 갖습니다.

5. 스킬/채널 보안
   - community procedures는 외부 참고자료로만 검역하고, external channels는 기본 비활성화입니다.
   - OpenClaw 스타일 gateway는 매니페스트만 준비하고, loopback/private network 정책을 확인하기 전까지 실행하지 않습니다.
   - Hermes/OpenClaw 어댑터는 `adapter_manifests/`에 export shape만 둡니다.

6. 외부 참고자료 검역
   - Hermes/OpenClaw/generic 절차 폴더는 `intake-external-references`로 활성 스킬이 아니라 참고자료 검역함에만 복사할 수 있습니다.
   - `SKILL.md`, `skill.yaml`, `README.md` 기반 폴더를 감지하고 Paideia kit의 `references/external/<runtime>/<reference>/`로 참고자료만 복사합니다.
   - 원본 코드는 실행하지 않고, 외부 `SKILL.md`는 `SOURCE_SKILL_REFERENCE.md`로 바꾸며, 활성 스킬 descriptor 대신 `REFERENCE.md`, `paideia_external_reference_manifest.json`, `paideia_reference_compatibility_profile.json`을 생성합니다.
   - 기본 intake 모드는 `quarantine_reference_rewrite_as_training_only`입니다.
   - 기본 상태는 `quarantined_reference_only`와 `direct_external_use.status=forbidden`입니다.
   - `curl|bash`, `Invoke-Expression`, recursive delete, credential access, network listener 같은 위험 패턴을 표시합니다.

## 현재 구현

- CLI
  - `build-agent-program`
  - `build-paideia-agent-kit`
  - `doctor-agent-program`
  - `intake-external-references`
  - `run-agent-program-chat`

- 설치 키트 산출물
  - `22b_paideia_agent_program.json`
  - `paideia_agent_install_manifest.json`
  - `paideia_onboarding.template.json`
  - `doctor_paideia.ps1`
  - `start_paideia_chat.ps1`
  - `adapter_manifests/codex_native.json`
  - `adapter_manifests/hermes_style.json`
  - `adapter_manifests/openclaw_style.json`
  - `references/external/<runtime>/<reference>/paideia_external_reference_manifest.json`

## 외부 참고자료 검역 명령

```powershell
ai22b-talent-foundry intake-external-references `
  --source C:\path\to\openclaw-or-hermes-skill `
  --paideia-kit C:\path\to\paideia_agent_kit `
  --source-runtime openclaw
```

검역 자료는 사용 가능 상태로 켜지지 않습니다. Paideia의 원칙은 "외부 스킬은 Paideia 스킬이 아니다"입니다. 보스가 내용을 검토하더라도 원본 절차를 활성화하지 않고, 유용한 아이디어만 Paideia-native 교육과제, guided practice, timed exam/task trial, 업무 증거를 거쳐 내재화합니다.

## Sources

- Hermes Agent GitHub: https://github.com/NousResearch/hermes-agent
- Hermes FAQ/Troubleshooting: https://hermes-agent.nousresearch.com/docs/reference/faq
- Hermes bundled skill/user guide: https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-hermes-agent
- Hermes memory/context field report: https://github.com/NousResearch/hermes-agent/issues/5563
- OpenClaw guide: https://openclaw.com.au/
- OpenClaw troubleshooting: https://openclaw.com.au/troubleshooting
- OpenClaw active memory docs: https://docs.openclaw.ai/concepts/active-memory
- OpenClaw per-user memory setup guide: https://hindsight.vectorize.io/guides/2026/04/15/guide-openclaw-per-user-memory-across-channels-setup

