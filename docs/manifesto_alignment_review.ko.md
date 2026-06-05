# 설명문 기준 구현 정합성 검토

검토일: 2026-05-31

## 결론

보스가 작성한 설명문의 핵심 철학은 프로젝트 안에 상당 부분 구현되어 있습니다. 특히 "프롬프트형 전문가 흉내"가 아니라 "육성 후 고용", "LLM은 엔진이고 정체성은 로컬 기록", "롤모델은 인격 주입이 아니라 학습 과정 복제", "Reasoning Ledger", "본체 제어 분신 군체"는 코드와 문서에 들어가 있습니다.

다만 공개 첫인상과 제품 흐름은 아직 설명문만큼 강하지 않습니다. README의 첫 화면은 기술 제품 설명에 가깝고, "나 자신을 확장한 에이전트", "분야별 영웅을 학습 과정으로 재구성", "군체능력", "Agent ID Card", "비전문 개발자가 AI와 함께 만드는 실험"이라는 발단이 약합니다. 또한 자기 확장 경로, Agent ID Card 연동, 다중 시뮬레이션 승자 선택, 토큰 절감 지표는 아직 제품 기능으로 완성되지 않았습니다.

## 구현되어 있는 부분

1. 롤모델 기반 육성

- 공개 롤모델 카탈로그와 커리큘럼 카탈로그가 있으며, 인격 주입이 아니라 `learning_process_replication_not_personality_injection` 정책을 사용합니다.
- Graham 외에도 소프트웨어, 데이터, 보안, 마케팅, 교육, 법률, 블록체인, 정보이론 등 에이전트 분야별 롤모델이 추가되어 있습니다.

2. LLM은 엔진, AI 인재는 로컬 기록

- LLM 서비스 선택과 런타임 계약이 분리되어 있고, `application_engine_not_identity` 정책을 사용합니다.
- ChatGPT/Codex, Claude, Gemini, Mistral, OpenRouter, Ollama, LM Studio, 로컬 모델 계열 선택지가 있습니다.

3. 추론기보의 공개 용어 전환

- 내부 파일명은 `reasoning_kibo.jsonl`을 유지하지만, 공개 용어는 Reasoning Ledger / Ariadne Thread로 정리되어 있습니다.
- 초등학교부터 대학원, 고용 후 업무까지 이어지는 누적 성장 기록 구조가 있습니다.

4. 군체능력

- 본체 제어 분신 군체가 구현되어 있습니다.
- 분신은 별도 의식이나 별도 고용 기록이 아니라, 같은 본체가 역할별 작업 투영체를 띄우는 방식입니다.
- 결과는 본체 합성 후 검토 대기 상태로 남고, 바로 장기 성장으로 병합되지 않습니다.

5. Tesla 기판 벤치마킹

- Tesla식 데이터 이동 최적화는 Memory Board Architecture 문서와 dataflow runtime으로 반영되어 있습니다.
- 모든 기억을 LLM에 넣지 않고, 필요한 기억과 근거, 안전 경계만 가까운 컨텍스트로 가져오는 방향입니다.

6. 기존 22B-AI 시스템 보존

- 신용이 성장 시스템은 버려진 것이 아니라 legacy life-development layer로 남겨져 있습니다.
- 향후 공통 life foundation 모듈로 승격할 계획이 문서화되어 있습니다.

## 보완이 필요한 부분

1. README의 발단이 약합니다.

현재 README는 기능 설명 중심입니다. 보스가 적은 "나를 여러 명으로 확장한다", "나의 영웅을 학습 과정으로 재구성한다", "학위보다 통찰과 노하우가 중요하다"는 프로젝트의 감정적, 철학적 출발점이 첫 화면에서 충분히 드러나지 않습니다.

2. 자기 확장 경로가 제품 기능으로 없습니다.

공개 롤모델 경로는 있지만, 사용자 자신의 문서, 업무 방식, 선호, 프로젝트 경험을 로컬 전용으로 안전하게 넣어 "나의 확장 에이전트"를 만드는 온보딩은 아직 없습니다.

3. Agent ID Card 연동이 없습니다.

