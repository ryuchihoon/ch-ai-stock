import pandas as pd
import ta

from src.data import get_datasource
from src.strategies import StrategyRegistry


def get_indicators(
    ticker: str,
    period: str = "1y",
    indicators: list[str] | None = None,
) -> dict:
    """
    기술적 지표를 계산하여 반환합니다.

    Args:
        ticker: 종목 코드
        period: 조회 기간. "3mo", "6mo", "1y", "2y", "5y" 중 하나 (기본값: "1y")
        indicators: 계산할 지표 목록. 지원 지표:
            "sma_N" (N일 단순이동평균), "ema_N" (N일 지수이동평균),
            "rsi_N" (N일 RSI), "macd" (MACD), "bb_N" (N일 볼린저밴드),
            "atr_N" (N일 ATR), "volume_ma_N" (N일 거래량 이동평균)
            기본값: ["sma_20", "sma_60", "rsi_14"]

    Returns:
        각 지표의 최근 값과 최근 20일 시계열 데이터
    """
    if indicators is None:
        indicators = ["sma_20", "sma_60", "rsi_14"]

    try:
        ds = get_datasource(ticker)
        df = ds.get_ohlcv(ticker, period)
        result = {"ticker": ticker, "period": period, "indicators": {}}

        for ind in indicators:
            parts = ind.split("_")
            kind = parts[0]
            n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 14

            if kind == "sma":
                series = ta.trend.sma_indicator(df["close"], window=n)
                result["indicators"][ind] = _series_to_snapshot(series)
            elif kind == "ema":
                series = ta.trend.ema_indicator(df["close"], window=n)
                result["indicators"][ind] = _series_to_snapshot(series)
            elif kind == "rsi":
                series = ta.momentum.rsi(df["close"], window=n)
                result["indicators"][ind] = _series_to_snapshot(series)
            elif kind == "macd":
                result["indicators"]["macd_line"] = _series_to_snapshot(
                    ta.trend.macd(df["close"])
                )
                result["indicators"]["macd_signal"] = _series_to_snapshot(
                    ta.trend.macd_signal(df["close"])
                )
                result["indicators"]["macd_hist"] = _series_to_snapshot(
                    ta.trend.macd_diff(df["close"])
                )
            elif kind == "bb":
                bb = ta.volatility.BollingerBands(df["close"], window=n)
                result["indicators"]["bb_upper"] = _series_to_snapshot(bb.bollinger_hband())
                result["indicators"]["bb_mid"] = _series_to_snapshot(bb.bollinger_mavg())
                result["indicators"]["bb_lower"] = _series_to_snapshot(bb.bollinger_lband())
            elif kind == "atr":
                series = ta.volatility.average_true_range(
                    df["high"], df["low"], df["close"], window=n
                )
                result["indicators"][ind] = _series_to_snapshot(series)
            elif kind == "volume":
                if len(parts) > 1 and parts[1] == "ma":
                    n2 = int(parts[2]) if len(parts) > 2 else 20
                    series = ta.trend.sma_indicator(df["volume"], window=n2)
                    result["indicators"][ind] = _series_to_snapshot(series)

        return result
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


def analyze_trend(
    ticker: str,
    strategy: str,
    period: str = "1y",
    params: dict | None = None,
) -> dict:
    """
    지정한 Trend Following 전략으로 종목을 분석하고 매매 신호를 반환합니다.

    Args:
        ticker: 종목 코드
        strategy: 전략 이름. 사용 가능한 전략은 list_strategies()로 확인
            현재 지원: "ma_crossover" (이동평균 교차), "rsi" (RSI 전략)
        period: 분석 기간. "3mo", "6mo", "1y", "2y", "5y" 중 하나 (기본값: "1y")
        params: 전략 파라미터 (선택사항).
            ma_crossover: {"short_window": 20, "long_window": 60}
            rsi: {"rsi_period": 14, "overbought": 70, "oversold": 30, "trend_ma": 60}

    Returns:
        signal (BUY/SELL/HOLD), strength (0~1), reason (근거 설명), indicators
    """
    if params is None:
        params = {}
    params["ticker"] = ticker

    try:
        strat = StrategyRegistry.get(strategy)
        ds = get_datasource(ticker)
        df = ds.get_ohlcv(ticker, period)

        result = strat.analyze(df, params)

        return {
            "ticker": ticker,
            "strategy": strategy,
            "signal": result.signal,
            "strength": round(result.strength, 3),
            "reason": result.reason,
            "indicators": result.indicators,
            # chart_data는 Mesop UI에서 직접 사용하므로 여기서는 제외
            # (LLM에 넘기기엔 너무 큰 데이터)
        }
    except KeyError as e:
        return {"error": str(e), "ticker": ticker, "strategy": strategy}
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "strategy": strategy}


def list_strategies() -> list[dict]:
    """
    사용 가능한 Trend Following 전략 목록을 반환합니다.

    Returns:
        각 전략의 name, description, default_params
    """
    return StrategyRegistry.list_all()


# --- 내부 헬퍼 ---

def _series_to_snapshot(series: pd.Series) -> dict:
    """시계열을 최근값 + 최근 20일 리스트로 변환"""
    series = series.dropna()
    if series.empty:
        return {"latest": None, "recent": []}
    recent = series.tail(20)
    return {
        "latest": round(float(series.iloc[-1]), 4),
        "recent": [round(float(v), 4) for v in recent],
    }
