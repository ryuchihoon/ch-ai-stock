"""전략 엔진 단위 테스트 (네트워크 없음, 합성 데이터 사용)"""

import numpy as np
import pandas as pd
import pytest

from src.strategies.base import StrategyResult
from src.strategies.ma_crossover import MACrossoverStrategy
from src.strategies.registry import StrategyRegistry
from src.strategies.rsi import RSIStrategy


# ---------------------------------------------------------------------------
# 헬퍼: 합성 OHLCV DataFrame 생성
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 120, trend: str = "up") -> pd.DataFrame:
    """테스트용 합성 일봉 데이터 생성.

    trend: "up" (상승), "down" (하락), "sideways" (횡보)
    """
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    rng = np.random.default_rng(42)

    if trend == "up":
        close = 100 + np.arange(n) * 0.5 + rng.normal(0, 1, n).cumsum()
    elif trend == "down":
        close = 200 - np.arange(n) * 0.5 + rng.normal(0, 1, n).cumsum()
    else:
        close = 100 + rng.normal(0, 1, n).cumsum()

    close = np.maximum(close, 1.0)
    high = close * (1 + rng.uniform(0, 0.02, n))
    low = close * (1 - rng.uniform(0, 0.02, n))
    open_ = close * (1 + rng.normal(0, 0.01, n))

    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": rng.integers(1_000_000, 10_000_000, n)},
        index=dates,
    )
    df.index.name = "date"
    return df


# ---------------------------------------------------------------------------
# StrategyRegistry
# ---------------------------------------------------------------------------

class TestStrategyRegistry:
    def test_registered_strategies(self):
        """ma_crossover, rsi 두 전략이 등록되어 있어야 한다."""
        strategies = StrategyRegistry.list_all()
        names = [s["name"] for s in strategies]
        assert "ma_crossover" in names
        assert "rsi" in names

    def test_get_existing(self):
        strat = StrategyRegistry.get("ma_crossover")
        assert strat is not None
        assert strat.name == "ma_crossover"

    def test_get_missing_raises(self):
        with pytest.raises(KeyError):
            StrategyRegistry.get("nonexistent_strategy")

    def test_list_all_has_required_keys(self):
        for item in StrategyRegistry.list_all():
            assert "name" in item
            assert "description" in item
            assert "params" in item


# ---------------------------------------------------------------------------
# MACrossoverStrategy
# ---------------------------------------------------------------------------

class TestMACrossoverStrategy:
    def setup_method(self):
        self.strategy = MACrossoverStrategy()

    def test_name_and_description(self):
        assert self.strategy.name == "ma_crossover"
        assert len(self.strategy.description) > 10

    def test_default_params(self):
        p = self.strategy.default_params
        assert p["short_window"] == 20
        assert p["long_window"] == 60

    def test_analyze_returns_strategy_result(self):
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        assert isinstance(result, StrategyResult)

    def test_signal_is_valid(self):
        for trend in ("up", "down", "sideways"):
            df = _make_ohlcv(120, trend=trend)
            result = self.strategy.analyze(df, {})
            assert result.signal in ("BUY", "SELL", "HOLD")

    def test_strength_in_range(self):
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        assert 0.0 <= result.strength <= 1.0

    def test_reason_is_string(self):
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0

    def test_indicators_are_python_native_types(self):
        """numpy 타입이 포함되면 pydantic 직렬화 에러 발생 — Python 네이티브여야 한다."""
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        for key, val in result.indicators.items():
            assert not isinstance(val, (np.bool_, np.integer, np.floating)), (
                f"indicators['{key}'] = {val!r} is numpy type {type(val)}"
            )
            assert isinstance(val, (bool, int, float)), (
                f"indicators['{key}'] = {val!r} should be Python native"
            )

    def test_chart_data_is_dict(self):
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        assert isinstance(result.chart_data, dict)
        assert "data" in result.chart_data  # Plotly figure dict

    def test_custom_params(self):
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {"short_window": 10, "long_window": 30})
        assert result.signal in ("BUY", "SELL", "HOLD")

    def test_insufficient_data_raises(self):
        df = _make_ohlcv(10)  # 10행은 long_window=60 SMA 계산 불가
        with pytest.raises(ValueError, match="데이터가 너무 적어"):
            self.strategy.analyze(df, {})

    def test_ticker_passed_to_result(self):
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {"ticker": "AAPL"})
        assert result.ticker == "AAPL"


# ---------------------------------------------------------------------------
# RSIStrategy
# ---------------------------------------------------------------------------

class TestRSIStrategy:
    def setup_method(self):
        self.strategy = RSIStrategy()

    def test_name_and_description(self):
        assert self.strategy.name == "rsi"
        assert len(self.strategy.description) > 10

    def test_default_params(self):
        p = self.strategy.default_params
        assert p["rsi_period"] == 14
        assert p["overbought"] == 70
        assert p["oversold"] == 30
        assert p["trend_ma"] == 60

    def test_analyze_returns_strategy_result(self):
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        assert isinstance(result, StrategyResult)

    def test_signal_is_valid(self):
        for trend in ("up", "down", "sideways"):
            df = _make_ohlcv(120, trend=trend)
            result = self.strategy.analyze(df, {})
            assert result.signal in ("BUY", "SELL", "HOLD")

    def test_strength_in_range(self):
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        assert 0.0 <= result.strength <= 1.0

    def test_indicators_are_python_native_types(self):
        """numpy 타입이 포함되면 pydantic 직렬화 에러 발생."""
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        for key, val in result.indicators.items():
            assert not isinstance(val, (np.bool_, np.integer, np.floating)), (
                f"indicators['{key}'] = {val!r} is numpy type {type(val)}"
            )

    def test_indicators_has_required_keys(self):
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        assert "rsi" in result.indicators
        assert "uptrend" in result.indicators
        assert isinstance(result.indicators["uptrend"], bool)

    def test_chart_data_has_two_subplots(self):
        """RSI 전략 차트는 캔들 + RSI 두 개의 subplot을 가져야 한다."""
        df = _make_ohlcv(120)
        result = self.strategy.analyze(df, {})
        assert isinstance(result.chart_data, dict)
        # Plotly subplots figure는 layout.grid 또는 여러 yaxis를 가짐
        assert "layout" in result.chart_data

    def test_oversold_signal_on_declining_rsi(self):
        """과매도 구간 데이터에서 BUY 또는 HOLD 신호가 나와야 한다."""
        df = _make_ohlcv(120, trend="down")
        result = self.strategy.analyze(df, {})
        assert result.signal in ("BUY", "HOLD")  # 하락장에서 과매도 가능

    def test_insufficient_data_raises(self):
        df = _make_ohlcv(5)
        with pytest.raises(ValueError, match="데이터가 너무 적어"):
            self.strategy.analyze(df, {})
