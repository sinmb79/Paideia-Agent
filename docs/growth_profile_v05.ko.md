# Growth Profile v0.5-v0.7

이 문서는 `추가 검토` 문서의 보완 요구 중 성장 프로필, Same Sky 평가, 졸업 패키지를 코드로 반영한 내용을 정리합니다.

## 목적

기존 `developmental_ecology.json`과 `life_trace.jsonl`은 성장 환경과 생애 사건을 기록합니다. v0.5부터는 이 기록을 다시 정리해 채팅과 업무 실행에 바로 사용할 수 있는 메모리팩으로 압축합니다.

새 핵심 산출물은 다음과 같습니다.

- `growth_profile.json`: 관계, 감정, 문화/의미, 미적 경험, 학습 비대칭을 요약한 성장 프로필
- `same_sky_eval.json`: 동일 장면을 여러 고용 에이전트에게 제시했을 때 해석 차이를 비교하는 평가 기록
- `graduate_package/`: 이력서, 성적표, 메모리팩, 런타임 매니페스트, 온보딩 프롬프트

## 새 명령

```powershell
ai22b-talent-foundry build-growth-profile `
  --blueprint .\blueprint.json `
  --ecology .\developmental_ecology.json `
  --life-trace .\life_trace.jsonl `
  --output .\growth_profile.json
```

```powershell
ai22b-talent-foundry run-same-sky-eval `
  --agent .\employment_record.a.json `
  --agent .\employment_record.b.json `
  --scene .\scene.json `
  --output .\same_sky_eval.json
```

```powershell
ai22b-talent-foundry build-graduate-package `
  --training-run .\training_run.json `
  --output-dir .\graduate_package
```

## 구현된 엔진

- `growth_profile.py`: 생애 사건과 성장 환경을 관계/감정/의미/미감/비대칭 메모리로 요약합니다.
- `exam_engine_v2.py`: 기존 성적표에 성장 기록 일관성, 관계 회복, 감정 회복, 안전 경계 점수를 추가합니다.
- `same_sky_eval.py`: 같은 장면에서 에이전트별 메모리 근거와 해석 초점을 비교합니다.
- `graduate_package_builder.py`: 최종 고용 검토용 resume, transcript, memory pack, runtime manifest를 생성합니다.

## 메모리 기판 연결

`memory_substrate.json`은 이제 `growth_profile` 보드를 포함합니다.

- `relationship_memory`: 가족/친구 관계, 갈등 회복, 멘토 접근
- `emotional_memory`: 스트레스 분포, 회복 방법, 감정 조절 규칙
- `meaning_memory`: 문화 경험, 가치 질문, 금지된 운명론/차별
- `aesthetic_memory`: 음악, 미술, 문학, 취미, 감각 앵커
- `asymmetry_profile`: 강점 편향, 성장 비용, 도메인 몰입, 안전 경계

이 정보는 숨은 chain-of-thought가 아닙니다. 채팅과 업무에서 검색 가능한 요약 메모리이며, LLM은 이 기록을 읽어 응답을 생성하는 응용 엔진으로만 사용됩니다.

## 릴리스/설치 연결

`growth_profile.json`은 다음 흐름에 포함됩니다.

```text
raise
  -> release bundle
  -> install package
  -> hire-installed employment_record
  -> chat-hired-agent / run-agent-program-chat
```

따라서 새로 육성한 에이전트는 설치 후에도 성장 프로필을 로컬 엔트리포인트로 유지합니다.

## 안전 정책

- 사주/생년월일은 성격 결정이나 예언에 쓰지 않습니다.
- 공개 인물의 사고방식이나 인격을 주입하지 않습니다.
- 실제 개인정보, 가족 정보, 주소, 사적 대화 원문은 공개 산출물에 넣지 않습니다.
- 병렬 분신/군체는 별도의 의식이 아니라 같은 본체 기록에서 나온 후보 실행입니다.
- 숨은 chain-of-thought는 저장하지 않고, 검토 가능한 요약과 수정된 원칙만 남깁니다.
