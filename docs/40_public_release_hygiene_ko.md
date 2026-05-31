# 공개 GitHub 배포 위생 규칙

22B-AI는 보스의 로컬 실험실이므로 GitHub에는 전체 작업 폴더를 그대로 올리지 않습니다. 공개 레포에는 프로그램 실행에 필요한 코드, 공개 가능한 문서, 테스트, 예시 템플릿만 선별해서 올립니다.

## 기본 제외

- `AGENTS.md`: 로컬 작업 규칙과 개인 경로가 들어갈 수 있습니다.
- `docs/log.md`: 작업 중간 로그와 로컬 상태가 들어갈 수 있습니다.
- `data/private`, `data/processed`: 개인 데이터와 생성 말뭉치입니다.
- `models`, `runs`, `apps/*/runs`: 모델 파일, 체크포인트, 실행 산출물, 설치 레지스트리입니다.
- `.env`, API 키, 토큰, 인증 쿠키, 세션 기록, sqlite 로그, 캐시입니다.
- 개인 음성, 가족 이미지, 의료/진료/학습 원본, 로컬 절대경로입니다.

## 공개 전 필수 명령

```powershell
.\scripts\run_tests.ps1
.\scripts\run_doctor.ps1
.\scripts\check_public_repo_hygiene.ps1
```

`check_public_repo_hygiene.ps1`는 Git이 추적할 후보 파일을 기준으로 차단 경로와 비밀정보 패턴을 검사하고, 결과를 `runs/public_repo_hygiene_report.json`에 저장합니다.

## GitHub 업로드 방식

1. 새 GitHub 레포를 만듭니다.
2. `.gitignore`가 적용된 후보 파일만 확인합니다.
3. 개인정보 스캔이 통과한 뒤에만 stage 합니다.
4. README는 한국어/영어가 서로 링크되도록 유지합니다.
5. 실행 산출물 ZIP은 코드 레포에 넣지 않고, 검증된 공개 번들만 필요한 경우 GitHub Release 자산으로 올립니다.
