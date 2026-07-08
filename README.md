<h1 align="center">rag-audit</h1>

<p align="center">
  <a href="plugins/rag-audit/.claude-plugin/plugin.json"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fai-turn%2Frag-audit%2Fmain%2Fplugins%2Frag-audit%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue&style=flat-square" alt="version"></a>
  <a href="https://code.claude.com/docs/en/plugins"><img src="https://img.shields.io/badge/Claude%20Code-plugin-d97757?style=flat-square" alt="Claude Code plugin"></a>
  <a href="plugins/rag-audit/skills/rag-audit/references/rules.md"><img src="https://img.shields.io/badge/rules-catalog-informational?style=flat-square" alt="rules catalog"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/ai-turn/rag-audit?style=flat-square" alt="license"></a>
</p>

`rag-audit`는 RAG 파이프라인 구조를 점검하는 Claude Code 플러그인입니다.

코드를 읽고 청킹, 임베딩, 검색, 프롬프트, 관측성, 평가 준비도를 규칙 기반으로 판정합니다. 결과는 안정적인 rule ID, 심각도, `file:line` 또는 `NOT FOUND: <searched paths/patterns>` 증거, 수정 제안, 0~100 Structure Score로 나옵니다.

```markdown
**Structure Score: 47/100** · 2 CRITICAL / 8 WARN / 6 INFO · determined all rules

### [CRITICAL] RAG-P003 · No unanswerable handling — `prompts/system.txt:1`
컨텍스트에 답이 없을 때 거절하라는 지시가 없어 모델이 답을 지어낼 수 있습니다.
**Fix:** "문서에서 확인되지 않습니다" 경로를 프롬프트에 명시하세요.
```

## 왜 쓰나

RAG 품질 문제는 보통 한 줄의 프롬프트 문제가 아니라 파이프라인 구조 문제입니다. 예를 들면:

- 관련 없는 문서도 항상 top-k로 프롬프트에 들어감
- 한국어 코퍼스에 영어 중심 임베딩 모델을 사용함
- 후속 질문을 그대로 임베딩해서 검색함
- 어떤 청크가 답변에 들어갔는지 로그가 없음
- 골든셋과 회귀 평가가 없어 수정 효과를 확인할 수 없음

`rag-audit`는 이런 결함을 코드 근거로 찾아냅니다. 답변 품질을 직접 측정하지는 않습니다. 대신 품질을 측정할 수 있는 구조인지, 먼저 고쳐야 할 구조 결함이 무엇인지 알려줍니다.

## 설치와 사용

```bash
/plugin marketplace add ai-turn/rag-audit
/plugin install rag-audit@rag-audit-marketplace
```

RAG 프로젝트를 연 Claude Code에서 실행합니다.

```bash
/rag-audit:audit                 # 현재 레포 감사
/rag-audit:audit services/bot    # 특정 경로만 감사
```

자연어 요청도 됩니다.

```text
내 RAG 챗봇 구조 좀 봐줘
```

플러그인 없이 쓰려면 `plugins/rag-audit/skills/rag-audit/` 폴더를 Claude Code skills 디렉터리에 복사하세요.

## 동작 방식

1. 의존성 파일로 RAG 스택을 감지합니다.
2. 스택별 adapter를 읽어 코드 위치를 찾습니다.
3. ingestion, embedding, retriever, prompt, observability, evaluation 인벤토리를 만듭니다.
4. `rules.md`의 모든 규칙을 `PASS`, `FINDING`, `N/A`, `UNKNOWN` 중 하나로 판정합니다.
5. 판정 결과로 Structure Score와 리포트를 계산합니다.

지원 adapter:

| Adapter | 대상 |
|---|---|
| `langchain.md` | LangChain / LangGraph |
| `generic.md` | 그 외 스택 또는 미지원 프레임워크 |

규칙 전체 정의는 [rules.md](plugins/rag-audit/skills/rag-audit/references/rules.md)에 있습니다. README에는 규칙 카탈로그를 중복하지 않습니다.

## 점수

Structure Score는 규칙 판정에서 기계적으로 계산합니다.

```text
Score = round(100 * PASS weight / non-N/A total weight)
```

가중치:

| Severity | Weight |
|---|---:|
| CRITICAL | 8 |
| WARN | 3 |
| INFO | 1 |

- `PASS`만 점수를 얻습니다.
- `FINDING`과 `UNKNOWN`은 0점입니다.
- `N/A`는 분모에서 제외합니다.
- 카테고리별 점수도 같은 공식으로 계산합니다.
- `UNKNOWN`이 있으면 점수는 하한값입니다.

해석 기준:

| Score | 의미 |
|---|---|
| 90+ | 구조는 대체로 견고함 |
| 60-89 | 심각도 높은 finding부터 고치면 됨 |
| <60 | RAG 구조의 기본 결함부터 봐야 함 |

## 리포트가 보는 영역

| Category | 보는 것 |
|---|---|
| C · Chunking & Ingestion | chunk overlap, 구조 인지 분할, metadata, CJK token sizing, 재색인 |
| E · Embedding | corpus language 적합성, query/document model 일치, embedding version |
| R · Retrieval | top-k, threshold, hybrid, reranking, filter, multi-turn rewrite, query preprocessing, score fusion |
| P · Prompt & Generation | context delimiter, grounding, unanswerable handling, citation, token guard, ordering |
| O · Observability | retrieved chunk log, tracing, feedback, latency/cost visibility |
| V · Evaluation readiness | golden set, regression eval, quality scoring, unanswerable tests |

## Fixtures와 회귀 체크

이 저장소에는 스킬 동작을 확인하기 위한 작은 fixture가 있습니다.

| Fixture | 목적 |
|---|---|
| `examples/flawed_rag.py` | 여러 구조 결함을 일부러 포함한 기본 fixture |
| `examples/bad_hybrid_merge.py` | `RAG-R008` raw score fusion 탐지 fixture |

감사 리포트를 저장한 뒤 expectation과 비교합니다.

```bash
python scripts/check_fixture_report.py examples/flawed_rag.expectations.json path/to/flawed-report.md
python scripts/check_fixture_report.py examples/bad_hybrid_merge.expectations.json path/to/hybrid-report.md
```

표준 입력도 지원합니다.

```bash
python scripts/check_fixture_report.py examples/flawed_rag.expectations.json -
```

이 체크는 Claude 실행 자체를 대체하지 않습니다. 스킬 결과에 반드시 포함되어야 할 finding과 포함되면 안 되는 finding을 검증하는 최소 회귀 안전장치입니다.

## 로드맵

- Adapter 추가: LlamaIndex, Spring AI, Haystack
- Fixture 확장: 규칙별 최소 failing example 추가
- Eval bootstrap: 골든셋 템플릿, 한국어 judge prompt, Langfuse/LangSmith 연동 예시
- 문서화: rule ID별 근거, false positive 기준, 수정 예시 정리

## 라이선스

MIT
