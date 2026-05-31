# 추론기보 기판 엔진 연구 메모

## 목적

`grham-쥬니어` 샘플 AI의 추론기보는 성격 키워드를 미리 주입하는 장치가 아니라, 학습자료, 과제, 시험, 오답, 피드백, 업무 경험이 쌓이며 만들어지는 검토 가능한 기억 기판이다. LLM은 언어 엔진으로만 쓰고, 에이전트의 정체성, 학습 이력, 문제 접근 습관은 이 기판에서 불러온다.

## 설계 근거

- ACT-R는 인간 인지를 시뮬레이션하기 위한 인지 아키텍처이며, 절차 시스템은 조건-행동 생산규칙과 충돌해결을 다룬다. 그래서 기보 기판에는 `procedural_operator_store`를 둔다.
- Soar는 impasse 기반 문제분해와 chunking으로 새 절차 지식을 만든다. 그래서 막힘을 기록하고, 해결된 시험/과제 경험을 다음 문제의 연산자 후보로 압축한다.
- Soar episodic memory는 실행 중인 상태를 episode로 저장하고 cue 기반으로 검색한다. 그래서 학년별 학습, 시험, 업무 경험을 `episodic_fast_store`로 남기고, 목표 문장과 태그로 활성 경로를 고른다.
- Complementary Learning Systems는 빠른 episodic 학습과 느린 구조화 학습의 상보성을 설명한다. 그래서 기보 기판은 원경험 저장과 느린 의미/원칙 통합을 분리한다.
- CoALA는 LLM 에이전트를 작업기억, episodic/semantic/procedural memory, 행동공간으로 나누는 틀을 제안한다. 그래서 Codex/OpenAI는 언어 엔진이고, 기억과 정체성은 로컬 산출물이 제공한다.
- Retrieval practice 연구는 시험 자체가 장기 보존을 강화할 수 있음을 보인다. 그래서 초등학교부터 대학원까지의 시험은 성적표 작성용이 아니라 기보 진화 압력으로 사용한다.
- 자기조절학습 모델은 forethought, performance, self-reflection 순환을 강조한다. 그래서 각 채팅/업무도 목표 설정, 근거 탐색, 결과 검토, 다음 규칙 수정으로 기록한다.
- insight 연구는 문제 표상 재구조화가 통찰적 해결의 핵심일 수 있음을 다룬다. 그래서 기판에는 막힘, 반례, 재표상, 새 자료 탐색을 별도 루프로 둔다.

## 구현 원칙

- 숨은 chain-of-thought는 저장하지 않는다. 저장되는 것은 요약된 근거, 반례, 오답, 수정된 원칙, 다음 탐색 질문이다.
- 사주 seed는 시뮬레이션 초기 조건을 채우는 상징 데이터일 뿐, 성격이나 투자 결론을 결정론적으로 주입하지 않는다.
- 인물 모방은 사고방식 흉내가 아니라 학습 경로 재현이다. Graham 트랙도 공개된 학습/교육/저작 메타데이터와 가치투자 교육과정을 통해 재현한다.
- 설치된 에이전트의 채팅은 `employment_record`, `agent_manifest`, `learning_ledger`, `memory_substrate`를 읽어 Codex에게 적용할 컨텍스트 패킷을 만든다.

## 참고 출처

- ACT-R 공식 사이트: https://act-r.psy.cmu.edu/
- ACT-R 7 reference manual: https://act-r.psy.cmu.edu/actr7.x/reference-manual.pdf
- Soar procedural learning manual: https://soar.eecs.umich.edu/soar_manual/04_ProceduralKnowledgeLearning/
- Soar episodic memory manual: https://soar.eecs.umich.edu/soar_manual/07_EpisodicMemory/
- CoALA paper: https://arxiv.org/abs/2309.02427
- Complementary Learning Systems paper: https://pubmed.ncbi.nlm.nih.gov/7624455/
- Test-enhanced learning: https://pubmed.ncbi.nlm.nih.gov/16507066/
- Self-regulated learning review: https://pmc.ncbi.nlm.nih.gov/articles/PMC5408091/
- Insight problem-solving review: https://www.nature.com/articles/s44159-023-00257-x
