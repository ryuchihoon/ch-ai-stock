# CH AI Stock - 설계 문서

## 1. 프로젝트 개요

AI Agent 기반 주식 거래 도우미. 미국/한국 주식에 대해 Trend Following 전략을 포함한 기술적 분석을 수행하고, 매매 추천을 제공한다. 실거래 연동은 하지 않으며 분석/추천에 집중한다.

### 핵심 목표
- 자연어로 주식 분석 요청 → Agent가 도구를 조합해 분석 결과 반환
- Trend Following 전략을 중심으로 다양한 전략을 플러그인 방식으로 확장 가능
- 향후 상위 Orchestrator Agent가 이 Agent를 sub-agent로 호출하는 구조를 지원

---

## 2. 기술 스택

| 역할 | 선택 | 비고 |
|------|------|------|
| Agent Framework | Google ADK | LiteLLM으로 모델 연동 |
| LLM | Claude (Anthropic, via LiteLLM) | claude-opus-4-5 |
| UI | Mesop | ADK 공식 연동 지원 |
| US 주식 데이터 | yfinance | 일봉 OHLCV |
| KR 주식 데이터 | FinanceDataReader | pykrx는 Python 3.14 미지원으로 제외 |
| 기술적 지표 | ta | pandas-ta→numba→llvmlite가 Python 3.14 미지원으로 대체 |
| 차트 | Plotly | Mesop 내 렌더링 |
| 언어 | Python 3.12+ | |
| 패키지 관리 | uv | |

---

## 3. 시스템 아키텍처

```
┌──────────────────────────────────────────────────┐
│                   Mesop UI                       │
│  - 채팅 인터페이스                                │
│  - Plotly 차트 표시                               │
│  - 분석 결과 카드                                 │
└─────────────────────┬────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│      Google ADK Agent (Claude via LiteLLM)       │
│                                                  │
│  System Prompt: 주식 분석 전문가 페르소나          │
│                                                  │
│  Tools:                                          │
│  ├── get_stock_data       일봉 OHLCV 조회         │
│  ├── get_indicators       기술적 지표 계산         │
│  ├── analyze_trend        전략 분석 실행           │
│  ├── search_stock         종목 검색               │
│  └── compare_stocks       종목 비교               │
└──────────┬───────────────────┬───────────────────┘
           │                   │
┌──────────▼──────┐   ┌────────▼──────────────────┐
│   Data Layer    │   │    Strategy Engine        │
│                 │   │                           │
│  DataSource     │   │  StrategyRegistry         │
│  ├── USStock    │   │  ├── MACrossover          │
│  │   (yfinance) │   │  ├── RSI                  │
│  └── KRStock    │   │  ├── DonchianChannel (P2) │
│      (FDR)      │   │  ├── ATRTrend      (P2)   │
│                 │   │  └── Turtle        (P2)   │
└─────────────────┘   └───────────────────────────┘
```

---

## 4. 프로젝트 디렉토리 구조

```
ch-ai-stock/
├── docs/
│   └── design.md
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py          # ADK Agent 정의, Tools 등록
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── stock.py      # get_stock_data, search_stock, compare_stocks
│   │       └── analysis.py   # get_indicators, analyze_trend
│   ├── data/
│   │   ├── __init__.py
│   │   ├── base.py           # DataSource 추상 클래스
│   │   ├── us.py             # USStockDataSource (yfinance)
│   │   └── kr.py             # KRStockDataSource (FinanceDataReader)
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py           # BaseStrategy, StrategyResult
│   │   ├── registry.py       # StrategyRegistry (플러그인 관리)
│   │   ├── ma_crossover.py   # Phase 1 (구현 완료)
│   │   ├── rsi.py            # Phase 1 (구현 완료)
│   │   ├── donchian.py       # Phase 2 (예정)
│   │   ├── atr_trend.py      # Phase 2 (예정)
│   │   └── turtle.py         # Phase 2 (예정)
│   └── ui/
│       ├── __init__.py
│       └── app.py            # Mesop 앱
├── tests/
│   ├── test_data.py
│   ├── test_strategies.py
│   └── test_tools.py
├── pyproject.toml
└── .env.example
```

