"""데이터 레이어 단위 테스트 (yfinance / FinanceDataReader 모킹)"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.data.base import DataSource, StockInfo
from src.data.kr import KRStockDataSource
from src.data.us import USStockDataSource


# ---------------------------------------------------------------------------
# 헬퍼: 가짜 OHLCV DataFrame 생성
# ---------------------------------------------------------------------------

def _fake_ohlcv(n: int = 60, multiindex: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    data = {
        "Open": np.random.uniform(100, 200, n),
        "High": np.random.uniform(150, 220, n),
        "Low": np.random.uniform(80, 150, n),
        "Close": np.random.uniform(100, 200, n),
        "Volume": np.random.randint(1_000_000, 10_000_000, n),
    }
    if multiindex:
        # yfinance 최신 버전 MultiIndex 형태 모방
        cols = pd.MultiIndex.from_tuples([(c, "AAPL") for c in data.keys()])
        df = pd.DataFrame(data, index=dates)
        df.columns = cols
    else:
        df = pd.DataFrame(data, index=dates)
    df.index.name = "date"
    return df


def _fake_kr_ohlcv(n: int = 60) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame(
        {
            "Open": np.random.uniform(50_000, 80_000, n),
            "High": np.random.uniform(70_000, 90_000, n),
            "Low": np.random.uniform(40_000, 70_000, n),
            "Close": np.random.uniform(50_000, 80_000, n),
            "Volume": np.random.randint(1_000_000, 50_000_000, n),
            "Change": np.random.uniform(-0.05, 0.05, n),  # FDR 추가 컬럼
        },
        index=dates,
    )
    df.index.name = "date"
    return df


def _fake_krx_listing() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Code": ["005930", "000660", "035420"],
            "Name": ["삼성전자", "SK하이닉스", "NAVER"],
            "Market": ["KOSPI", "KOSPI", "KOSPI"],
        }
    )


# ---------------------------------------------------------------------------
# DataSource 추상 클래스
# ---------------------------------------------------------------------------

class TestDataSourceInterface:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            DataSource()  # type: ignore

    def test_stock_info_fields(self):
        info = StockInfo(ticker="AAPL", name="Apple Inc.", market="US", sector="Technology", currency="USD")
        assert info.ticker == "AAPL"
        assert info.market == "US"
        assert info.currency == "USD"


# ---------------------------------------------------------------------------
# USStockDataSource
# ---------------------------------------------------------------------------

class TestUSStockDataSource:
    @patch("src.data.us.yf.download")
    def test_get_ohlcv_columns(self, mock_download):
        """반환 DataFrame에 필수 컬럼이 있어야 한다."""
        mock_download.return_value = _fake_ohlcv(60)
        ds = USStockDataSource()
        df = ds.get_ohlcv("AAPL", "1y")
        assert set(df.columns) == {"open", "high", "low", "close", "volume"}

    @patch("src.data.us.yf.download")
    def test_get_ohlcv_multiindex_columns(self, mock_download):
        """yfinance MultiIndex 컬럼도 올바르게 처리해야 한다."""
        mock_download.return_value = _fake_ohlcv(60, multiindex=True)
        ds = USStockDataSource()
        df = ds.get_ohlcv("AAPL", "1y")
        assert set(df.columns) == {"open", "high", "low", "close", "volume"}

    @patch("src.data.us.yf.download")
    def test_get_ohlcv_index_is_datetime(self, mock_download):
        mock_download.return_value = _fake_ohlcv(60)
        ds = USStockDataSource()
        df = ds.get_ohlcv("AAPL")
        assert pd.api.types.is_datetime64_any_dtype(df.index)

    @patch("src.data.us.yf.download")
    def test_get_ohlcv_no_timezone(self, mock_download):
        """tz-naive index여야 한다 (전략 계산 시 tz 혼용 방지)."""
        mock_download.return_value = _fake_ohlcv(60)
        ds = USStockDataSource()
        df = ds.get_ohlcv("AAPL")
        assert df.index.tz is None

    @patch("src.data.us.yf.download")
    def test_get_ohlcv_empty_raises(self, mock_download):
        mock_download.return_value = pd.DataFrame()
        ds = USStockDataSource()
        with pytest.raises(ValueError, match="데이터 없음"):
            ds.get_ohlcv("INVALID")

    @patch("src.data.us.yf.Ticker")
    def test_get_info_returns_stock_info(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "currency": "USD",
        }
        mock_ticker_cls.return_value = mock_ticker
        ds = USStockDataSource()
        info = ds.get_info("AAPL")
        assert isinstance(info, StockInfo)
        assert info.ticker == "AAPL"
        assert info.market == "US"
        assert info.currency == "USD"

    @patch("src.data.us.yf.Ticker")
    def test_get_info_ticker_uppercased(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {"longName": "Apple Inc.", "currency": "USD"}
        mock_ticker_cls.return_value = mock_ticker
        ds = USStockDataSource()
        info = ds.get_info("aapl")  # 소문자 입력
        assert info.ticker == "AAPL"

    @patch("src.data.us.yf.Ticker")
    def test_search_success(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {"longName": "Apple Inc.", "currency": "USD"}
        mock_ticker_cls.return_value = mock_ticker
        ds = USStockDataSource()
        results = ds.search("AAPL")
        assert len(results) == 1
        assert results[0].ticker == "AAPL"

    @patch("src.data.us.yf.Ticker")
    def test_search_failure_returns_empty(self, mock_ticker_cls):
        mock_ticker_cls.side_effect = Exception("not found")
        ds = USStockDataSource()
        results = ds.search("NONEXISTENT_XYZ")
        assert results == []


# ---------------------------------------------------------------------------
# KRStockDataSource
# ---------------------------------------------------------------------------

class TestKRStockDataSource:
    @patch("src.data.kr.fdr.DataReader")
    @patch("src.data.kr._get_krx_listing")
    def test_get_ohlcv_columns(self, mock_listing, mock_reader):
        mock_reader.return_value = _fake_kr_ohlcv(60)
        ds = KRStockDataSource()
        df = ds.get_ohlcv("005930", "1y")
        assert set(df.columns) == {"open", "high", "low", "close", "volume"}

    @patch("src.data.kr.fdr.DataReader")
    @patch("src.data.kr._get_krx_listing")
    def test_get_ohlcv_extra_columns_removed(self, mock_listing, mock_reader):
        """FDR의 Change 같은 불필요한 컬럼이 제거되어야 한다."""
        mock_reader.return_value = _fake_kr_ohlcv(60)
        ds = KRStockDataSource()
        df = ds.get_ohlcv("005930")
        assert "change" not in df.columns

    @patch("src.data.kr.fdr.DataReader")
    @patch("src.data.kr._get_krx_listing")
    def test_get_ohlcv_index_is_datetime(self, mock_listing, mock_reader):
        mock_reader.return_value = _fake_kr_ohlcv(60)
        ds = KRStockDataSource()
        df = ds.get_ohlcv("005930")
        assert pd.api.types.is_datetime64_any_dtype(df.index)

    @patch("src.data.kr.fdr.DataReader")
    @patch("src.data.kr._get_krx_listing")
    def test_get_ohlcv_empty_raises(self, mock_listing, mock_reader):
        mock_reader.return_value = pd.DataFrame()
        ds = KRStockDataSource()
        with pytest.raises(ValueError, match="데이터 없음"):
            ds.get_ohlcv("999999")

    @patch("src.data.kr._get_krx_listing")
    def test_get_info_known_ticker(self, mock_listing):
        mock_listing.return_value = _fake_krx_listing()
        ds = KRStockDataSource()
        info = ds.get_info("005930")
        assert isinstance(info, StockInfo)
        assert info.name == "삼성전자"
        assert info.market == "KR"
        assert info.currency == "KRW"

    @patch("src.data.kr._get_krx_listing")
    def test_get_info_unknown_ticker_fallback(self, mock_listing):
        mock_listing.return_value = _fake_krx_listing()
        ds = KRStockDataSource()
        info = ds.get_info("999999")
        assert info.ticker == "999999"
        assert info.name == "999999"  # fallback to ticker

    @patch("src.data.kr._get_krx_listing")
    def test_search_by_name(self, mock_listing):
        mock_listing.return_value = _fake_krx_listing()
        ds = KRStockDataSource()
        results = ds.search("삼성")
        assert len(results) >= 1
        tickers = [r.ticker for r in results]
        assert "005930" in tickers

    @patch("src.data.kr._get_krx_listing")
    def test_search_by_code(self, mock_listing):
        mock_listing.return_value = _fake_krx_listing()
        ds = KRStockDataSource()
        results = ds.search("005930")
        assert any(r.ticker == "005930" for r in results)

    @patch("src.data.kr._get_krx_listing")
    def test_search_no_match_returns_empty(self, mock_listing):
        mock_listing.return_value = _fake_krx_listing()
        ds = KRStockDataSource()
        results = ds.search("ZZZZ_no_match_xyz")
        assert results == []
