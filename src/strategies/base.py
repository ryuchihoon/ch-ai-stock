from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd


@dataclass
class StrategyResult:
    ticker: str
    strategy_name: str
    signal: Literal["BUY", "SELL", "HOLD"]
    strength: float          # 0.0 ~ 1.0
    reason: str              # Agent가 사용자에게 설명할 근거
    chart_data: dict         # Plotly figure dict (json-serializable)
    indicators: dict = field(default_factory=dict)  # 계산된 지표값 스냅샷


class BaseStrategy(ABC):
    """모든 전략의 추상 기반 클래스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """전략 식별자 (registry key로 사용)"""

    @property
    @abstractmethod
    def description(self) -> str:
        """전략 설명 (Agent가 사용자에게 안내할 때 사용)"""

    @property
    @abstractmethod
    def default_params(self) -> dict:
        """기본 파라미터"""

    @abstractmethod
    def analyze(self, data: pd.DataFrame, params: dict) -> StrategyResult:
        """
        전략 분석을 수행한다.

        Args:
            data: OHLCV DataFrame (date index, open/high/low/close/volume columns)
            params: 전략 파라미터 (default_params에 없는 키는 무시)

        Returns:
            StrategyResult
        """

    def _merge_params(self, params: dict) -> dict:
        """기본 파라미터에 사용자 파라미터를 병합한다."""
        merged = self.default_params.copy()
        merged.update(params)
        return merged