---

## 5. 데이터 레이어 설계

### DataSource 추상 인터페이스

```python
class DataSource(ABC):
    @abstractmethod
    def get_ohlcv(self, ticker: str, period: str) -> pd.DataFrame:
        """
        Returns DataFrame with columns: date, open, high, low, close, volume
        period: "3mo" | "6mo" | "1y" | "2y" | "5y"
        """
        pass

    @abstractmethod
    def search(self, query: str) -> list[StockInfo]:
        pass

    @abstractmethod
    def get_info(self, ticker: str) -> StockInfo:
        pass
```

### Ticker 규칙
- US 주식: 그대로 사용 (`AAPL`, `MSFT`, `NVDA`)
- KR 주식: 6자리 숫자 코드 (`005930`, `000660`)
- Agent가 ticker를 받으면 숫자 6자리인지로 KR/US 자동 판별

---

## 6. Strategy Engine 설계

### 핵심 원칙
- 모든 전략은 `BaseStrategy`를 상속
- `StrategyRegistry`에 등록하면 Agent가 이름으로 호출 가능
- 전략 추가 시 기존 코드 수정 없이 새 파일만 추가

### BaseStrategy 인터페이스

```python
@dataclass
class StrategyResult:
    ticker: str
    signal: Literal["BUY", "SELL", "HOLD"]
    strength: float          # 0.0 ~ 1.0 (신호 강도)
    reason: str              # Agent가 사용자에게 설명할 근거
    chart_data: dict         # Plotly figure dict
    indicators: dict         # 계산된 지표값 스냅샷

class BaseStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def default_params(self) -> dict: ...

    @abstractmethod
    def analyze(self, data: pd.DataFrame, params: dict) -> StrategyResult: ...
```

### StrategyRegistry

```python
class StrategyRegistry:
    _strategies: dict[str, BaseStrategy] = {}

    @classmethod
    def register(cls, strategy: BaseStrategy): ...

    @classmethod
    def get(cls, name: str) -> BaseStrategy: ...

    @classmethod
    def list_all(cls) -> list[dict]: ...  # name + description 목록
```

### Phase 1 전략 명세

#### MACrossoverStrategy
- 지표: SMA 단기(기본 20일) / 장기(기본 60일)
- 신호: 단기선이 장기선을 상향 돌파 → BUY, 하향 돌파 → SELL
- 파라미터: `short_window`, `long_window`

#### RSIStrategy
- 지표: RSI (기본 14일)
- 신호: RSI > 70 과매수 권역 진입/이탈, RSI < 30 과매도 권역 진입/이탈
- 트렌드 맥락: 60일 SMA 방향으로 신호 필터링
- 파라미터: `period`, `overbought`, `oversold`

### Phase 2 전략 명세 (예정)

#### DonchianChannelStrategy
- 지표: N일 최고가/최저가 채널
- 신호: 신고가 돌파 → BUY, 신저가 이탈 → SELL
- 파라미터: `window` (기본 20일)

#### ATRTrendStrategy
- 지표: ATR 기반 변동성 측정 + 추세 판단
- 신호: ATR 배수 기반 지지/저항 돌파
- 파라미터: `atr_period`, `multiplier`

#### TurtleStrategy
- Turtle Trading Rules 구현 (System 1: 20일, System 2: 55일)
- 진입: N일 신고가 돌파, 청산: N일 신저가 이탈
- 파라미터: `entry_window`, `exit_window`

---

## 7. Agent 설계

### System Prompt 방향
- 주식 분석 전문가 페르소나
- 한국어로 응답
- 분석 결과를 차트와 함께 설명하도록 유도
- 투자 권유가 아닌 분석/참고 정보임을 명시

### Tools 명세

