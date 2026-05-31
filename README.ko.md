# Paideia Agent

[English](README.md) | [한국어 설명문](README.ko.md)

Paideia Agent는 로컬 우선 AI 인재 육성 프로그램이자 설치형 에이전트 런타임입니다. 단순히 프롬프트로 성격을 흉내 내는 챗봇이 아니라, 교육 과정, 시험, 과제, 실패와 회복, 기억 형성, 업무 경험을 누적한 뒤 고용 가능한 에이전트로 내보내는 것을 목표로 합니다.

## 핵심 개념

- **먼저 육성, 나중에 고용**: AI 인재는 성장 기록, 교과 과정, 시험, 리포트, 검토 게이트를 거친 뒤 에이전트가 됩니다.
- **추론기보**: 숨은 chain-of-thought가 아니라, 가설, 근거, 반례, 오답, 수정된 원칙, 업무 습관을 요약한 검토 가능한 학습 기록입니다.
- **기억기판**: 모든 대화 전문을 넣는 것이 아니라, 현재 작업에 필요한 검증된 요약과 절차 기억만 선택해 연결합니다.
- **LLM은 엔진**: OpenAI/Codex 같은 LLM은 언어와 도구 실행 엔진이며, 에이전트의 정체성과 학습 기록은 로컬 산출물에서 옵니다.
- **스킬 마이그레이션**: Hermes/OpenClaw/generic 스킬을 가져올 수 있지만, 기본값은 격리와 비활성화입니다.

## 첫 번째 깊은 트랙

첫 구현 트랙은 증권 리서치입니다.

```text
domain: securities_research
role_model: graham_value_investing
sample talent: grham-junior
```

이 트랙은 Benjamin Graham의 공개적으로 확인 가능한 학습 환경과 가치투자 계보에서 영감을 받습니다. 다만 Graham의 성격이나 결론을 미리 주입하지 않습니다. 공개 근거가 있는 학습 조건, 교과 과정, 시험, 과제, 리포트, 피드백 루프를 구성해 AI 인재가 그 과정 안에서 자기 추론기보를 만들어가도록 설계합니다.

## 실행 예시

```powershell
python -m pip install -e .
$env:PYTHONPATH = "src"
ai22b-talent-foundry list-role-models --domain securities_research
```

Graham 트랙 블루프린트 예시:

```powershell
ai22b-talent-foundry blueprint `
  --request "Raise a separate Graham learning-path sample AI without modifying existing talents." `
  --talent-name "grham-junior" `
  --gender "male" `
  --owner "Boss" `
  --domain securities_research `
  --role-model graham_value_investing
```

설치형 Paideia Agent kit 생성:

```powershell
ai22b-talent-foundry build-paideia-agent-kit `
  --employment-record .\employment_record.json `
  --output-dir .\paideia_agent_kit

ai22b-talent-foundry doctor-agent-program `
  --program .\paideia_agent_kit\22b_paideia_agent_program.json
```

## Hermes/OpenClaw 스킬 가져오기

```powershell
ai22b-talent-foundry migrate-agent-assets `
  --source C:\path\to\skill-folder `
  --paideia-kit C:\path\to\paideia_agent_kit `
  --source-runtime openclaw
```

가져온 스킬은 `skills/imported/<runtime>/<skill>/` 아래에 복사됩니다. 즉시 실행되지 않고, wrapper `SKILL.md`와 `paideia_skill_manifest.json`을 만든 뒤 `disabled` 상태로 보관됩니다. 보스 검토, 위험 패턴 확인, doctor 검사를 통과한 뒤에만 교육축 또는 절차 스킬로 승격해야 합니다.

## 공개 저장소 원칙

이 저장소는 공개 가능한 코드, 문서, 테스트, 공개 메타데이터만 담습니다. 개인 성장 데이터, 로컬 기억, 생성된 에이전트 번들, 모델 체크포인트, 음성 자산, 비공개 교재는 GitHub에 올리지 않습니다.

공개 전 점검:

```powershell
.\scripts\check_public_repo_hygiene.ps1
```

## 참고 문서

- [Paideia Agent overview](docs/paideia_center.md)
- [Hermes/OpenClaw benchmark summary](docs/paideia_agent_benchmark.en.md)
- [Security policy](SECURITY.md)
