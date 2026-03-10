from .base import BaseStrategy


class StrategyRegistry:
    """전략 플러그인 레지스트리. 전략 추가 시 register()만 호출하면 된다."""

    _strategies: dict[str, BaseStrategy] = {}

    @classmethod
    def register(cls, strategy: BaseStrategy) -> None:
        cls._strategies[strategy.name] = strategy

    @classmethod
    def get(cls, name: str) -> BaseStrategy:
        if name not in cls._strategies:
            available = list(cls._strategies.keys())
            raise KeyError(f"전략 '{name}'을 찾을 수 없습니다. 사용 가능: {available}")
        return cls._strategies[name]

    @classmethod
    def list_all(cls) -> list[dict]:
        return [
            {"name": s.name, "description": s.description, "params": s.default_params}
            for s in cls._strategies.values()
        ]
