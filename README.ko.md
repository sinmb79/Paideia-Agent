# 22B Paideia

22B Paideia는 로컬 우선 AI 인재 육성 프로그램이자 설치형 에이전트 런타임입니다.

이 저장소는 공개 또는 공유 가능한 코드, 문서, 테스트, 공개 메타데이터만 담는 것을 목표로 합니다. 개인 성장 데이터, 로컬 기억, 생성된 에이전트 번들, 모델 체크포인트, 음성 자산, 비공개 교재는 GitHub에 올리지 않습니다.

기본 문서는 영어 README입니다.

- [English README](README.md)
- [Paideia overview](docs/paideia_center.md)
- [Hermes/OpenClaw benchmark summary](docs/paideia_agent_benchmark.en.md)
- [Security policy](SECURITY.md)

## 핵심 차이

- 먼저 교육하고, 나중에 에이전트로 고용합니다.
- 추론기보는 숨은 chain-of-thought가 아니라 검토 가능한 학습 기록입니다.
- LLM은 정체성이 아니라 언어와 도구 실행 엔진입니다.
- 외부 Hermes/OpenClaw 스킬은 가져올 수 있지만, 기본값은 격리와 비활성화입니다.

## 빠른 실행

```powershell
python -m pip install -e .
$env:PYTHONPATH = "src"
ai22b-talent-foundry list-role-models --domain securities_research
```

## 공개 배포 전 점검

```powershell
.\scripts\check_public_repo_hygiene.ps1
```

이 검사는 개인 경로, 비밀키, 런타임 산출물, 모델 체크포인트, private/processed 데이터, 빌드 산출물이 Git 후보에 들어가는지 확인합니다.
