# CH AI Stock

[![Tests](https://github.com/ryuchihoon/ch-ai-stock/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/ryuchihoon/ch-ai-stock/actions/workflows/test.yml)

AI Agent 기반 주식 기술적 분석 도우미. 미국/한국 주식의 Trend Following 전략 신호를 자연어로 질의할 수 있습니다.

> **주의**: 본 프로젝트는 분석/추천 목적이며, 실거래 기능은 포함하지 않습니다. 모든 분석 결과는 참고용이며 투자 권유가 아닙니다.

## 기능

- **자연어 질의**: "삼성전자 RSI 전략 알려줘", "AAPL MA 크로스오버 분석해줘" 등
- **미국/한국 주식 지원**: 티커 심볼(AAPL) 또는 6자리 종목코드(005930)
- **Trend Following 전략**:
  - 이동평균 교차 (MA Crossover) — 골든크로스/데드크로스
  - RSI 전략 — 과매수/과매도 + 추세 필터
- **기술적 지표**: SMA, EMA, RSI, MACD, 볼린저밴드, ATR
- **종목 검색 및 비교**: 수익률/변동성 비교 분석

## 기술 스택

| 역할 | 라이브러리 |
|------|-----------|
| AI Agent | [Google ADK](https://google.github.io/adk-docs/) + Claude (via LiteLLM) |
| UI | [Mesop](https://mesop-dev.github.io/mesop/) |
| 미국 주식 데이터 | [yfinance](https://github.com/ranaroussi/yfinance) |
| 한국 주식 데이터 | [FinanceDataReader](https://github.com/FinanceData/FinanceDataReader) |
| 기술적 지표 | [ta](https://github.com/bukosabino/ta) |
| 차트 | [Plotly](https://plotly.com/python/) |
| 패키지 관리 | [uv](https://docs.astral.sh/uv/) |

## 요구사항

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Anthropic API Key ([발급](https://console.anthropic.com/settings/keys))

## 설치 및 실행

```bash
# 저장소 클론
git clone https://github.com/your-username/ch-ai-stock.git
cd ch-ai-stock

# 의존성 설치
uv sync

# 환경변수 설정
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY 입력

# Mesop UI 실행
uv run mesop src/ui/app.py
```

브라우저에서 `http://localhost:32123` 접속.

### ADK Web UI로 테스트 (선택)

```bash
export ANTHROPIC_API_KEY=your_key_here
uv run adk web src
```

`http://localhost:8000` 접속 후 `agent` 선택.

### 터미널에서 직접 질의 (선택)

Mesop UI 없이 터미널에서 Agent에 질문할 수 있습니다.

```bash
export ANTHROPIC_API_KEY=your_key_here

# 단일 질문
uv run python scripts/query_agent.py "애플(AAPL) RSI 전략 신호 알려줘"

# 대화형 모드
uv run python scripts/query_agent.py
```

## 예시 질문

- `AAPL을 MA 크로스오버 전략으로 분석해줘`
- `삼성전자(005930) RSI 전략 분석 부탁해`
- `NVDA, TSLA, MSFT 수익률 비교해줘`
- `SK하이닉스 최근 1년 지표 알려줘`
- `사용 가능한 전략 목록 알려줘`

## 프로젝트 구조

```
src/
├── agent/
│   ├── agent.py          # ADK Agent 정의
│   └── tools/
│       ├── stock.py      # 주식 데이터/검색/비교 도구
│       └── analysis.py   # 지표 계산/전략 분석 도구
├── data/
│   ├── base.py           # DataSource 추상 클래스
│   ├── us.py             # 미국 주식 (yfinance)
│   └── kr.py             # 한국 주식 (FinanceDataReader)
├── strategies/
│   ├── base.py           # BaseStrategy / StrategyResult
│   ├── registry.py       # 전략 등록/조회 레지스트리
│   ├── ma_crossover.py   # 이동평균 교차 전략
│   └── rsi.py            # RSI 전략
└── ui/
    └── app.py            # Mesop 채팅 UI
docs/
└── design.md             # 설계 문서
```

## 테스트

```bash
uv run pytest tests/ -v
```

네트워크 없이 실행 가능한 단위 테스트 74개 (데이터 소스 모킹):

| 파일 | 대상 |
|------|------|
| `tests/test_data.py` | USStockDataSource, KRStockDataSource |
| `tests/test_strategies.py` | MACrossoverStrategy, RSIStrategy, StrategyRegistry |
| `tests/test_tools.py` | Agent Tools (get_stock_data, analyze_trend 등) |

## 전략 추가 방법

1. `src/strategies/`에 새 전략 파일 작성 (`BaseStrategy` 상속)
2. `src/strategies/__init__.py`에 import 및 `StrategyRegistry.register()` 추가

## 라이선스

MIT License — [LICENSE](LICENSE) 참조
