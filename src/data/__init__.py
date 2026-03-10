from .base import DataSource, StockInfo
from .kr import KRStockDataSource
from .us import USStockDataSource


def get_datasource(ticker: str) -> DataSource:
    """ticker가 숫자 6자리이면 KR, 아니면 US로 판별."""
    if ticker.isdigit() and len(ticker) == 6:
        return KRStockDataSource()
    return USStockDataSource()


__all__ = ["DataSource", "StockInfo", "USStockDataSource", "KRStockDataSource", "get_datasource"]
