# 공개 릴리스 준비도

Paideia Agent는 로컬 우선 에이전트 연구 프리뷰입니다. 공개 릴리스 준비도는 테스트 통과만을 뜻하지 않습니다. 보스의 비공개 학습자료, 로컬 메모리, 생성된 실행 상태, 인증정보, 모델 체크포인트가 공개 저장소에 섞이지 않는지도 함께 증명해야 합니다.

## 필수 게이트

공개 배포 또는 릴리스 브랜치 병합 전에는 다음을 실행합니다.

```powershell
python -m compileall src\ai22b\talent_foundry
$env:PYTHONPATH = "src"
python -B -m pytest tests\test_package_smoke.py tests\test_cli_smoke.py -q
.\scripts\check_public_repo_hygiene.ps1
ai22b-talent-foundry audit-public-release-readiness --repo-root . --strict --output .\public_release_readiness.json
```

hygiene 스크립트는 두 가지 위험을 검사합니다.

- 비공개 폴더, 로컬 사용자 경로, API 키, 토큰, 생성된 런타임 산출물 같은 차단 경로와 차단 내용
- `README.md`, `README.ko.md`, `SECURITY.md`, `LICENSE`, `pyproject.toml` 및 패키지 라이선스 메타데이터 같은 공개 릴리스 필수 파일

Python readiness audit는 검토 가능한 `paideia-public-release-readiness/v1` 보고서를 씁니다. 이 검사는 소스 저장소 메타데이터, CI gate, 그리고 `src`, `docs`, `tests`, `scripts`, `examples`, `data/public` 같은 공개 후보 파일을 확인하며, 네트워크 호출, 서브프로세스 실행, 비공개 생성 런타임 상태 검사를 수행하지 않습니다.

## 에이전트 번들 게이트

생성된 에이전트는 소스 저장소에 커밋하지 않습니다. 검토 가능한 로컬 패키지는 다음 명령으로 준비합니다.

```powershell
ai22b-talent-foundry bundle --installed-manifest <installed_agent_manifest.json> --output-dir <bundle_dir>
ai22b-talent-foundry doctor-bundle --bundle-dir <bundle_dir> --output <bundle_dir>\release_doctor_report.json
ai22b-talent-foundry package-bundle --bundle-dir <bundle_dir> --output-zip <bundle_dir>.zip
```

package manifest와 `.sha256` 파일은 아카이브 체크섬을 증명합니다. `install-package`는 로컬 registry에 설치하기 전에 체크섬을 다시 검증합니다.

## 신원 등록

Agent ID Card / Agent_warrent 연동은 기본적으로 로컬 export 경로입니다. Paideia는 등록 payload를 만들고, 로컬 경로, 원문 owner email, credential-like token이 파일에 새지 않았는지 검증할 수 있습니다. 외부 등록은 계속 보스가 직접 수행하는 명시적 수동 작업으로 남습니다.
