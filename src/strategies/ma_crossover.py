import pandas as pd
import ta
import plotly.graph_objects as go

from .base import BaseStrategy, StrategyResult


class MACrossoverStrategy(BaseStrategy):
    """이동평균선 교차 전략 (골든크로스 / 데드크로스)"""

    @property
    def name(self) -> str:
        return "ma_crossover"

    @property
    def description(self) -> str:
        return (
            "단기 이동평균선이 장기 이동평균선을 상향 돌파하면 BUY(골든크로스), "
            "하향 돌파하면 SELL(데드크로스) 신호를 생성합니다."
        )

    @property
    def default_params(self) -> dict:
        return {"short_window": 20, "long_window": 60}

    def analyze(self, data: pd.DataFrame, params: dict) -> StrategyResult:
        p = self._merge_params(params)
        short_w = p["short_window"]
        long_w = p["long_window"]

        df = data.copy()
        df[f"sma_{short_w}"] = ta.trend.sma_indicator(df["close"], window=short_w)
        df[f"sma_{long_w}"] = ta.trend.sma_indicator(df["close"], window=long_w)
        df = df.dropna()

        if df.empty:
            raise ValueError("데이터가 너무 적어 분석할 수 없습니다.")

        short_col = f"sma_{short_w}"
        long_col = f"sma_{long_w}"

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        short_now = latest[short_col]
        long_now = latest[long_col]
        short_prev = prev[short_col]
        long_prev = prev[long_col]

        # 교차 감지
        crossed_up = short_prev <= long_prev and short_now > long_now
        crossed_down = short_prev >= long_prev and short_now < long_now

        # 추세 강도: 두 선의 간격 비율
        gap_ratio = abs(short_now - long_now) / long_now
        strength = min(gap_ratio * 20, 1.0)

        if crossed_up:
            signal = "BUY"
            reason = (
                f"골든크로스 발생: {short_w}일 SMA({short_now:.2f})가 "
                f"{long_w}일 SMA({long_now:.2f})를 상향 돌파했습니다."
            )
        elif crossed_down:
            signal = "SELL"
            reason = (
                f"데드크로스 발생: {short_w}일 SMA({short_now:.2f})가 "
                f"{long_w}일 SMA({long_now:.2f})를 하향 돌파했습니다."
            )
        elif short_now > long_now:
            signal = "BUY"
            reason = (
                f"상승 추세 유지 중: {short_w}일 SMA({short_now:.2f})가 "
                f"{long_w}일 SMA({long_now:.2f}) 위에 위치합니다."
            )
        else:
            signal = "SELL"
            reason = (
                f"하락 추세 유지 중: {short_w}일 SMA({short_now:.2f})가 "
                f"{long_w}일 SMA({long_now:.2f}) 아래에 위치합니다."
            )

        chart_data = self._build_chart(df, short_col, long_col, short_w, long_w)

        return StrategyResult(
            ticker=params.get("ticker", ""),
            strategy_name=self.name,
            signal=signal,
            strength=strength,
            reason=reason,
            chart_data=chart_data,
            indicators={
                f"sma_{short_w}": round(short_now, 2),
                f"sma_{long_w}": round(long_now, 2),
                "golden_cross": crossed_up,
                "dead_cross": crossed_down,
            },
        )

    def _build_chart(
        self, df: pd.DataFrame, short_col: str, long_col: str, short_w: int, long_w: int
    ) -> dict:
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            name="OHLCV",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df[short_col],
            name=f"SMA {short_w}",
            line=dict(color="#FF9800", width=1.5),
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df[long_col],
            name=f"SMA {long_w}",
            line=dict(color="#2196F3", width=1.5),
        ))

        fig.update_layout(
            title=f"MA Crossover ({short_w}/{long_w})",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=500,
            margin=dict(l=40, r=40, t=50, b=40),
        )
        return fig.to_dict()
