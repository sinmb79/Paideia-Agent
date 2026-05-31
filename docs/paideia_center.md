# Paideia Agent

`Paideia Agent`는 단일 에이전트 이름만이 아니라, 보스의 컴퓨터에서 AI 인재를 길러내는 로컬 AI 교육센터/육성 프로그램입니다.

## 이름의 의미

`Paideia`는 단순한 지식 전달보다 넓은 교육과 형성을 뜻합니다. 이 프로젝트는 특정 답변 스타일을 주입하는 챗봇이 아니라, 성장 단계, 교과 과정, 시험, 실패, 사회성, 도구 사용, 안전 경계, 업무 경험을 누적해 AI 인재를 길러내는 것을 목표로 합니다.

따라서 추론기록, 즉 **Reasoning Ledger(Ariadne Thread)** 는 Paideia의 핵심 산출물 중 하나이지, 전체 프로그램 그 자체는 아닙니다.

## 구성

- `Paideia Agent`: AI 교육센터/육성 프로그램.
- `AI talent`: Paideia에서 길러지는 개별 AI 인재. 예: sample talent, grham-쥬니어.
- `Reasoning Ledger / Ariadne Thread`: 기억과 경험의 미로에서 길을 찾는 검토 가능한 추론 기록. 내부 호환 파일명은 `reasoning_kibo.jsonl`입니다.
- `Memory substrate`: 학습 데이터, 경험, 절차, 대화 발달을 담는 기억 기판.
- `Codex bridge`: 로컬 파일, 도구 실행, 검증, 성장 기록 승격을 담당하는 실행 관문.
- `Connected LLM`: 언어 생성과 고차원 추론을 수행하는 엔진. 정체성 자체가 아니다.

## 프로그래밍 가능한 교육축

Paideia는 추론만 육성하지 않습니다. 다음 축을 각각 프로그램화하고 평가/승격할 수 있어야 합니다.

1. 언어와 대화법: 인사, 잡담, 질문 의도 파악, 정정 수용, 말투.
2. Reasoning Ledger: 문제 정의, 근거, 반례, 보류 조건, 실패 회복.
3. 직업군 전문성: 교과, 실습, 시험, 보고서, 자격/학위형 기록.
4. 사회성: 갈등, 사과, 화해, 협업, 부모/보스 피드백 수용.
5. 도구 사용: Codex, 로컬 파일, 브라우징, 워크스페이스 작업, 데이터플로우.
6. 안전/정체성: 개인정보, 권한 경계, 정체성 혼입 방지, 실행 금지 행동.
7. 시뮬레이션 roll-out: 같은 성장 체크포인트에서 여러 분신 에피소드를 병렬 실행하고, 검증된 경험만 통합.

## 성장형 학습 원칙

새 학습은 항상 이전 체크포인트의 학습 데이터를 입력으로 받아야 합니다. 병렬 시뮬레이션은 시간을 건너뛰는 방법이 아니라, 같은 발달 단계 안에서 경험의 폭을 늘리는 방법입니다.

```text
previous checkpoint
-> stage curriculum
-> parallel episode roll-outs
-> exam/social/safety evaluation
-> promote or quarantine
-> updated checkpoint
-> next stage
```

## 에이전트화

최종 에이전트는 `Paideia Agent`가 길러낸 개별 AI 인재를 고용 가능한 실행체로 내보낸 것입니다. 따라서 에이전트 프로그램은 다음 구조를 따릅니다.

```text
local education records
+ learning ledger
+ Reasoning Ledger
+ memory substrate
+ recent chat/work logs
-> Codex bridge
-> connected LLM
-> answer/work result
-> evaluation
-> verified learning promotion
```

이 구조가 Hermes/OpenClaw류 에이전트와 다른 점은, 에이전트가 먼저 있는 것이 아니라 **교육센터가 AI 인재를 성장시킨 뒤 에이전트로 고용한다**는 점입니다.

## 설치형 Paideia Agent

고용된 개별 인재는 `Paideia Agent` 설치 키트로 내보낼 수 있습니다.

```powershell
ai22b-talent-foundry build-paideia-agent-kit `
  --employment-record .\employment_record.json `
  --output-dir .\paideia_agent_kit

ai22b-talent-foundry doctor-agent-program `
  --program .\paideia_agent_kit\22b_paideia_agent_program.json `
  --output .\paideia_agent_kit\paideia_doctor_report.json
```

설치 키트에는 `README.md`, `doctor_paideia.ps1`, `start_paideia_chat.ps1`, `build_openclaw_runtime_bundle.ps1`, `build_openclaw_live_smoke_plan.ps1`, `start_openclaw_webchat.ps1`, `paideia_onboarding.template.json`, `adapter_manifests/`가 포함됩니다. Hermes/OpenClaw식 확장을 고려하되, 외부 채널과 커뮤니티 스킬은 기본 비활성화입니다. OpenClaw식 런타임 검증은 설치 폴더 안에서 runtime bundle 생성, no-secret live smoke plan 생성, 로컬 WebChat 실행 순서로 진행합니다.

## Hermes/OpenClaw 스킬 마이그레이션

기존 Hermes/OpenClaw 스킬은 다음 명령으로 Paideia Agent kit에 가져올 수 있습니다.

```powershell
ai22b-talent-foundry migrate-agent-assets `
  --source C:\path\to\skill-folder `
  --paideia-kit C:\path\to\paideia_agent_kit `
  --source-runtime openclaw
```

마이그레이션된 스킬은 즉시 실행되지 않습니다. Paideia는 외부 스킬을 `skills/imported/<runtime>/<skill>/` 아래에 복사하고, wrapper `SKILL.md`와 `paideia_skill_manifest.json`을 만듭니다. 기본 상태는 `disabled`이며, 보스 검토와 doctor 확인 후에만 교육축이나 절차 스킬로 승격해야 합니다.