[Agent ID Card](https://www.agentidcard.org/)는 AIL ID, JWT credential, owner, role, scope, verification, NFT image 등을 제공한다고 설명합니다. 현재 Paideia에는 이 외부 ID를 dossier와 install manifest에 연결하는 export/import 기능이 없습니다.

4. 군체 시뮬레이션은 첫 형태만 있습니다.

본체 제어 분신 군체는 구현되어 있지만, 여러 시나리오를 동시에 굴려 성과를 비교하고, 가장 좋은 결과만 승격하는 simulation rollout scheduler는 아직 충분히 제품화되지 않았습니다.

5. 토큰 절감과 성능 향상은 초기 계량 블록이 들어갔지만, 비교 리포트는 계속 보강해야 합니다.

Agent run과 dataflow run에 `runtime_observability`가 들어가 컨텍스트 크기, 추정 토큰, 선택된 메모리 수, 도구 수, provider usage 존재 여부, fallback, review/promotion/quarantine 카운터를 기록합니다. 다만 일반 프롬프트형 에이전트 대비 비용, 정확도, 재작업률을 비교하는 장기 리포트는 아직 별도 과제로 남아 있습니다.

6. 외부 LLM 어댑터는 doctor 기반 운영 준비 상태로 올라왔지만, 실제 provider별 장기 운영 검증은 계속 필요합니다.

온보딩 선택지는 이제 provider readiness card를 포함합니다. 각 카드에는 doctor 명령, 명시적 live-check 명령, 기본 no-network 정책, secret 비공개, 데이터 전송 범위, 실패 시 fallback, 비용/자원 경고가 들어갑니다. 다만 실제 사용자 환경의 API 키, 요금제, localhost 서버 상태, 모델별 응답 품질은 `doctor-llm-provider --live-check`와 사용자 검토로 계속 확인해야 합니다.

## 보완 계획

### 1단계: 공개 설명문 정비

- `docs/project_manifesto.ko.md`와 `docs/project_manifesto.md`를 README에서 직접 연결합니다.
- README 상단에 "Origin" 섹션을 추가해 프로젝트의 발단을 명확히 설명합니다.
- 한글 README는 보스가 쓴 설명문의 결을 살려 "자기 확장", "롤모델 기반 육성", "군체능력", "로컬 노하우"를 먼저 보여줍니다.

### 2단계: 자기 확장 온보딩

- `owner_self_extension` role-model 타입을 추가합니다.
- 공개 저장소에는 템플릿만 두고, 실제 개인 자료는 `data/private/**` 또는 로컬 storage root로만 받습니다.
- 개인정보, 저작권, 음성/문서 자산 보호 정책을 doctor/hygiene 검사에 연결합니다.

### 3단계: Agent ID Card 연동

- `agent_identity_card.json` 산출물 스키마를 추가합니다.
- `hiring_dossier.json`, `installed_agent_manifest.json`, employment record에 외부 ID 필드를 연결합니다.
- CLI 후보: `export-agent-id-card-payload`, `verify-agent-id-card`.
- 네트워크 등록은 기본 비활성화하고, 사용자가 명시적으로 실행할 때만 수행합니다.

### 4단계: 군체 simulation rollout 고도화

- `simulation_rollouts` 엔진을 추가해 같은 체크포인트에서 여러 에피소드를 실행합니다.
- 각 에피소드에 목표, 스트레스 조건, 실패/회복, 점수, 승격/격리 상태를 기록합니다.
- 좋은 결과만 Reasoning Ledger와 learning ledger에 승격합니다.

### 5단계: 비용/성능 계량

- 각 작업의 컨텍스트 크기, 추정 토큰, 선택된 메모리 수, 재검토 횟수, promotion/quarantine 비율을 기록합니다.
- 현재 P0 반영: agent/dataflow 실행 결과에 `runtime_observability`를 추가해 위 지표를 초기 기록합니다.
- 일반 프롬프트형 에이전트와 Paideia memory-board 경로를 비교하는 리포트를 생성합니다.

### 5.5단계: 기억 수명주기 감사

- 현재 P0 반영: `learning_ledger.json`에 `memory_lifecycle` 리포트를 추가해 기억 쓰기 정책, 승격/격리 기준, 수동 삭제 정책, 복구/마이그레이션 방침, retrieval quality, 개인정보/secret/로컬 경로 위생 검사를 기록합니다.
- 현재 P0 반영: `maintain-hired-memory` 명령으로 감사, 경험 삭제, 백업 기반 복구, 마이그레이션 기록을 실행하고 `memory_lifecycle_maintenance_log.jsonl`에 운영 감사 로그를 남깁니다.
- 남은 운영 검증: 장기 마이그레이션 replay, 다중 백업 회전, 검색 품질 자동 평가를 별도 명령으로 확장합니다.

### 6단계: 실제 LLM 어댑터 강화

- 우선순위: OpenAI/Codex bridge, Ollama, LM Studio, OpenRouter.
- 각 어댑터에 API 키/로컬 주소 점검, 실패 시 fallback, 외부 전송 경고, 데이터 최소화 로그를 넣습니다.
- 현재 P0 반영: 공통 `LLMClient` 경로, provider doctor, secret redaction, private reasoning field 제거, live/auto fallback, chat/provider 경로, 온보딩 readiness card를 추가했습니다.
- 남은 운영 검증: 실제 provider 계정/로컬 서버별 live smoke, 비용 리포트, 모델별 응답 품질 평가를 별도 장기 검증으로 운영합니다.

### 7단계: 설치형 제품 경험

- 온보딩에서 "내 확장 에이전트", "공개 롤모델", "전문팀", "본체 제어 분신 군체"를 명확히 선택하게 합니다.
- 생성 후 성적표, dossier, Agent ID Card payload, 첫 채팅, 첫 업무 실행까지 한 흐름으로 이어지게 합니다.
