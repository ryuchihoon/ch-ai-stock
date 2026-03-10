from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass
class StockInfo:
    ticker: str
    name: str
    market: str  # "US" | "KR"
    sector: str = ""
    currency: str = ""


class DataSource(ABC):
    """주식 데이터 소스 추상 클래스"""

    @abstractmethod
    def get_ohlcv(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """
        일봉 OHLCV 데이터를 반환한다.

        Args:
            ticker: 종목 코드
            period: "3mo" | "6mo" | "1y" | "2y" | "5y"

        Returns:
            columns: date(index), open, high, low, close, volume
        """

    @abstractmethod
    def get_info(self, ticker: str) -> StockInfo:
        """종목 기본 정보를 반환한다."""

    @abstractmethod
    def search(self, query: str) -> list[StockInfo]:
        """종목명 또는 티커로 검색한다."""
