import yfinance as yf
import pandas as pd

from .base import DataSource, StockInfo


class USStockDataSource(DataSource):
    """미국 주식 데이터 소스 (yfinance 기반)"""

    def get_ohlcv(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        ticker = ticker.upper()
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError(f"데이터 없음: {ticker}")

        # yfinance 최신 버전은 MultiIndex 컬럼 반환 → 첫 번째 레벨만 사용
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]
        df.index.name = "date"
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df[["open", "high", "low", "close", "volume"]]

    def get_info(self, ticker: str) -> StockInfo:
        ticker = ticker.upper()
        info = yf.Ticker(ticker).info
        return StockInfo(
            ticker=ticker,
            name=info.get("longName", ticker),
            market="US",
            sector=info.get("sector", ""),
            currency=info.get("currency", "USD"),
        )

    def search(self, query: str) -> list[StockInfo]:
        # yfinance는 검색 API를 직접 제공하지 않으므로 ticker 직접 조회 시도
        try:
            info = self.get_info(query.upper())
            return [info]
        except Exception:
            return []
