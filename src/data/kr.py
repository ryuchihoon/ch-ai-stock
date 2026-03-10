from datetime import datetime, timedelta

import FinanceDataReader as fdr
import pandas as pd

from .base import DataSource, StockInfo

PERIOD_DAYS = {
    "3mo": 90,
    "6mo": 180,
    "1y": 365,
    "2y": 730,
    "5y": 1825,
}

# KRX 전체 종목 리스트 (검색용, 첫 호출 시 캐시)
_krx_listing: pd.DataFrame | None = None


def _get_krx_listing() -> pd.DataFrame:
    global _krx_listing
    if _krx_listing is None:
        _krx_listing = fdr.StockListing("KRX")
    return _krx_listing


class KRStockDataSource(DataSource):
    """한국 주식 데이터 소스 (FinanceDataReader 기반)"""

    def get_ohlcv(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        days = PERIOD_DAYS.get(period, 365)
        end = datetime.today()
        start = end - timedelta(days=days)

        df = fdr.DataReader(ticker, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if df.empty:
            raise ValueError(f"데이터 없음: {ticker}")

        df.columns = [c.lower() for c in df.columns]
        df.index.name = "date"
        df.index = pd.to_datetime(df.index).tz_localize(None)

        # FDR 컬럼명 정규화 (Change 등 불필요한 컬럼 제거)
        cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        return df[cols]

    def get_info(self, ticker: str) -> StockInfo:
        listing = _get_krx_listing()
        row = listing[listing["Code"] == ticker]
        name = row.iloc[0]["Name"] if not row.empty else ticker
        return StockInfo(
            ticker=ticker,
            name=name,
            market="KR",
            currency="KRW",
        )

    def search(self, query: str) -> list[StockInfo]:
        try:
            listing = _get_krx_listing()
        except Exception:
            return []

        query_lower = query.lower()
        matched = listing[
            listing["Name"].str.lower().str.contains(query_lower, na=False)
            | listing["Code"].str.contains(query, na=False)
        ]

        return [
            StockInfo(
                ticker=str(row["Code"]).zfill(6),
                name=row["Name"],
                market="KR",
                currency="KRW",
            )
            for _, row in matched.head(10).iterrows()
        ]
