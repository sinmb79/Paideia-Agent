# Physical AI Simulation/RL Benchmark Notes

작성일: 2026-05-31

## 핵심 결론

보스가 말한 "자기 복제 로봇을 시뮬레이션에 여러 개 띄워 동시에 다른 상황을 학습한다"는 구조는 피지컬 AI/로봇 학습에서 이미 가장 강한 축입니다. 직접 베껴올 핵심은 특정 로봇 모델이 아니라 아래 학습 구조입니다.

1. 본체 정책은 하나이고, 시뮬레이션 안에는 수천 개의 병렬 분신 환경을 둔다.
2. 각 분신은 다른 초기 조건, 난이도, 실패 상황, 센서 잡음, 물리 파라미터를 겪는다.
3. 성공/실패/오답/회복 기록은 바로 본체의 정책과 기억 기판에 반영된다.
4. 실제 배포 전에는 domain randomization과 평가 게이트를 통과한 경험만 승격한다.
5. LLM은 정체성이 아니라 언어/도구/추론 실행 엔진이고, Codex는 로컬 파일, 도구, 검증, 실행을 담당하는 관문이다.

## 참고한 외부 흐름

- NVIDIA Isaac Gym: GPU에서 물리 시뮬레이션과 RL 학습을 함께 돌려 CPU-GPU 병목을 줄이고, 단일 GPU에서 수많은 환경을 동시에 실행하는 방향을 제시했다.
- NVIDIA Isaac Lab: Isaac Sim 기반의 공식 로봇 학습 프레임워크로, 강화학습, 모방학습, 도메인 랜덤화, 센서/액추에이터 모델을 통합한다.
- MuJoCo MJX / MuJoCo Playground: JAX 기반 벡터화로 동일한 물리 장면을 대량 병렬 실행해 RL throughput을 높인다.
- OpenAI dexterous manipulation: 수많은 무작위 시뮬레이션과 domain randomization으로 물리 손 제어 정책을 학습하고 실제 로봇에 전이한 사례다.
- GR00T / DreamGen 계열: 인간 시연과 합성 데이터, 비디오 월드 모델을 섞어 로봇 일반화를 확장하려는 흐름이다.

## 22B-AI에 벤치마킹할 구조

## 성장형 학습에 맞는 시간 구조

중요한 전제는 병렬 시뮬레이션이 성장 순서를 깨면 안 된다는 점입니다. 병렬 에피소드는 "한 아이가 동시에 여러 인생을 사는 것"이 아니라, 현재 성장 단계의 본체 체크포인트에서 출발한 여러 실험 roll-out이어야 합니다.

잘못된 구조:

1. 초등학교, 대학교, 직장 상황을 한꺼번에 섞어 대량 생성한다.
2. 좋은 답변만 모아 memory에 넣는다.
3. 최종 캐릭터가 갑자기 똑똑해진 것처럼 보이게 한다.

이 방식은 성장형 학습이 아니라 후처리된 페르소나 주입에 가깝습니다.

올바른 구조:

1. `age_checkpoint_000`: 태아/영아기 초기 상태를 만든다.
2. 그 상태에서 같은 나이대의 여러 에피소드 분신을 병렬 실행한다.
3. 결과를 평가하고, 그 나이대가 실제로 배울 수 있는 경험만 승격한다.
4. 승격된 경험으로 `memory_substrate`, `learning_ledger`, `reasoning_kibo`를 갱신한다.
5. 갱신된 본체를 `age_checkpoint_001`로 저장한다.
6. 다음 나이/학년은 반드시 이전 체크포인트를 초기 조건으로 사용한다.

즉, 병렬성은 시간축을 건너뛰는 수단이 아니라, 같은 발달 단계 안에서 경험의 폭을 넓히는 수단입니다.

### Checkpointed Development Loop

```text
previous_self_checkpoint
  -> age/stage curriculum
  -> N parallel episode clones
  -> exam + social feedback + safety review
  -> promote/quarantine
  -> consolidated_self_checkpoint
  -> next age/stage
```

이 구조에서 분신들은 독립된 의식이 아닙니다. 본체의 현재 기억과 능력을 복사한 실험 roll-out이며, 검증된 경험만 본체에 다시 통합됩니다. 피지컬 AI에서 하나의 정책 네트워크가 수천 개 환경을 병렬 경험한 뒤 정책 업데이트를 받는 것과 같은 대응입니다.

