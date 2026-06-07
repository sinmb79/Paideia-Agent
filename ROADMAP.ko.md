# Paideia Agent 로드맵

[English](ROADMAP.md) | [한국어](ROADMAP.ko.md)

Paideia Agent는 큰 비전을 가진 프로젝트이지만, 공개 프리뷰에서는 먼저 좁고 검증 가능한 제품 중심축이 필요합니다. 이 로드맵은 첫 사용자가 바로 실행할 수 있는 MVP 경계를 고정하기 위한 문서입니다.

## 현재 MVP

```text
Graham Junior 오프라인 온보딩
-> 평가와 커리큘럼 산출물
-> Reasoning Ledger / Ariadne Thread
-> 고용 dossier
-> 로컬 에이전트 kit 준비도
-> first-run/runtime doctor 검증
```

MVP는 비공개 파일, API 키, 생성 체크포인트, 네트워크 호출 없이 실행되어야 합니다. live LLM, import skill, Agent_warrent 등록, projection swarm은 deterministic local 경로가 검증된 뒤 연결합니다.

## 기능 상태

| 영역 | 상태 | 공개 릴리스 의미 |
| --- | --- | --- |
| Graham Junior 온보딩 | Core MVP | 오프라인으로 동작하고 직접 테스트 가능해야 합니다. |
| Reasoning Ledger / Ariadne Thread | Core MVP | 숨은 chain-of-thought가 아니라 검토 가능한 학습 기록입니다. |
| 이력 dossier와 성적표 | Core MVP | 교육, 시험, 리포트, 고용 준비도를 설명해야 합니다. |
| 로컬 에이전트 kit와 doctor | Core MVP | 설치, smoke test, fail-closed 동작을 검증해야 합니다. |
| LLM provider 선택 | Core MVP / Optional live | deterministic local이 기본이며 live provider는 명시 설정이 필요합니다. |
| Agent_warrent / Agent ID Card | Beta | 로컬 export만 제공하고 외부 등록은 보스가 직접 통제합니다. |
| Hermes/OpenClaw skill migration | Experimental | import skill은 기본 격리 및 비활성 상태입니다. |
| Projection swarm | Experimental | 본체 제어 작업 분신이며 검토된 본체 synthesis만 승격합니다. |
| Dashboard / studio UI | Future | CLI runtime과 doctor가 안정된 뒤 추가합니다. |
| Local fine-tuning | Future | 데이터 정책, eval, 보안 gate가 성숙한 뒤 추가합니다. |

## P0 보강

1. README의 3분 데모 경로를 최신 상태로 유지합니다.
2. CI에서 전체 테스트, compile check, package build, public hygiene를 실행합니다.
3. prompt injection, memory poisoning, imported skill, provider secret, generated kit에 대한 security threat model을 유지합니다.
4. 공개 artifact에는 schema 이름을 붙이고, 엄격한 validator 전에 inventory를 먼저 관리합니다.
5. 대형 모듈은 한 번에 쪼개지 않고 policy와 tool execution 경계부터 작게 분리합니다.

## P1 구조화

1. typed `LLMResult`와 provider contract fixture를 도입합니다.
2. public CLI 이름을 깨지 않으면서 tool specs, planners, executors, verifiers를 분리합니다.
3. 핵심 artifact에 JSON schema validation을 추가합니다.
4. 고정된 Graham Junior offline end-to-end integration fixture를 추가합니다.
5. Codex 보조 개발, 공개 hygiene, 문서 작성 규칙을 contributor 문서에 유지합니다.

## P2 제품화

1. CLI doctor가 안정된 뒤 web/desktop dashboard를 추가합니다.
2. sandbox policy가 성숙한 뒤 plugin/skill marketplace 흐름을 추가합니다.
3. subprocess/network tool을 열기 전에 OS/container 격리 정책을 추가합니다.
4. MVP gate가 반복적으로 통과된 뒤 package publish automation을 추가합니다.

## 공개 프리뷰의 비목표

- 실제 인물을 복제하거나 사칭하지 않습니다.
- 저작권 교재 본문을 공개 저장소에 저장하지 않습니다.
- 보스의 데이터, 비공개 기억, 생성된 에이전트를 업로드하지 않습니다.
- 명시적 보스 조치 없이 live LLM/provider check를 실행하지 않습니다.
- deterministic demo를 투자, 의료, 법률, 보안 조언의 증거로 취급하지 않습니다.
