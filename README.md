# rag-audit

RAG 파이프라인의 구조를 점검하는 Claude Code 플러그인입니다. 코드베이스에서 파이프라인 여섯 단계(청킹, 임베딩, 검색, 프롬프트, 관측, 평가)를 찾아 28개 규칙으로 전수 판정하고, `file:line` 근거가 붙은 소견과 0~100 구조 점수를 보고합니다.

```
Structure Score: 48/100 (C 31 · E 100 · R 36 · P 50 · O 0 · V 50)
2 CRITICAL / 8 WARN / 5 INFO · determined 28/28 rules

[CRITICAL] RAG-P003 · 답변 불가 처리 없음 — prompts/system.txt:1
근거가 없어도 모델이 지어서 답함 (환각의 프롬프트 측 절반)
Fix: "컨텍스트에 답이 없으면 '문서에서 확인되지 않습니다'라고 답하세요" 한 줄 추가
```

## 동작 방식

감사는 여섯 단계로 진행됩니다.

1. 의존성 파일(requirements.txt, package.json 등)로 스택 감지
2. 어댑터 로드 — 각 개념이 이 프레임워크 코드 어디에 있는지 적어 둔 지도
3. 파이프라인 인벤토리 작성 — 판정에 앞서 코드 지도부터 만듭니다
4. 28개 규칙 전수 판정 — 규칙마다 PASS / FINDING / N/A / UNKNOWN 중 하나로 끝납니다
5. 점수 계산 — 심각도 가중 PASS 비율
6. 리포트 출력

카테고리별로 코드에서 실제 확인하는 내용은 다음과 같습니다.

| 카테고리 | 코드에서 확인하는 것 |
|---|---|
| C 청킹 (5개) | 스플리터 인자 — 오버랩이 0인지, 마크다운에 고정 길이 분할을 쓰는지, 메타데이터가 청크에 남는지 |
| E 임베딩 (3개) | 모델명이 코퍼스 언어에 맞는지, 색인 스크립트와 서빙 코드의 임베딩 설정이 서로 같은지 |
| R 검색 (6개) | k와 임계값, BM25/하이브리드 유무, 리랭커 유무, 멀티턴 질의 재작성 단계 유무 |
| P 프롬프트 (6개) | 프롬프트 원문에 grounding 지시, 답변 불가 처리, 인용 지시가 실제 문장으로 있는지 |
| O 관측 (4개) | 트레이싱 초기화 여부, 검색 스팬에 청크 ID와 점수가 기록되는지 |
| V 평가 (4개) | 골든셋 파일, CI 평가 워크플로, 스코어링 코드가 존재하는지 |

판정 규율은 하나입니다. `file:line` 증거를 대지 못하면 지적하지 않고 UNKNOWN으로 남깁니다.

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

"내 RAG 챗봇 구조 좀 봐줘" 같은 자연어 요청에도 스킬이 발동합니다. 플러그인 없이 쓰려면 `plugins/rag-audit/skills/rag-audit/` 폴더를 `~/.claude/skills/`에 복사하면 됩니다.

## 점수 계산

- 매 실행 28개 규칙 전부가 PASS / FINDING / N/A / UNKNOWN 중 하나로 판정됩니다. 빠지는 규칙이 없어야 실행 간 비교가 성립합니다.
- 점수는 심각도 가중 PASS 비율입니다. 가중치는 CRITICAL 8, WARN 3, INFO 1이며 공식은 rules.md에 공개되어 있습니다. 같은 판정이면 같은 점수가 나옵니다.
- UNKNOWN은 0점으로 계산합니다. UNKNOWN이 남아 있는 점수는 하한값으로 읽으면 됩니다.

이 점수는 구조 점수입니다. 100점이라도 답변 품질을 보장하지는 않으며, 품질은 측정으로만 확인됩니다. 리포트 끝의 Measure next(다음 측정 단계) 섹션이 청크 로깅, 골든셋 구축, faithfulness 점검 순서로 다음 단계를 안내합니다.

## 증상별 진입점

| 증상 | 걸리는 규칙 |
|---|---|
| 문서에 없는 내용을 지어서 답한다 | RAG-R002 + RAG-P003 |
| 후속 질문부터 검색 품질이 급락한다 | RAG-R006 |
| 제품 코드나 에러 메시지 검색이 엉뚱한 문서를 반환한다 | RAG-R003 |
| 한국어 문서인데 검색 품질이 유독 낮다 | RAG-E001 |
| 잘못된 답의 원인 청크를 역추적할 수 없다 | RAG-O001 |
| 수정 후 개선 여부를 확인할 방법이 없다 | RAG-V001 |

## 규칙 카탈로그 (v0.1, 28개)

| 카테고리 | 규칙 | 다루는 것 |
|---|---|---|
| C · Chunking & Ingestion | C001–C005 | 오버랩, 구조 인지 분할, 메타데이터, CJK 토큰 산정, 재색인 |
| E · Embedding | E001–E003 | 코퍼스 언어 적합성, 색인/질의 모델 일치, 버전 관리 |
| R · Retrieval | R001–R006 | top-k, 임계값, 하이브리드, 리랭킹, 필터, 멀티턴 질의 재작성 |
| P · Prompt & Generation | P001–P006 | 컨텍스트 구분, grounding, 답변 불가 처리, 인용, 토큰 가드, 배치 순서 |
| O · Observability | O001–O004 | 요청별 청크 기록, 트레이싱, 피드백, 단계별 비용/지연 |
| V · Evaluation readiness | V001–V004 | 골든셋, 회귀 평가, 품질 스코어링, unanswerable 테스트 |

전체 정의는 `plugins/rag-audit/skills/rag-audit/references/rules.md`에 있습니다. 규칙은 프레임워크 중립 개념으로 정의되고, 어댑터 파일이 프레임워크별 코드 위치를 안내합니다. 현재 LangChain/LangGraph 어댑터가 있으며 그 외 스택은 generic 폴백으로 동작합니다.

## 테스트 픽스처

`examples/flawed_rag.py`는 위반을 일부러 심어 둔 LangChain 샘플입니다. 파일 상단 docstring의 반드시 검출(must-find) / 검출 금지(must-not-find) 목록과 감사 결과를 대조해 스킬 자체를 회귀 테스트할 수 있습니다. 판정이 갈릴 수 있는 규칙은 목록에서 의도적으로 제외했습니다.

## 로드맵

- 어댑터 추가: LlamaIndex, Spring AI, Haystack (PR 환영)
- 규칙 문서 사이트: 규칙 ID별 근거와 수정 예시
- `/rag-audit:eval-init`: 골든셋 템플릿, 한국어 judge 프롬프트, Langfuse 연동

## 라이선스

MIT