### 성장형 누적 원칙

- 다음 단계 학습은 항상 이전 단계의 `learning_ledger`, `reasoning_kibo`, `memory_substrate`를 입력으로 받아야 합니다.
- 고등학생 단계는 초등/중등 단계에서 만든 언어, 사회성, 실패 회복, 공부 습관을 전제로 합니다.
- 대학/대학원 리서치 단계는 수능형 독해, 수학, 통계, 글쓰기, 실패 기록을 바탕으로 더 어려운 자료를 다룹니다.
- 에이전트 고용 이후에는 실제 보스와의 대화, 업무 성공/실패, API 실패, 파일 검증 경험이 다시 기보를 확장합니다.
- 미래 단계의 지식은 과거 단계에 직접 주입하지 않습니다. 필요하면 "미래에 배울 잠재 과목"으로만 계획에 둡니다.

### 현재 OpenAI/Codex 연결에서의 의미

현재 ChatGPT/Codex는 grham-쥬니어의 가중치 자체가 아니라 언어/도구 실행 엔진입니다. 따라서 지금 단계의 성장형 학습은 모델 파라미터를 즉시 바꾸는 것이 아니라, 로컬의 `learning_ledger`, `reasoning_kibo`, `memory_substrate`, 대화 로그, 평가 결과를 누적하고 다음 턴의 Codex/LLM 컨텍스트에 반영하는 방식입니다.

나중에 로컬 모델을 별도로 학습할 때는 이 누적 산출물을 LoRA/파인튜닝/검색증강 데이터셋으로 전환할 수 있습니다. 하지만 지금도 성장 순서를 지키려면 모든 대화와 시뮬레이션은 체크포인트 기반으로 누적되어야 합니다.

### 1. Vectorized Life Episodes

인간형 성장 시뮬레이션도 한 개의 선형 인생만 돌리면 느리고 편향됩니다. 한 학년 안에 여러 `episode clone`을 두어 병렬 경험을 수집합니다.

- `school_day_001_a`: 숙제를 잘한 날
- `school_day_001_b`: 숙제를 안 해서 야단맞은 날
- `school_day_001_c`: 친구와 다툰 날
- `school_day_001_d`: 친구에게 먼저 사과한 날
- `research_case_001_a`: 기업 분석에서 가설이 맞은 경우
- `research_case_001_b`: 반례가 맞아 기존 가설을 폐기한 경우

본체는 모든 분신의 경험을 그대로 믿지 않고, 평가/검증을 통과한 요약만 `learning_ledger`와 `memory_substrate`에 승격합니다.

### 2. Domain Randomization for Conversation and Research

로봇에서는 마찰, 질량, 조명, 센서 잡음을 랜덤화합니다. AI 인재에서는 다음을 랜덤화합니다.

- 질문 표현: 존댓말, 반말, 오타, 중간 생략, 감정 섞임
- 사용자 의도: 잡담, 정체성 질문, 업무 지시, 반박, 정정, 스트레스
- 자료 상태: 충분한 자료, 충돌하는 자료, 오래된 자료, 출처 불명확
- 심리/사회 상황: 친구 갈등, 부모 피드백, 실패, 칭찬, 압박감
- 업무 환경: 제한 시간, 파일 누락, API 실패, 권한 부족, 보안 경계

이렇게 해야 케이스별 if문이 아니라 다양한 상황에서 안정적인 대화/추론 정책이 생깁니다.

### 3. Sim-to-Real Equivalent

피지컬 AI의 sim-to-real은 로봇을 실제 세계에 보내기 전 검증하는 과정입니다. 여기서는 다음과 같이 대응됩니다.

- Sim: 학습 시뮬레이터의 대량 대화/시험/업무 에피소드
- Real: 보스와의 실제 채팅, 실제 로컬 파일 작업, 실제 리서치 업무
- Reality gap: 시뮬레이션에서는 잘했지만 보스의 실제 질문에는 어색한 문제
- Domain randomization: 실제 보스 질문의 변형과 실패 조건을 미리 학습
- Gate: 보스 승인, 테스트 점수, 회귀 테스트, 개인정보/저작권 감사

