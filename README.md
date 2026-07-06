# rag-audit

RAG 파이프라인을 위한 구조 감사 도구 — **린터처럼 동작하는 Claude Code 플러그인**입니다.

코드베이스에서 RAG 파이프라인(청킹 → 임베딩 → 검색 → 프롬프트 → 관측 → 평가)을 찾아 인벤토리를 만들고, 고정된 규칙 카탈로그(28개 규칙, 6개 카테고리)를 전수 적용해 `규칙 ID + 심각도 + file:line 근거 + 수정안` 형식의 리포트와 0–100 구조 점수를 생성합니다.

```
Structure Score: 48/100 (C 31 · E 100 · R 36 · P 50 · O 0 · V 50)
2 CRITICAL / 8 WARN / 5 INFO · determined 28/28 rules

[CRITICAL] RAG-P003 · 답변 불가 처리 없음
- Evidence: prompts/system.txt:1 — 컨텍스트 부족 시 지시 부재
- Why: 근거가 없어도 모델이 답변을 지어냄 (환각의 프롬프트 측 절반)
- Fix: "컨텍스트에 답이 없으면 '문서에서 확인되지 않습니다'라고 답하세요" 추가
```

## 설계 원칙

- **점수는 계산으로만.** 구조 점수(0–100)는 규칙 판정에서 기계적으로 산출됩니다 — 심각도 가중 PASS 비율이며 공식은 rules.md에 공개되어 있습니다. Lighthouse처럼 결정적이라 실행 간·저장소 간 비교와 개선 추적이 가능합니다. LLM이 감으로 매기는 숫자는 출력하지 않으며, 이 점수는 구조 성숙도이지 답변 품질 측정값이 아닙니다.
- **증거 없으면 침묵.** 모든 지적은 `file:line` 근거가 필수이며, 확인 불가한 규칙은 `UNKNOWN`으로 정직하게 표기합니다.
- **전 규칙 강제 커버리지.** 매 실행마다 26개 규칙 전부가 PASS / FINDING / N/A / UNKNOWN 중 하나로 판정됩니다. 실행 간 일관성은 이 장치로 확보합니다.
- **정적 분석의 한계 명시.** 이 도구는 구조 결함을 찾습니다. 답변 품질 자체는 측정으로만 확인할 수 있고, 리포트가 그 첫걸음("Measure next")을 안내합니다.
- **범용 아키텍처.** 규칙은 프레임워크 중립적 개념으로 정의되고, 프레임워크별 어댑터는 "그 개념이 코드 어디에 있는지"의 탐지 맵입니다. 현재 LangChain/LangGraph 어댑터가 1급 지원이며, 그 외 스택은 generic 폴백으로 동작합니다.

## 설치

```
/plugin marketplace add <this-repo-or-local-path>
/plugin install rag-audit@rag-audit-marketplace
```

플러그인 없이 스킬만 쓰려면 `plugins/rag-audit/skills/rag-audit/` 폴더를 `~/.claude/skills/`에 복사해도 됩니다.

## 사용

```
/rag-audit:audit                 # 현재 레포 감사
/rag-audit:audit services/bot    # 특정 경로 감사
```

또는 자연어로: "내 RAG 챗봇 구조 좀 봐줘", "왜 자꾸 환각이 생기지?"

## 규칙 카테고리 (v0.1 — 28개)

| 카테고리 | 규칙 | 다루는 것 |
|---|---|---|
| C · Chunking & Ingestion | C001–C005 | 오버랩, 구조 인지 분할, 메타데이터, CJK 토큰 산정, 재색인 |
| E · Embedding | E001–E003 | 코퍼스 언어 적합성, 색인/질의 모델 일치, 버전 관리 |
| R · Retrieval | R001–R006 | top-k, 임계값, 하이브리드, 리랭킹, 필터, 멀티턴 질의 재작성 |
| P · Prompt & Generation | P001–P006 | 컨텍스트 구분, grounding, 답변 불가 처리, 인용, 토큰 가드, 배치 순서 |
| O · Observability | O001–O004 | 요청별 청크 기록, 트레이싱, 피드백, 단계별 비용/지연 |
| V · Evaluation readiness | V001–V004 | 골든셋, 회귀 평가, 품질 스코어링, unanswerable 테스트 |

전체 정의: `plugins/rag-audit/skills/rag-audit/references/rules.md`

## 테스트 픽스처

`examples/flawed_rag.py`는 위반이 의도적으로 심어진 LangChain 샘플입니다. 파일 상단 docstring의 **must-find**(전부 FINDING으로 나와야 함) / **must-not-find**(FINDING으로 나오면 안 됨) 목록과 대조해 스킬 자체를 회귀 테스트할 수 있습니다. 판정이 갈릴 수 있는 규칙은 의도적으로 목록에서 제외되어 있습니다.

## 로드맵

- 어댑터 추가: LlamaIndex, Spring AI, Haystack (`references/<framework>.md` PR 환영)
- 규칙 문서 사이트: 규칙 ID별 근거·참고문헌·수정 예시 페이지
- `/rag-audit:eval-init`: "Measure next"를 실행해주는 스캐폴딩 — 골든셋 템플릿, 한국어 judge 프롬프트, Langfuse 점수 연동 (자매 프로젝트로 분리 예정)
