# rag-audit

> RAG 챗봇이 이상한 답을 하는 건 알겠는데, **청킹 탓인지 검색 탓인지 프롬프트 탓인지** 모르겠을 때 돌리는 도구.

린터처럼 동작하는 Claude Code 플러그인입니다. 코드베이스에서 RAG 파이프라인(청킹 → 임베딩 → 검색 → 프롬프트 → 관측 → 평가)을 찾아내고, 28개 규칙을 전수 적용해 `file:line` 근거가 붙은 소견과 0–100 구조 점수를 내놓습니다. 감이 아니라 공식으로요.

```
Structure Score: 48/100 (C 31 · E 100 · R 36 · P 50 · O 0 · V 50)
2 CRITICAL / 8 WARN / 5 INFO · determined 28/28 rules

[CRITICAL] RAG-P003 · 답변 불가 처리 없음
- Evidence: prompts/system.txt:1 — 컨텍스트 부족 시 지시 부재
- Why: 근거가 없어도 모델이 답변을 지어냄 (환각의 프롬프트 측 절반)
- Fix: "컨텍스트에 답이 없으면 '문서에서 확인되지 않습니다'라고 답하세요" 추가
```

## 증상으로 찾아보기

| 이런 증상이 있다면 | 보통 여기가 문제입니다 |
|---|---|
| 문서에 없는 내용을 자신 있게 지어낸다 | RAG-R002 + RAG-P003 — 환각의 검색 절반 + 프롬프트 절반 |
| "그럼 두 번째는요?" 같은 후속 질문만 하면 바보가 된다 | RAG-R006 — 멀티턴 질의 재작성 없음 |
| 제품 코드·에러 메시지로 검색하면 엉뚱한 문서가 나온다 | RAG-R003 — dense-only 검색 |
| 한국어 문서인데 검색 품질이 유독 나쁘다 | RAG-E001 — 코퍼스 언어와 임베딩 모델 불일치 |
| 이상한 답이 나왔는데 어느 청크 때문인지 역추적이 안 된다 | RAG-O001 — 요청별 청크 미기록 |
| 프롬프트를 고치긴 했는데 나아진 건지 알 수가 없다 | RAG-V001 — 골든셋 없음 |

전부 코드에 흔적이 남는 구조적 원인이고, rag-audit는 그 흔적을 찾아 규칙 ID로 짚어줍니다.

## 3분 시작

```
/plugin marketplace add ai-turn/rag-audit
/plugin install rag-audit@rag-audit-marketplace
```

RAG 프로젝트를 연 Claude Code에서:

```
/rag-audit:audit                 # 현재 레포 감사
/rag-audit:audit services/bot    # 특정 경로만
```

커맨드를 외울 필요는 없습니다. "내 RAG 챗봇 구조 좀 봐줘", "왜 자꾸 환각이 생기지?"라고 물으면 스킬이 알아서 발동합니다.

플러그인 없이 스킬만 쓰려면 `plugins/rag-audit/skills/rag-audit/`를 `~/.claude/skills/`에 복사해도 됩니다.

## 점수를 믿어도 되는 이유

"LLM이 매기는 점수"는 보통 실행할 때마다 달라지는 감상문입니다. rag-audit의 점수는 다르게 만들어집니다.

- **전수 판정** — 매 실행 28개 규칙 전부가 PASS / FINDING / N/A / UNKNOWN 중 하나로 끝납니다. 빠뜨리는 규칙이 없어야 실행 간 비교가 성립합니다.
- **계산으로만** — 점수 = 심각도 가중 PASS 비율(CRITICAL 8 / WARN 3 / INFO 1). 공식은 [rules.md](plugins/rag-audit/skills/rag-audit/references/rules.md)에 공개되어 있고, 같은 판정이면 같은 점수입니다. Lighthouse와 같은 방식입니다.
- **증거 없으면 침묵** — 모든 소견에 `file:line`이 붙습니다. 확인하지 못한 규칙은 UNKNOWN으로 정직하게 남고, UNKNOWN이 있는 점수는 하한값으로 읽으면 됩니다.

## 이 도구를 믿지 말아야 할 때

구조 점수 100점이 "답변이 좋다"는 뜻은 아닙니다. 구조가 깨끗해도 검색은 쓰레기를 물어올 수 있고, 그건 측정만이 알 수 있습니다. rag-audit가 책임지는 범위는 "측정을 시작할 수 있는 구조인가"까지이고, 리포트 마지막의 **Measure next** 섹션이 그다음 걸음(청크 로깅 → 골든셋 → faithfulness 체크)을 안내합니다.

## 규칙 카탈로그 (v0.1 — 28개)

| 카테고리 | 규칙 | 다루는 것 |
|---|---|---|
| C · Chunking & Ingestion | C001–C005 | 오버랩, 구조 인지 분할, 메타데이터, CJK 토큰 산정, 재색인 |
| E · Embedding | E001–E003 | 코퍼스 언어 적합성, 색인/질의 모델 일치, 버전 관리 |
| R · Retrieval | R001–R006 | top-k, 임계값, 하이브리드, 리랭킹, 필터, 멀티턴 질의 재작성 |
| P · Prompt & Generation | P001–P006 | 컨텍스트 구분, grounding, 답변 불가 처리, 인용, 토큰 가드, 배치 순서 |
| O · Observability | O001–O004 | 요청별 청크 기록, 트레이싱, 피드백, 단계별 비용/지연 |
| V · Evaluation readiness | V001–V004 | 골든셋, 회귀 평가, 품질 스코어링, unanswerable 테스트 |

규칙은 프레임워크 중립 개념으로 정의되고, 어댑터 파일이 "그 개념이 이 프레임워크 코드 어디에 있는지"를 알려줍니다. 현재 LangChain/LangGraph가 1급 지원이고, 그 외 스택은 generic 폴백으로 동작합니다.

## 테스트 픽스처

`examples/flawed_rag.py`는 위반이 의도적으로 심어진 LangChain 샘플입니다. 파일 상단 docstring의 **must-find**(전부 FINDING으로 나와야 함) / **must-not-find**(FINDING으로 나오면 안 됨) 목록과 대조해 스킬 자체를 회귀 테스트할 수 있습니다. 판정이 갈릴 수 있는 규칙은 의도적으로 목록에서 제외되어 있습니다.

## 로드맵

- 어댑터 추가: LlamaIndex, Spring AI, Haystack (`references/<framework>.md` PR 환영)
- 규칙 문서 사이트: 규칙 ID별 근거·참고문헌·수정 예시 페이지
- `/rag-audit:eval-init`: "Measure next"를 실행해주는 스캐폴딩 — 골든셋 템플릿, 한국어 judge 프롬프트, Langfuse 점수 연동 (자매 프로젝트로 분리 예정)
