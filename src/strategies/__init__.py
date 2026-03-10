from .base import BaseStrategy, StrategyResult
from .ma_crossover import MACrossoverStrategy
from .registry import StrategyRegistry
from .rsi import RSIStrategy

# 전략 등록
StrategyRegistry.register(MACrossoverStrategy())
StrategyRegistry.register(RSIStrategy())

__all__ = [
    "BaseStrategy",
    "StrategyResult",
    "StrategyRegistry",
    "MACrossoverStrategy",
    "RSIStrategy",
]
