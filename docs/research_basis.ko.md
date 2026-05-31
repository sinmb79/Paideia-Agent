# Paideia Agent 연구 근거와 반영 내용

이 문서는 참고한 프로그램, 연구논문, 보고서가 Paideia Agent의 어떤 설계로 이어졌는지 정리합니다. 단순 참고 목록이 아니라, 실제 제품에 반영된 내용을 함께 기록합니다.

## 에이전트 프로그램

| 출처 | 확인한 점 | Paideia Agent 반영 |
| --- | --- | --- |
| OpenClaw 온보딩 | 첫 실행에서 provider/model, gateway, 채팅/채널, 스킬, 다음 단계를 선택하게 해야 합니다. | `start-console`이 LLM 서비스와 채팅 표면을 먼저 묻고, `paideia_onboarding.template.json`에 선택값과 카탈로그를 기록합니다. |
| OpenClaw 모델 provider 문서 | 에이전트는 provider/model 선택과 fallback 정책이 명확해야 합니다. | `llm_service_catalog`에 OpenAI/Codex, deterministic local, bigram, Transformers, llama.cpp/GGUF 경로를 분리했습니다. |
| OpenClaw agent runtime 문서 | OpenAI/Codex는 런타임 표면일 수 있지만, 그 자체가 에이전트 정체성은 아닙니다. | `llm_identity_policy: application_engine_not_identity`를 기록하고, 정체성은 로컬 교육 산출물에서 오도록 했습니다. |
| Hermes Agent | 설치, 모델 전환, CLI 채팅, 도구, 스킬, 메모리, 게이트웨이, OpenClaw 마이그레이션을 강조합니다. | 설치 키트, doctor 검사, 스킬 마이그레이션 wrapper, adapter manifest, Reasoning Ledger를 추가했습니다. |
| OpenHands | 워크스페이스 에이전트는 계획, 결과, trace 같은 검증 가능한 파일을 남겨야 합니다. | 고용 에이전트의 workspace/dataflow 실행이 계획, 결과, trace, 학습 승격 기록을 남깁니다. |

## 학습과 기억 연구

| 출처 | 확인한 점 | Paideia Agent 반영 |
| --- | --- | --- |
| Reflexion | 언어 피드백과 작업 결과가 모델 가중치 변경 없이 다음 행동을 개선할 수 있습니다. | `learning_ledger.json`에 검토된 업무 결과와 피드백을 승격합니다. |
| Generative Agents | 관찰, 기억 검색, reflection, planning이 장기 일관성에 중요합니다. | `memory_substrate.json`, active memory route, 최근 대화 요약, 성장 체크포인트를 분리했습니다. |
| CoALA | LLM 에이전트는 working/episodic/semantic/procedural memory와 action으로 나눠 볼 수 있습니다. | 기억기판을 episode store, semantic principle, procedural operator, action surface로 나눴습니다. |
| ACT-R | 인간형 인지는 선언기억과 절차기억의 조합으로 모델링할 수 있습니다. | 습관과 문제 해결 절차를 검토 가능한 procedural operator로 기록합니다. |
| Soar | 막힘과 chunking은 문제 해결에서 새 절차 지식을 만들 수 있습니다. | 실패한 시험, 막힌 업무, 정정, 복구 답변을 학습 후보로 남깁니다. |
| Complementary Learning Systems | 빠른 episodic 학습과 느린 구조화 학습은 역할이 다릅니다. | 원경험은 로컬에 두고, 검토된 요약과 원칙만 active memory로 승격합니다. |
| Retrieval practice / test-enhanced learning | 시험은 측정만이 아니라 학습 압력입니다. | 초중고 시험, 수능형 평가, 대학 시험, 리포트, 박사 심사가 Reasoning Ledger를 갱신합니다. |
| 자기조절학습 | 학습은 계획, 수행, 모니터링, 성찰의 반복입니다. | 장기 목표와 job cycle이 성공 기준, trace, 검토 라벨, 다음 학습 규칙을 저장합니다. |
| 통찰 문제 해결 연구 | 어려운 문제는 문제 표상의 재구성이 중요할 수 있습니다. | 반례, 재정의, 자료 탐색 결정, 수정 원칙을 최종 답과 분리해 저장합니다. |

