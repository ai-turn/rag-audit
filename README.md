# rag-audit

RAG 파이프라인용 린터. Claude Code 플러그인입니다.

코드를 읽고 30개 규칙으로 점검해서, 어디가 왜 문제인지 `file:line`으로 짚고 0~100점 구조 점수를 매깁니다. 점수는 LLM의 감이 아니라 공개된 공식으로 계산합니다.

```
Structure Score: 47/100 (C 31 · E 100 · R 33 · P 50 · O 0 · V 50)
2 CRITICAL / 8 WARN / 6 INFO · determined 30/30 rules

[CRITICAL] RAG-P003 · 답변 불가 처리 없음 — prompts/system.txt:1
근거가 없어도 모델이 지어서 답함 (환각의 프롬프트 측 절반)
Fix: "컨텍스트에 답이 없으면 '문서에서 확인되지 않습니다'라고 답하세요" 한 줄 추가
```

## 동작 방식

1. 의존성 파일로 스택을 알아냅니다
2. 어댑터를 읽습니다 — 프레임워크별 "이 개념은 코드 어디에 있나" 지도
3. 파이프라인 인벤토리를 만듭니다 — 판정은 그다음
4. 30개 규칙을 전부 판정합니다 — 규칙마다 PASS / FINDING / N/A / UNKNOWN
5. 점수를 계산하고 리포트를 씁니다

| 카테고리 | 확인하는 것 |
|---|---|
| C 청킹 (5) | 오버랩, 구조 인지 분할, 메타데이터 보존, CJK 토큰 산정 |
| E 임베딩 (3) | 모델과 코퍼스 언어의 궁합, 색인/서빙 설정 일치 |
| R 검색 (8) | k, 임계값, 질의 전처리, 하이브리드와 RRF 융합, 리랭킹, 멀티턴 재작성 |
| P 프롬프트 (6) | grounding, 답변 불가 처리, 인용 지시 — 프롬프트 원문 텍스트로 판정 |
| O 관측 (4) | 트레이싱, 요청별 청크 기록, 피드백 수집 |
| V 평가 (4) | 골든셋, 회귀 평가, 품질 스코어링 |

원칙은 하나입니다. `file:line` 증거가 없으면 지적하지 않습니다. 확인 못 한 규칙은 UNKNOWN으로 남깁니다.

## 설치와 사용

```
/plugin marketplace add ai-turn/rag-audit
/plugin install rag-audit@rag-audit-marketplace
```

RAG 프로젝트를 연 Claude Code에서:

```
/rag-audit:audit                 # 현재 레포 감사
/rag-audit:audit services/bot    # 특정 경로만
```

"내 RAG 챗봇 구조 좀 봐줘"라고 말해도 됩니다. 플러그인 없이 쓰려면 `plugins/rag-audit/skills/rag-audit/` 폴더를 `~/.claude/skills/`에 복사하세요.

## 점수

- 30개 규칙을 전부 판정한 뒤, 심각도 가중치(CRITICAL 8 / WARN 3 / INFO 1)로 PASS 비율을 냅니다. 공식은 rules.md에 있습니다.
- 같은 코드면 같은 점수. 고치고 다시 돌리면 오른 만큼 보입니다.
- UNKNOWN은 0점 처리합니다. UNKNOWN이 남아 있으면 실제 점수는 표시된 것 이상입니다.

주의할 점 하나. 이건 구조 점수입니다. 100점이어도 답변 품질은 별개 문제고, 품질은 측정해야 압니다. 그 첫걸음은 리포트 끝의 Measure next가 안내합니다.

## 증상별 진입점

| 증상 | 걸리는 규칙 |
|---|---|
| 문서에 없는 내용을 지어서 답한다 | RAG-R002 + RAG-P003 |
| 후속 질문부터 검색 품질이 급락한다 | RAG-R006 |
| 제품 코드나 에러 메시지 검색이 엉뚱한 문서를 반환한다 | RAG-R003 |
| 한국어 문서인데 검색 품질이 유독 낮다 | RAG-E001 |
| 잘못된 답의 원인 청크를 역추적할 수 없다 | RAG-O001 |
| 수정 후 개선 여부를 확인할 방법이 없다 | RAG-V001 |

## 규칙 카탈로그 (v0.2, 30개)

| 카테고리 | 규칙 | 다루는 것 |
|---|---|---|
| C · Chunking & Ingestion | C001–C005 | 오버랩, 구조 인지 분할, 메타데이터, CJK 토큰 산정, 재색인 |
| E · Embedding | E001–E003 | 코퍼스 언어 적합성, 색인/질의 모델 일치, 버전 관리 |
| R · Retrieval | R001–R008 | top-k, 임계값, 하이브리드, 리랭킹, 필터, 멀티턴 질의 재작성, 질의 전처리, RRF 융합 |
| P · Prompt & Generation | P001–P006 | 컨텍스트 구분, grounding, 답변 불가 처리, 인용, 토큰 가드, 배치 순서 |
| O · Observability | O001–O004 | 요청별 청크 기록, 트레이싱, 피드백, 단계별 비용/지연 |
| V · Evaluation readiness | V001–V004 | 골든셋, 회귀 평가, 품질 스코어링, unanswerable 테스트 |

전체 정의는 `plugins/rag-audit/skills/rag-audit/references/rules.md`에 있습니다. 규칙은 프레임워크 중립이고, 어댑터가 프레임워크별 코드 위치를 압니다. 지금은 LangChain/LangGraph 어댑터가 있고, 나머지 스택은 generic 폴백으로 돕니다.

## 테스트 픽스처

`examples/flawed_rag.py`에 위반을 일부러 심어놨습니다. docstring의 반드시 검출(must-find) / 검출 금지(must-not-find) 목록과 감사 결과를 대조하면 스킬 자체를 회귀 테스트할 수 있습니다.

## 로드맵

- 어댑터 추가: LlamaIndex, Spring AI, Haystack (PR 환영)
- 규칙 문서 사이트: 규칙 ID별 근거와 수정 예시
- `/rag-audit:eval-init`: 골든셋 템플릿, 한국어 judge 프롬프트, Langfuse 연동

## 라이선스

MIT