### 4. Curriculum + RL Loop

학습 루프는 다음 단계로 둡니다.

1. `scenario_generator`: 학년/상황/직업군별 시나리오 생성
2. `parallel_episode_runner`: 여러 분신 에피소드 병렬 실행
3. `evaluator`: 성적표, 대화 품질, 근거성, 안전성 평가
4. `reflection_summarizer`: 숨은 사고과정이 아닌 검토 가능한 요약 생성
5. `ledger_promoter`: 기준을 넘은 경험만 학습 원장에 승격
6. `memory_substrate_updater`: 기보 기판의 노드/경로 갱신
7. `codex_chat_bridge`: Codex를 통해 실제 대화와 도구 실행으로 연결

### 5. Codex-First LLM Connection

보스가 지적한 대로 ChatGPT는 단순 API 모델이 아니라 Codex 실행 환경과 연결되어야 합니다.

- Codex: 로컬 파일 읽기/쓰기, 테스트 실행, 브라우징, 도구 호출, 검증, 로그 저장
- LLM: 언어 생성과 고차원 추론 보조
- grham-쥬니어: 로컬 정체성, 학습기보, 성장 원장, 대화 기억

즉, "OpenAI API가 곧 grham-쥬니어"가 아니라, Codex가 로컬 기보를 읽어 LLM에 필요한 맥락을 제공하고, 결과를 다시 검증/저장하는 구조가 맞습니다.

## 구현 제안

첫 구현은 무거운 Isaac/MuJoCo 설치가 아니라, 경량 텍스트 기반 `parallel_life_sim`으로 시작합니다.

- 입력: 학년, 목표 직업군, 시뮬레이션 개수, 난이도, 스트레스 비율
- 출력: `episode_trace.jsonl`, `assessment_transcript.json`, `reasoning_kibo_update.jsonl`
- 병렬화: Python `concurrent.futures`로 episode clones 실행
- 평가: 규칙 기반 + Codex/LLM 평가 보조
- 승격: 기존 `learning_ledger`의 promote/quarantine 정책 재사용

그 다음 단계에서 GPU가 충분하면 Isaac Lab 또는 MuJoCo MJX를 별도 선택 모듈로 붙입니다. 지금 grham-쥬니어는 물리 로봇이 아니므로, 피지컬 AI의 병렬 학습 구조만 먼저 추상화하는 것이 맞습니다.

## 위험과 방지책

- 시뮬레이션 편향: 현실 보스 대화와 달라질 수 있으므로 실제 채팅 로그 기반 평가를 넣는다.
- 가짜 기억: 모든 에피소드는 `simulated_episode`로 표시하고 실제 경험과 구분한다.
- 과잉 승격: LLM 실패나 저품질 답변은 quarantine에 둔다.
- 숨은 chain-of-thought 저장: 내부 추론 원문이 아니라 검토 가능한 요약만 저장한다.
- 개인정보 혼입: 보스 가족, 음성, 로컬 파일 경로는 공개 산출물과 분리한다.

## Sources

- NVIDIA Isaac Gym paper: https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/file/28dd2c7955ce926456240b2ff0100bde-Paper-round2.pdf
- NVIDIA Isaac Lab docs: https://docs.isaacsim.omniverse.nvidia.com/6.0.0/isaac_lab_tutorials/index.html
- NVIDIA Isaac Lab research page: https://research.nvidia.com/publication/2025-09_isaac-lab-gpu-accelerated-simulation-framework-multi-modal-robot-learning
- MuJoCo MJX docs: https://mujoco.readthedocs.io/en/latest/mjx.html
- MuJoCo Playground: https://playground.mujoco.org/
- OpenAI dexterous manipulation paper: https://journals.sagepub.com/doi/full/10.1177/0278364919887447
- OpenAI sim-to-real dynamics randomization: https://openai.com/index/sim-to-real-transfer-of-robotic-control-with-dynamics-randomization/
- NVIDIA GR00T N1: https://research.nvidia.com/labs/lpr/publication/gr00tn1_2025/
- OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses/compact?api-mode=responses
- OpenAI Agents SDK: https://platform.openai.com/docs/guides/agents-sdk