```python
def get_stock_data(ticker: str, period: str = "1y") -> dict:
    """
    ticker: 종목 코드 (US: AAPL, KR: 005930)
    period: 3mo | 6mo | 1y | 2y | 5y
    returns: OHLCV 데이터 요약 + 기본 통계
    """

def get_indicators(ticker: str, period: str = "1y",
                   indicators: list[str] = ["sma_20", "sma_60", "rsi_14"]) -> dict:
    """
    지원 지표: sma_N, ema_N, rsi_N, macd, bb_N, atr_N, volume_ma_N
    returns: 최근 N일 지표값 + 차트 데이터
    """

def analyze_trend(ticker: str, strategy: str,
                  period: str = "1y", params: dict = {}) -> dict:
    """
    strategy: 'ma_crossover' | 'rsi' | 'donchian' | 'atr_trend' | 'turtle'
    returns: StrategyResult (신호, 강도, 근거, 차트)
    """

def search_stock(query: str, market: str = "all") -> list[dict]:
    """
    market: 'us' | 'kr' | 'all'
    query: 종목명 또는 티커 일부
    returns: 매칭 종목 목록
    """

def compare_stocks(tickers: list[str], metric: str = "performance",
                   period: str = "1y") -> dict:
    """
    metric: 'performance' | 'volatility'
    returns: 비교 분석 결과
    """
```

---

## 8. Mesop UI 설계

### 화면 구성
```
┌─────────────────────────────────────────┐
│  CH AI Stock              [설정]        │
├─────────────────────────────────────────┤
│                                         │
│  [채팅 영역]                             │
│  - 사용자 메시지                         │
│  - Agent 텍스트 응답                     │
│  - 차트 카드 (Plotly iframe)            │
│  - 분석 결과 테이블                      │
│                                         │
├─────────────────────────────────────────┤
│  [입력창]                    [전송]      │
└─────────────────────────────────────────┘
```

### 주요 컴포넌트
- `chat_message`: 사용자/Agent 메시지 버블
- `chart_card`: Plotly 차트를 HTML로 임베드
- `signal_badge`: BUY/SELL/HOLD 신호를 색상으로 표시
- `indicator_table`: 지표값 테이블

---

## 9. 개발 단계

### Phase 1 - 기반 구축 ✅ 완료
- [x] 프로젝트 초기 설정 (uv, pyproject.toml)
- [x] Data Layer: USStockDataSource, KRStockDataSource
- [x] Strategy Engine: BaseStrategy, StrategyRegistry
- [x] 전략 구현: MACrossoverStrategy, RSIStrategy
- [x] ADK Agent + Tools 연동 (Claude via LiteLLM)
- [x] Mesop UI 기본 채팅 인터페이스
- [ ] 단위 테스트

### Phase 2 - 전략 확장
- [ ] DonchianChannelStrategy
- [ ] ATRTrendStrategy
- [ ] TurtleStrategy
- [ ] 다중 전략 동시 분석 (종합 신호)
- [ ] 백테스트 기능 (단순 수익률 시뮬레이션)

### Phase 3 - 고도화
- [ ] 종목 스크리닝 (조건 만족 종목 자동 탐색)
- [ ] 포트폴리오 수준 분석
- [ ] Orchestrator Agent 연동 준비 (A2A 프로토콜)

---

## 10. 확정 사항

- [x] LLM: `claude-opus-4-5` (Anthropic, Google ADK + LiteLLM 경유)
- [x] KR 주식 데이터: `FinanceDataReader` 단독 사용 (pykrx는 Python 3.14 미지원)
- [x] 기술적 지표 라이브러리: `ta` (pandas-ta는 Python 3.14 미지원)
- [x] Python 3.12+ 요구 (llvmlite 등 의존성 이슈로 3.11 제외)
- [ ] 차트를 Mesop 내에서 렌더링하는 구체적 방법 → Phase 2에서 구현 예정
- [ ] ADK Agent의 스트리밍 응답을 Mesop에서 처리하는 방식 → Phase 2에서 구현 예정
