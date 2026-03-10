from google.adk.agents import Agent
from google.adk.models import LiteLlm

from .tools import (
    analyze_trend,
    compare_stocks,
    get_indicators,
    get_stock_data,
    list_strategies,
    search_stock,
)

SYSTEM_PROMPT = """당신은 주식 기술적 분석 전문가 AI입니다.

## 역할
- 미국 주식(티커 심볼: AAPL, MSFT 등)과 한국 주식(6자리 코드: 005930, 000660 등)을 분석합니다.
- Trend Following을 비롯한 기술적 분석 전략으로 매매 신호를 제공합니다.
- 분석 결과는 항상 근거와 함께 설명합니다.

## 중요 안내
- 제공하는 모든 분석은 **참고용**이며 투자 권유가 아닙니다.
- 투자 결정은 사용자 본인의 판단과 책임 하에 이루어져야 합니다.

## 도구 사용 지침
1. 종목 분석 요청 시: get_stock_data → analyze_trend 순서로 호출
2. 지표 확인 요청 시: get_indicators 사용
3. 종목 이름만 알고 코드를 모를 때: search_stock으로 먼저 검색
4. 여러 종목 비교 요청 시: compare_stocks 사용
5. 어떤 전략이 있는지 물어볼 때: list_strategies 사용

## 응답 형식
- 분석 결과는 **신호(BUY/SELL/HOLD)**, **근거**, **주요 지표값** 순으로 설명합니다.
- 한국어로 응답합니다.
- 숫자는 단위와 함께 명확하게 표시합니다.
"""


def create_agent() -> Agent:
    """CH AI Stock ADK Agent를 생성한다."""
    return Agent(
        model=LiteLlm(model="anthropic/claude-opus-4-5"),
        name="ch_ai_stock_agent",
        description="미국/한국 주식 기술적 분석 및 Trend Following 전략 신호 제공",
        instruction=SYSTEM_PROMPT,
        tools=[
            get_stock_data,
            search_stock,
            compare_stocks,
            get_indicators,
            analyze_trend,
            list_strategies,
        ],
    )


# ADK CLI 실행을 위한 root_agent 노출
root_agent = create_agent()
