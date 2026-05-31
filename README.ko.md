# Paideia Agent

[English](README.md) | [한국어 설명문](README.ko.md)

Paideia Agent는 로컬 우선 AI 인재 육성 프로그램이자 설치형 에이전트 런타임입니다. 단순히 프롬프트로 성격을 흉내 내는 챗봇이 아니라, 교육 과정, 시험, 과제, 실패와 회복, 기억 형성, 업무 경험을 누적한 뒤 고용 가능한 에이전트로 내보내는 것을 목표로 합니다.

## 핵심 개념

- **먼저 육성, 나중에 고용**: AI 인재는 성장 기록, 교과 과정, 시험, 리포트, 검토 게이트를 거친 뒤 에이전트가 됩니다.
- **Reasoning Ledger / Ariadne Thread**: 기존의 “추론기보”를 외국 사용자도 이해하기 쉬운 용어로 정리한 이름입니다. 숨은 chain-of-thought가 아니라, 가설, 근거, 반례, 오답, 수정된 원칙, 업무 습관을 요약한 검토 가능한 학습 기록입니다. 내부 호환 파일명은 `reasoning_kibo.jsonl`로 유지합니다.
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

이 트랙은 Benjamin Graham의 공개적으로 확인 가능한 학습 환경과 가치투자 계보에서 영감을 받습니다. 다만 Graham의 성격이나 결론을 미리 주입하지 않습니다. 공개 근거가 있는 학습 조건, 교과 과정, 시험, 과제, 리포트, 피드백 루프를 구성해 AI 인재가 그 과정 안에서 자기 Reasoning Ledger를 만들어가도록 설계합니다.

## 실행 예시

먼저 Graham Junior 샘플을 온보딩으로 바로 실행할 수 있습니다.

```powershell
ai22b-talent-foundry start-console `
  --answers examples\graham_junior_onboarding.answers.json
```

이 샘플은 먼저 `openai_chatgpt_codex` LLM 서비스와 `codex-bridge-chat` 채팅 표면을 선택한 뒤, 선택된 LLM을 교육과정 연구원으로 사용해 Graham 기반 증권 리서치 트랙을 육성합니다.

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

## 온보딩 모델

Paideia Agent의 첫 실행 순서는 다음과 같습니다.

1. LLM 서비스를 선택합니다.
2. 채팅 표면을 선택합니다.
3. Graham Junior 샘플 또는 사용자가 원하는 롤모델/분야를 선택합니다.
4. 선택한 LLM이 연구원 역할로 사용자 요청을 교육과정, 평가, 성장 입력으로 바꿉니다.
5. 육성 후 이력서형 dossier를 검토하고 채팅 또는 업무 실행을 시작합니다.

지원되는 초기 LLM 서비스는 `openai_chatgpt_codex`, `deterministic_local`, `bigram_local`, `transformers_local`, `llama_cpp_local`입니다. 지원되는 초기 채팅 표면은 `codex-bridge-chat`, `cli-console`, `dataflow-job`, 그리고 기본 비활성화 상태의 `openclaw-style-gateway` 어댑터입니다.

## 이력서형 Dossier

`hiring_dossier.json`과 `HIRING_DOSSIER.ko.md`는 육성된 AI 인재를 실제 에이전트로 고용하기 전 확인하는 이력서형 기록입니다. 여기에는 이름, 성별, 출생 설정, 학력, 전공, 성적표, 논문/리포트, 프로젝트, 활동, 시험 결과, 박사 심사, 고용 권한, 금지사항, 계속 성장 정책이 들어갑니다.

관련 파일:

- `hiring_dossier.json`: 도구와 어댑터가 읽는 구조화 이력서.
- `HIRING_DOSSIER.ko.md`: 사람이 읽는 한글 이력서.
- `assessment_transcript.json`: 시험과 리포트 성적표.
- `learning_ledger.json`: 검증된 학습 경험 원장.
- `reasoning_kibo.jsonl`: Reasoning Ledger의 내부 호환 파일.

## 연구 근거

참고한 연구논문, 보고서, 프로그램과 Paideia Agent에 반영된 내용을 별도 문서로 정리했습니다.

- [연구 근거와 반영 내용](docs/research_basis.ko.md)
- [Research Basis](docs/research_basis.md)
- [Tesla식 데이터플로우 기판 벤치마킹](docs/tesla_board_benchmark.ko.md): 보스가 제안한 테슬라 AI 칩/기판 비유를 기억 지역성, 컨텍스트 패킹, 학습 승격, Reasoning Ledger 구조로 번역한 문서입니다.
- [기존 22B-AI 시스템 계승 메모](docs/legacy_system_integration.ko.md): 이전 신용 성장 시스템과 from-scratch 모델 작업을 Paideia의 legacy foundation으로 계승하는 방식을 설명합니다.

## 공개 저장소 원칙

이 저장소는 공개 가능한 코드, 문서, 테스트, 공개 메타데이터만 담습니다. 개인 성장 데이터, 로컬 기억, 생성된 에이전트 번들, 모델 체크포인트, 음성 자산, 비공개 교재는 GitHub에 올리지 않습니다.

공개 전 점검:

```powershell
.\scripts\check_public_repo_hygiene.ps1
```

## 참고 문서

- [Paideia Agent overview](docs/paideia_center.md)
- [Hermes/OpenClaw benchmark summary](docs/paideia_agent_benchmark.en.md)
- [연구 근거와 반영 내용](docs/research_basis.ko.md)
- [Tesla식 데이터플로우 기판 벤치마킹](docs/tesla_board_benchmark.ko.md)
- [기존 22B-AI 시스템 계승 메모](docs/legacy_system_integration.ko.md)
- [Security policy](SECURITY.md)
