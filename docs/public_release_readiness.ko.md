# 공개 릴리스 준비도

Paideia Agent는 로컬 우선 AI 인재 육성 및 에이전트 런타임 연구 프리뷰입니다. 공개 릴리스 준비도는 단순히 테스트가 통과하는지를 넘어서, 보스의 비공개 학습자료, 로컬 메모리, 생성된 실행 산출물, 인증정보, 모델 체크포인트가 공개 저장소에 섞이지 않는지 검증하는 절차입니다.

## 필수 게이트

공개 배포 또는 릴리스 브랜치 병합 전에는 다음 검증을 실행합니다.

```powershell
python -m compileall src\ai22b\talent_foundry
python -m pip install -e ".[security]"
python -m bandit -q -r src -c pyproject.toml -f json -o .\runs\bandit_report.json
python -m pip_audit . --skip-editable --format json --output .\runs\pip_audit_report.json
$env:PYTHONPATH = "src"
python -B -m pytest tests\test_package_smoke.py tests\test_cli_smoke.py -q
.\scripts\check_public_repo_hygiene.ps1
ai22b-talent-foundry audit-public-release-readiness --repo-root . --strict --output .\public_release_readiness.json
ai22b-talent-foundry build-source-sbom --repo-root . --output .\source_sbom.json
ai22b-talent-foundry build-llm-connection-profile --llm-engine deterministic_local --output .\llm_connection_profile.json
ai22b-talent-foundry doctor-package-install --repo-root . --strict --output .\package_install_doctor.json
ai22b-talent-foundry doctor-runtime-contract --repo-root . --strict --output .\runtime_contract_doctor.json
ai22b-talent-foundry doctor-first-run --repo-root . --strict --output .\first_run_doctor.json
```

테스트는 `python -m pip install -e ".[dev]"` 이후 실행합니다. 보안 게이트는 `python -m pip install -e ".[security]"` 이후 실행합니다. 패키지 smoke test는 정적 `pyproject.toml`뿐 아니라 설치된 distribution metadata와 console script entrypoint까지 확인합니다.

## 공개 위생 검사

공개 위생 스크립트는 다음 위험을 빠르게 차단합니다.

- `data/private/**`, `runs/**`, `models/**`, `build/**`, `.env*` 같은 비공개 또는 생성 산출물 경로
- 로컬 사용자 경로, API 키, 토큰, private key, refresh token, auth token
- GitHub diff에서 실제 내용과 다르게 보일 수 있는 bidirectional Unicode 제어문자
- `README.md`, `README.ko.md`, `SECURITY.md`, `LICENSE`, `pyproject.toml`, `schemas/**` 같은 공개 릴리스 필수 파일

Bidi 제어문자는 차단 대상입니다. 그 외 `Cc` 또는 `Cf` 범주의 숨은 제어/서식 문자는 Python release readiness audit의 JSON 리포트에 report-only 관찰값으로 남깁니다. 관찰값에는 파일, codepoint, Unicode 이름과 category, 줄/열, masked escaped surrounding snippet, surrounding-snippet SHA-256이 포함됩니다. masked snippet은 숨은 제어문자 codepoint는 보존하되 일반 텍스트를 `*`로 대체하므로 split secret이나 private text가 공개 리포트에 복사되지 않습니다.

## CI와 보안 증거

GitHub Actions는 `permissions: contents: read`로 실행합니다. `actions/checkout@v6`에는 `persist-credentials: false`를 명시해 CI가 저장소 credential을 불필요하게 보존하지 않도록 합니다. `setup-python`과 `upload-artifact`도 Node 24 대응 공식 action 계열을 사용합니다.

릴리스 준비도 감사는 더 이상 `actions/checkout@v5` 같은 정확한 문자열만 찾지 않습니다. `PyYAML`로 workflow를 파싱해서 job, `needs`, OS/Python matrix, 최소 action major version, artifact retention, checkout credential, job-level permission override, trigger 정책을 구조적으로 확인합니다. 명령어와 artifact 이름은 shell payload이므로 필요한 job 안에서만 marker를 확인합니다.

Security job, release-gates job, optional dependency audit job은 JSON 리포트를 workflow artifact로 업로드합니다. 이 artifact들은 검토 증거이지 장기 보관 데이터가 아니므로 `retention-days: 14` 정책을 사용합니다.

## 선택 의존성 감사

`live-llm`, `local-llm`, `rag`, `fine-tune`, `all` extras는 의존성 트리가 커질 수 있으므로 일반 PR마다 강제하지 않습니다. 대신 `.github/workflows/optional-dependency-audit.yml`에서 주간 또는 수동 실행으로 각 optional extra를 설치하고 `pip-audit --local` 결과를 JSON artifact로 저장합니다.

프리뷰 릴리스는 최신 optional audit 결과를 검토해야 합니다. 안정 릴리스에서는 optional extra의 high 또는 critical 취약점이 해결되지 않은 경우 릴리스를 막는 정책으로 강화해야 합니다.

## 공급망 정책

현재 public preview 단계에서는 공식 GitHub Action tag와 Dependabot을 함께 사용합니다. 모든 action을 full-length commit SHA로 고정하는 방식은 더 강력하지만 유지보수 비용이 큽니다. 정식 릴리스 브랜치를 고정하는 단계에서는 action SHA pinning을 다시 검토해야 합니다.

## 에이전트 번들

생성된 에이전트 번들은 공개 소스 저장소에 커밋하지 않습니다. 검토 가능한 로컬 패키지는 다음 명령으로 준비합니다.

```powershell
ai22b-talent-foundry bundle --installed-manifest <installed_agent_manifest.json> --output-dir <bundle_dir>
ai22b-talent-foundry doctor-bundle --bundle-dir <bundle_dir> --output <bundle_dir>\release_doctor_report.json
ai22b-talent-foundry package-bundle --bundle-dir <bundle_dir> --output-zip <bundle_dir>.zip
```

패키지 manifest와 `.sha256` 파일은 archive checksum을 증명합니다. `install-package`는 에이전트를 로컬 registry에 설치하기 전에 checksum을 다시 검증합니다.

## Agent ID Card 연동

Agent ID Card / Agent_warrent 연동은 기본적으로 로컬 export 경로입니다. Paideia는 등록 payload를 만들고, 로컬 경로, 원문 owner email, credential-like token이 파일에 들어가지 않는지 검증할 수 있습니다. 외부 등록은 보스가 직접 수행하는 명시적 수동 작업으로 유지합니다.
