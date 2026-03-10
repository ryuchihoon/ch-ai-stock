"""Agent Tools 단위 테스트 (데이터 소스 모킹)"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from src.agent.tools.analysis import get_indicators, analyze_trend, list_strategies, _series_to_snapshot
from src.agent.tools.stock import compare_stocks, get_stock_data, search_stock
from src.data.base import StockInfo


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 1, n).cumsum()
    close = np.maximum(close, 1.0)
    df = pd.DataFrame(
        {
            "open": close * (1 + rng.normal(0, 0.005, n)),
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, n),
        },
        index=dates,
    )
    df.index.name = "date"
    return df


def _fake_stock_info(ticker: str = "AAPL", market: str = "US") -> StockInfo:
    return StockInfo(
        ticker=ticker,
        name="Apple Inc." if market == "US" else "삼성전자",
        market=market,
        currency="USD" if market == "US" else "KRW",
    )


def _patch_datasource(ticker: str = "AAPL", market: str = "US"):
    """get_datasource 패치를 반환하는 context manager용 설정"""
    mock_ds = MagicMock()
    mock_ds.get_ohlcv.return_value = _make_ohlcv()
    mock_ds.get_info.return_value = _fake_stock_info(ticker, market)
    return mock_ds


# ---------------------------------------------------------------------------
# get_stock_data
# ---------------------------------------------------------------------------

class TestGetStockData:
    @patch("src.agent.tools.stock.get_datasource")
    def test_returns_dict_with_required_keys(self, mock_get_ds):
        mock_get_ds.return_value = _patch_datasource()
        result = get_stock_data("AAPL")
        assert isinstance(result, dict)
        for key in ("ticker", "name", "market", "currency", "period", "total_days", "latest", "stats"):
            assert key in result, f"키 없음: {key}"

    @patch("src.agent.tools.stock.get_datasource")
    def test_latest_has_ohlcv(self, mock_get_ds):
        mock_get_ds.return_value = _patch_datasource()
        result = get_stock_data("AAPL")
        latest = result["latest"]
        for key in ("date", "open", "high", "low", "close", "volume"):
            assert key in latest

    @patch("src.agent.tools.stock.get_datasource")
    def test_stats_has_required_keys(self, mock_get_ds):
        mock_get_ds.return_value = _patch_datasource()
        result = get_stock_data("AAPL")
        for key in ("period_high", "period_low", "avg_close", "period_return_pct", "avg_volume"):
            assert key in result["stats"]

    @patch("src.agent.tools.stock.get_datasource")
    def test_values_are_python_native(self, mock_get_ds):
        mock_get_ds.return_value = _patch_datasource()
        result = get_stock_data("AAPL")
        assert isinstance(result["latest"]["close"], float)
        assert isinstance(result["latest"]["volume"], int)
        assert isinstance(result["stats"]["period_return_pct"], float)

    @patch("src.agent.tools.stock.get_datasource")
    def test_error_returns_error_dict(self, mock_get_ds):
        mock_get_ds.side_effect = Exception("네트워크 오류")
        result = get_stock_data("INVALID")
        assert "error" in result
        assert result["ticker"] == "INVALID"


# ---------------------------------------------------------------------------
# search_stock
# ---------------------------------------------------------------------------

class TestSearchStock:
    @patch("src.data.us.USStockDataSource")
    def test_us_market_search(self, mock_us_cls):
        mock_us = MagicMock()
        mock_us.search.return_value = [_fake_stock_info("AAPL", "US")]
        mock_us_cls.return_value = mock_us

        results = search_stock("AAPL", market="us")
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["ticker"] == "AAPL"

    @patch("src.data.kr.KRStockDataSource")
    def test_kr_market_search(self, mock_kr_cls):
        mock_kr = MagicMock()
        mock_kr.search.return_value = [_fake_stock_info("005930", "KR")]
        mock_kr_cls.return_value = mock_kr

        results = search_stock("삼성", market="kr")
        assert isinstance(results, list)
        assert any(r["market"] == "KR" for r in results)

    @patch("src.data.us.USStockDataSource")
    @patch("src.data.kr.KRStockDataSource")
    def test_all_market_search(self, mock_kr_cls, mock_us_cls):
        mock_us = MagicMock()
        mock_us.search.return_value = [_fake_stock_info("AAPL", "US")]
        mock_us_cls.return_value = mock_us

        mock_kr = MagicMock()
        mock_kr.search.return_value = [_fake_stock_info("005930", "KR")]
        mock_kr_cls.return_value = mock_kr

        results = search_stock("test", market="all")
        markets = {r["market"] for r in results}
        assert "US" in markets
        assert "KR" in markets

    @patch("src.data.us.USStockDataSource")
    def test_error_returns_error_list(self, mock_us_cls):
        mock_us_cls.side_effect = Exception("오류")
        results = search_stock("AAPL", market="us")
        assert isinstance(results, list)
        assert "error" in results[0]


# ---------------------------------------------------------------------------
# compare_stocks
# ---------------------------------------------------------------------------

class TestCompareStocks:
    @patch("src.agent.tools.stock.get_datasource")
    def test_returns_dict_with_results(self, mock_get_ds):
        mock_get_ds.return_value = _patch_datasource()
        result = compare_stocks(["AAPL", "MSFT"], metric="performance")
        assert "metric" in result
        assert "period" in result
        assert "results" in result
        assert len(result["results"]) == 2

    @patch("src.agent.tools.stock.get_datasource")
    def test_performance_sorted_descending(self, mock_get_ds):
        mock_get_ds.return_value = _patch_datasource()
        result = compare_stocks(["AAPL", "MSFT"], metric="performance")
        returns = [r.get("period_return_pct", float("-inf")) for r in result["results"] if "error" not in r]
        assert returns == sorted(returns, reverse=True)

    @patch("src.agent.tools.stock.get_datasource")
    def test_volatility_sorted_ascending(self, mock_get_ds):
        mock_get_ds.return_value = _patch_datasource()
        result = compare_stocks(["AAPL", "MSFT"], metric="volatility")
        vols = [r.get("annualized_volatility_pct", float("inf")) for r in result["results"] if "error" not in r]
        assert vols == sorted(vols)

    @patch("src.agent.tools.stock.get_datasource")
    def test_max_5_tickers(self, mock_get_ds):
        mock_get_ds.return_value = _patch_datasource()
        tickers = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
        result = compare_stocks(tickers)
        assert len(result["results"]) <= 5


# ---------------------------------------------------------------------------
# get_indicators
# ---------------------------------------------------------------------------

class TestGetIndicators:
    @patch("src.agent.tools.analysis.get_datasource")
    def test_default_indicators_returned(self, mock_get_ds):
        mock_ds = MagicMock()
        mock_ds.get_ohlcv.return_value = _make_ohlcv()
        mock_get_ds.return_value = mock_ds

        result = get_indicators("AAPL")
        assert "indicators" in result
        for key in ("sma_20", "sma_60", "rsi_14"):
            assert key in result["indicators"]

    @patch("src.agent.tools.analysis.get_datasource")
    def test_sma_snapshot_structure(self, mock_get_ds):
        mock_ds = MagicMock()
        mock_ds.get_ohlcv.return_value = _make_ohlcv()
        mock_get_ds.return_value = mock_ds

        result = get_indicators("AAPL", indicators=["sma_20"])
        snap = result["indicators"]["sma_20"]
        assert "latest" in snap
        assert "recent" in snap
        assert isinstance(snap["latest"], float)
        assert isinstance(snap["recent"], list)

    @patch("src.agent.tools.analysis.get_datasource")
    def test_macd_returns_three_components(self, mock_get_ds):
        mock_ds = MagicMock()
        mock_ds.get_ohlcv.return_value = _make_ohlcv()
        mock_get_ds.return_value = mock_ds

        result = get_indicators("AAPL", indicators=["macd"])
        for key in ("macd_line", "macd_signal", "macd_hist"):
            assert key in result["indicators"]

    @patch("src.agent.tools.analysis.get_datasource")
    def test_bb_returns_three_bands(self, mock_get_ds):
        mock_ds = MagicMock()
        mock_ds.get_ohlcv.return_value = _make_ohlcv()
        mock_get_ds.return_value = mock_ds

        result = get_indicators("AAPL", indicators=["bb_20"])
        for key in ("bb_upper", "bb_mid", "bb_lower"):
            assert key in result["indicators"]

    @patch("src.agent.tools.analysis.get_datasource")
    def test_error_returns_error_dict(self, mock_get_ds):
        mock_get_ds.side_effect = Exception("오류")
        result = get_indicators("INVALID")
        assert "error" in result


# ---------------------------------------------------------------------------
# analyze_trend
# ---------------------------------------------------------------------------

class TestAnalyzeTrend:
    @patch("src.agent.tools.analysis.get_datasource")
    def test_ma_crossover_signal_structure(self, mock_get_ds):
        mock_ds = MagicMock()
        mock_ds.get_ohlcv.return_value = _make_ohlcv()
        mock_get_ds.return_value = mock_ds

        result = analyze_trend("AAPL", "ma_crossover")
        for key in ("ticker", "strategy", "signal", "strength", "reason", "indicators"):
            assert key in result

    @patch("src.agent.tools.analysis.get_datasource")
    def test_rsi_signal_structure(self, mock_get_ds):
        mock_ds = MagicMock()
        mock_ds.get_ohlcv.return_value = _make_ohlcv()
        mock_get_ds.return_value = mock_ds

        result = analyze_trend("AAPL", "rsi")
        assert result["signal"] in ("BUY", "SELL", "HOLD")
        assert 0.0 <= result["strength"] <= 1.0

    @patch("src.agent.tools.analysis.get_datasource")
    def test_chart_data_not_in_result(self, mock_get_ds):
        """chart_data는 LLM에 전달하지 않으므로 결과에 없어야 한다."""
        mock_ds = MagicMock()
        mock_ds.get_ohlcv.return_value = _make_ohlcv()
        mock_get_ds.return_value = mock_ds

        result = analyze_trend("AAPL", "ma_crossover")
        assert "chart_data" not in result

    @patch("src.agent.tools.analysis.get_datasource")
    def test_unknown_strategy_returns_error(self, mock_get_ds):
        mock_ds = MagicMock()
        mock_ds.get_ohlcv.return_value = _make_ohlcv()
        mock_get_ds.return_value = mock_ds

        result = analyze_trend("AAPL", "nonexistent_strategy")
        assert "error" in result

    @patch("src.agent.tools.analysis.get_datasource")
    def test_custom_params_passed(self, mock_get_ds):
        mock_ds = MagicMock()
        mock_ds.get_ohlcv.return_value = _make_ohlcv()
        mock_get_ds.return_value = mock_ds

        result = analyze_trend("AAPL", "ma_crossover", params={"short_window": 10, "long_window": 30})
        assert "error" not in result
        assert result["signal"] in ("BUY", "SELL", "HOLD")


# ---------------------------------------------------------------------------
# list_strategies
# ---------------------------------------------------------------------------

class TestListStrategies:
    def test_returns_list(self):
        result = list_strategies()
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_each_has_required_keys(self):
        for item in list_strategies():
            assert "name" in item
            assert "description" in item
            assert "params" in item


# ---------------------------------------------------------------------------
# _series_to_snapshot (내부 헬퍼)
# ---------------------------------------------------------------------------

class TestSeriesToSnapshot:
    def test_normal_series(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        snap = _series_to_snapshot(s)
        assert snap["latest"] == pytest.approx(5.0)
        assert len(snap["recent"]) <= 20

    def test_empty_series(self):
        snap = _series_to_snapshot(pd.Series([], dtype=float))
        assert snap["latest"] is None
        assert snap["recent"] == []

    def test_recent_max_20(self):
        s = pd.Series(range(100), dtype=float)
        snap = _series_to_snapshot(s)
        assert len(snap["recent"]) == 20

    def test_values_are_float(self):
        s = pd.Series([1.0, 2.0, 3.0])
        snap = _series_to_snapshot(s)
        assert isinstance(snap["latest"], float)
        for v in snap["recent"]:
            assert isinstance(v, float)
