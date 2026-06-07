# 기여 안내

[English](CONTRIBUTING.md) | [한국어](CONTRIBUTING.ko.md)

Paideia Agent는 로컬 우선 연구 프리뷰입니다. 기여는 첫 실행 경로가 이해 가능하고, 검증 가능하고, 공개 안전하게 유지되도록 해야 합니다.

## 개발 원칙

- 새 화면이나 기능을 추가하기 전에 MVP 경로가 계속 동작해야 합니다.
- 한 PR에서는 하나의 경계를 작게 바꾸는 것을 우선합니다.
- 비공개 커리큘럼, 생성된 에이전트, 로컬 기억, 모델 체크포인트, credential, run artifact를 커밋하지 않습니다.
- import skill, provider payload, generated memory candidate는 검토 전까지 신뢰하지 않습니다.
- 온보딩이나 첫 사용에 영향을 주는 변경은 영문/국문 문서를 함께 갱신합니다.

## 로컬 준비

```powershell
python -m pip install -e ".[dev]"
$env:PYTHONPATH = "src"
```

PR 전 권장 검증:

```powershell
python -m compileall src/ai22b/talent_foundry
python -B -m pytest tests -q
python -m build
ruff check src tests --select E9,F63,F7,F82
.\scripts\check_public_repo_hygiene.ps1
```

## 공개 안전 규칙

- 공개 artifact에는 상대경로를 사용합니다.
- provider 원문 응답, secret, private reasoning trace, 개인 로컬 경로를 포함하지 않습니다.
- 저작권 자료나 보스 제공 자료는 공개 저장소에 본문을 넣지 않고 metadata와 reading plan으로 관리합니다.
- live provider test는 명시적으로 실행해야 하며 기본 offline check에서는 실행하지 않습니다.

## 리팩터링 규칙

대형 모듈은 경계를 찾는 동안만 허용합니다. 분리할 때는 public CLI 이름을 유지하고, 호환 shim 또는 테스트를 먼저 둡니다.

우선 분리 순서:

1. `action_policy.py`를 policy models, evaluator, approvals, risk levels로 분리합니다.
2. `tool_registry.py`를 specs, planners, executors, verifiers로 분리합니다.
3. `llm_clients.py`를 typed result contract와 provider adapters로 분리합니다.
4. `agent_execution_loop.py`를 planner, executor, verifier, result models로 분리합니다.

## PR 체크리스트

- 3분 offline demo가 계속 동작합니다.
- first-run doctor와 runtime doctor가 네트워크 호출 없이 통과합니다.
- 생성 산출물은 ignored runtime folder에 남습니다.
- public release hygiene가 통과합니다.
- 실험 기능은 Beta, Experimental, Future 중 하나로 표시합니다.
