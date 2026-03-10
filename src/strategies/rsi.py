import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .base import BaseStrategy, StrategyResult


class RSIStrategy(BaseStrategy):
    """RSI 기반 추세 전략 (과매수/과매도 + 추세 필터)"""

    @property
    def name(self) -> str:
        return "rsi"

    @property
    def description(self) -> str:
        return (
            "RSI가 과매도 구간(기본 30)에서 반등 시 BUY, 과매수 구간(기본 70)에서 하락 시 SELL. "
            "장기 이동평균선 방향을 추세 필터로 사용합니다."
        )

    @property
    def default_params(self) -> dict:
        return {
            "rsi_period": 14,
            "overbought": 70,
            "oversold": 30,
            "trend_ma": 60,
        }

    def analyze(self, data: pd.DataFrame, params: dict) -> StrategyResult:
        p = self._merge_params(params)
        rsi_period = p["rsi_period"]
        overbought = p["overbought"]
        oversold = p["oversold"]
        trend_ma = p["trend_ma"]

        df = data.copy()
        df["rsi"] = ta.momentum.rsi(df["close"], window=rsi_period)
        df["trend_sma"] = ta.trend.sma_indicator(df["close"], window=trend_ma)
        df = df.dropna()

        if df.empty:
            raise ValueError("데이터가 너무 적어 분석할 수 없습니다.")

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        rsi_now = latest["rsi"]
        rsi_prev = prev["rsi"]
        price = latest["close"]
        sma = latest["trend_sma"]
        uptrend = price > sma

        # 신호 판단
        rsi_rising = rsi_now > rsi_prev
        rsi_falling = rsi_now < rsi_prev

        if rsi_prev <= oversold and rsi_now > oversold:
            signal = "BUY"
            strength = min((rsi_now - oversold) / 20, 1.0)
            reason = (
                f"RSI({rsi_now:.1f})가 과매도 구간({oversold})을 상향 돌파했습니다. "
                f"{'상승 추세(SMA 위)에서 ' if uptrend else ''}반등 신호입니다."
            )
        elif rsi_prev >= overbought and rsi_now < overbought:
            signal = "SELL"
            strength = min((overbought - rsi_now) / 20, 1.0)
            reason = (
                f"RSI({rsi_now:.1f})가 과매수 구간({overbought})을 하향 돌파했습니다. "
                f"{'하락 추세(SMA 아래)에서 ' if not uptrend else ''}조정 신호입니다."
            )
        elif rsi_now < oversold:
            signal = "BUY"
            strength = min((oversold - rsi_now) / oversold, 1.0) * 0.7
            reason = (
                f"RSI({rsi_now:.1f})가 과매도 구간({oversold}) 내에 있습니다. "
                "돌파 시 매수 신호 발생 가능합니다."
            )
        elif rsi_now > overbought:
            signal = "SELL"
            strength = min((rsi_now - overbought) / (100 - overbought), 1.0) * 0.7
            reason = (
                f"RSI({rsi_now:.1f})가 과매수 구간({overbought}) 내에 있습니다. "
                "이탈 시 매도 신호 발생 가능합니다."
            )
        else:
            signal = "HOLD"
            strength = 0.0
            trend_desc = "상승" if uptrend else "하락"
            reason = (
                f"RSI({rsi_now:.1f})가 중립 구간({oversold}~{overbought})에 있습니다. "
                f"현재 {trend_desc} 추세 ({trend_ma}일 SMA 기준)."
            )

        chart_data = self._build_chart(df, overbought, oversold, trend_ma, rsi_period)

        return StrategyResult(
            ticker=params.get("ticker", ""),
            strategy_name=self.name,
            signal=signal,
            strength=strength,
            reason=reason,
            chart_data=chart_data,
            indicators={
                "rsi": round(float(rsi_now), 2),
                "rsi_prev": round(float(rsi_prev), 2),
                f"sma_{trend_ma}": round(float(sma), 2),
                "uptrend": bool(uptrend),
                "overbought": overbought,
                "oversold": oversold,
            },
        )

    def _build_chart(
        self, df: pd.DataFrame, overbought: int, oversold: int, trend_ma: int, rsi_period: int
    ) -> dict:
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.03,
        )

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            name="OHLCV",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df.index, y=df["trend_sma"],
            name=f"SMA {trend_ma}",
            line=dict(color="#2196F3", width=1.5),
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df.index, y=df["rsi"],
            name=f"RSI({rsi_period})",
            line=dict(color="#FF9800", width=1.5),
        ), row=2, col=1)

        # 과매수/과매도 기준선
        for level, color in [(overbought, "rgba(239,83,80,0.3)"), (oversold, "rgba(38,166,154,0.3)")]:
            fig.add_hline(y=level, line_dash="dash", line_color=color, row=2, col=1)

        fig.update_layout(
            title=f"RSI({rsi_period}) Strategy",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=600,
            margin=dict(l=40, r=40, t=50, b=40),
        )
        return fig.to_dict()