## 피지컬 AI와 시뮬레이션

| 출처 | 확인한 점 | Paideia Agent 반영 |
| --- | --- | --- |
| NVIDIA Isaac Gym / Isaac Lab | 대량 병렬 시뮬레이션은 embodied policy 학습을 빠르게 합니다. | 같은 나이/학년 체크포인트에서 여러 episode rollout을 병렬로 돌리는 구조를 계획했습니다. |
| MuJoCo MJX / Playground | 벡터화된 환경은 다양한 변형을 빠르게 시험할 수 있습니다. | 대화, 학교생활, 스트레스, 친구 갈등, 리서치 상황을 다양화하되 성장 시간축은 유지합니다. |
| OpenAI dexterous manipulation / domain randomization | 시뮬레이션 변형은 실제 배포 전 reality gap을 줄입니다. | 질문 표현, API 실패, 파일 누락, 상충 자료, 사회적 스트레스를 승격 전 평가합니다. |
| GR00T 계열 로봇 보고서 | 시연, 합성 데이터, 시뮬레이션, 실제 피드백이 함께 필요합니다. | 생성 에피소드, 시험, 실제 대화, 실제 업무를 다른 evidence class로 구분하고 promotion/quarantine을 적용합니다. |

## 이번 제품 결정

- 온보딩은 LLM 서비스 선택, 채팅 표면 선택, 롤모델 선택, 육성, 이력서 검토 순서로 명확히 바꿨습니다.
- 첫 테스트 샘플은 `examples/graham_junior_onboarding.answers.json`입니다.
- “추론기보”는 내부 파일명으로 유지하되, 공개 용어는 **Reasoning Ledger / Ariadne Thread**로 바꿨습니다.
- LLM은 연구원과 대화 엔진입니다. AI 인재의 정체성은 로컬 교육기록, 학습원장, 기억기판, dossier에서 옵니다.
- 이력서형 dossier를 제품의 핵심 산출물로 설명합니다.
- 외부 게이트웨이와 마이그레이션 스킬은 기본 비활성화이며, 보스 검토와 doctor 검사를 통과해야 합니다.

## 주요 링크

- OpenClaw onboarding reference: https://docs.openclaw.ai/reference/wizard
- OpenClaw model providers: https://docs.openclaw.ai/providers/models
- OpenClaw agent runtimes: https://docs.openclaw.ai/concepts/agent-runtimes
- Hermes Agent repository: https://github.com/NousResearch/hermes-agent
- OpenHands overview: https://docs.openhands.dev/overview/introduction
- Reflexion: https://arxiv.org/abs/2303.11366
- Generative Agents: https://arxiv.org/abs/2304.03442
- CoALA: https://arxiv.org/abs/2309.02427
- ACT-R: https://act-r.psy.cmu.edu/
- Soar: https://soar.eecs.umich.edu/
- Complementary Learning Systems: https://pubmed.ncbi.nlm.nih.gov/7624455/
- Test-enhanced learning: https://pubmed.ncbi.nlm.nih.gov/16507066/
- Self-regulated learning review: https://pmc.ncbi.nlm.nih.gov/articles/PMC5408091/
- Insight problem-solving review: https://www.nature.com/articles/s44159-023-00257-x
- NVIDIA Isaac Gym paper: https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/file/28dd2c7955ce926456240b2ff0100bde-Paper-round2.pdf
- NVIDIA Isaac Lab: https://docs.isaacsim.omniverse.nvidia.com/6.0.0/isaac_lab_tutorials/index.html
- MuJoCo MJX: https://mujoco.readthedocs.io/en/latest/mjx.html
- OpenAI dexterous manipulation: https://journals.sagepub.com/doi/full/10.1177/0278364919887447
