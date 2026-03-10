"""
CH AI Stock - Mesop UI

실행: uv run mesop src/ui/app.py
"""

import asyncio
from dataclasses import dataclass, field

from dotenv import load_dotenv
load_dotenv()  # ADK/Gemini 초기화 전에 .env 로드

import mesop as me
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from src.agent import create_agent

# ---------------------------------------------------------------------------
# ADK Runner 초기화 (앱 시작 시 1회)
# ---------------------------------------------------------------------------

_APP_NAME = "ch_ai_stock"
_SESSION_ID = "default_session"
_USER_ID = "user"

_runner = InMemoryRunner(agent=create_agent(), app_name=_APP_NAME)

# session_service 메서드는 async → 모듈 로드 시점에 동기로 한 번 실행
asyncio.run(
    _runner.session_service.create_session(
        app_name=_APP_NAME,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
    )
)


# ---------------------------------------------------------------------------
# 상태
# ---------------------------------------------------------------------------

@dataclass
class ChatMessage:
    role: str        # "user" | "assistant"
    content: str
    is_loading: bool = False


@me.stateclass
class AppState:
    messages: list[ChatMessage] = field(default_factory=list)
    input_text: str = ""
    is_loading: bool = False


# ---------------------------------------------------------------------------
# ADK 호출
# ---------------------------------------------------------------------------

def _call_agent(user_input: str) -> str:
    """ADK Runner를 통해 Agent를 호출하고 최종 텍스트 응답을 반환한다."""
    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_input)],
    )

    response_text = ""
    for event in _runner.run(
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    return response_text or "응답을 생성하지 못했습니다."


# ---------------------------------------------------------------------------
# 이벤트 핸들러
# ---------------------------------------------------------------------------

def on_input_change(e: me.InputEvent):
    state = me.state(AppState)
    state.input_text = e.value


def on_send(e: me.ClickEvent):
    state = me.state(AppState)
    user_text = state.input_text.strip()
    if not user_text or state.is_loading:
        return

    state.messages.append(ChatMessage(role="user", content=user_text))
    state.messages.append(ChatMessage(role="assistant", content="", is_loading=True))
    state.input_text = ""
    state.is_loading = True
    yield

    try:
        response = _call_agent(user_text)
    except Exception as ex:
        response = f"오류가 발생했습니다: {ex}"

    state.messages.pop()
    state.messages.append(ChatMessage(role="assistant", content=response))
    state.is_loading = False


def on_key_down(e: me.InputEnterEvent):
    state = me.state(AppState)
    user_text = state.input_text.strip()
    if not user_text or state.is_loading:
        return

    state.messages.append(ChatMessage(role="user", content=user_text))
    state.messages.append(ChatMessage(role="assistant", content="", is_loading=True))
    state.input_text = ""
    state.is_loading = True
    yield

    try:
        response = _call_agent(user_text)
    except Exception as ex:
        response = f"오류가 발생했습니다: {ex}"

    state.messages.pop()
    state.messages.append(ChatMessage(role="assistant", content=response))
    state.is_loading = False


# ---------------------------------------------------------------------------
# 컴포넌트
# ---------------------------------------------------------------------------

def signal_color(signal: str) -> str:
    return {"BUY": "#26a69a", "SELL": "#ef5350", "HOLD": "#78909c"}.get(signal, "#78909c")


@me.component
def chat_bubble(message: ChatMessage):
    is_user = message.role == "user"
    with me.box(style=me.Style(
        display="flex",
        justify_content="flex-end" if is_user else "flex-start",
        margin=me.Margin(bottom=12),
    )):
        with me.box(style=me.Style(
            background="#1565C0" if is_user else "#263238",
            color="#ffffff",
            padding=me.Padding.all(12),
            border_radius=12,
            max_width="75%",
            font_size=14,
            line_height="1.6",
            white_space="pre-wrap",
        )):
            if message.is_loading:
                me.text("분석 중...", style=me.Style(color="#90A4AE", font_style="italic"))
            else:
                me.markdown(message.content)


# ---------------------------------------------------------------------------
# 페이지
# ---------------------------------------------------------------------------

@me.page(
    path="/",
    title="CH AI Stock",
    security_policy=me.SecurityPolicy(dangerously_disable_trusted_types=True),
)
def main_page():
    state = me.state(AppState)

    with me.box(style=me.Style(
        display="flex",
        flex_direction="column",
        height="100vh",
        background="#121212",
        color="#ECEFF1",
        font_family="'Noto Sans KR', sans-serif",
    )):
        # 헤더
        with me.box(style=me.Style(
            padding=me.Padding.symmetric(vertical=16, horizontal=24),
            background="#1A237E",
            display="flex",
            align_items="center",
            gap=12,
        )):
            me.text("📈 CH AI Stock", style=me.Style(
                font_size=20, font_weight="bold", color="#E8EAF6"
            ))
            me.text("AI 주식 분석 도우미", style=me.Style(
                font_size=13, color="#9FA8DA"
            ))

        # 채팅 영역
        with me.box(style=me.Style(
            flex="1",
            overflow_y="auto",
            padding=me.Padding.all(20),
            display="flex",
            flex_direction="column",
        )):
            if not state.messages:
                _welcome_message()
            else:
                for msg in state.messages:
                    chat_bubble(message=msg)

        # 입력 영역
        with me.box(style=me.Style(
            padding=me.Padding.all(16),
            background="#1E1E1E",
            border=me.Border(top=me.BorderSide(width=1, color="#37474F", style="solid")),
            display="flex",
            gap=12,
            align_items="flex-end",
        )):
            with me.box(style=me.Style(flex="1")):
                me.input(
                    label="종목을 입력하세요 (예: AAPL 분석해줘, 삼성전자 RSI 전략 분석)",
                    value=state.input_text,
                    on_input=on_input_change,
                    on_enter=on_key_down,
                    style=me.Style(width="100%"),
                    disabled=state.is_loading,
                )
            me.button(
                "전송",
                on_click=on_send,
                disabled=state.is_loading,
                style=me.Style(
                    background="#1565C0",
                    color="#ffffff",
                    padding=me.Padding.symmetric(vertical=10, horizontal=20),
                    border_radius=8,
                ),
            )


@me.component
def _welcome_message():
    with me.box(style=me.Style(
        display="flex",
        flex_direction="column",
        align_items="center",
        justify_content="center",
        flex="1",
        gap=16,
        color="#78909C",
        padding=me.Padding.all(40),
    )):
        me.text("📊", style=me.Style(font_size=48))
        me.text("무엇이든 물어보세요", style=me.Style(font_size=20, font_weight="bold", color="#B0BEC5"))
        me.text("예시 질문:", style=me.Style(font_size=13))
        for example in [
            "AAPL을 MA 크로스오버 전략으로 분석해줘",
            "삼성전자(005930) RSI 전략 분석 부탁해",
            "NVDA, TSLA, MSFT 수익률 비교해줘",
            "사용 가능한 전략 목록 알려줘",
        ]:
            with me.box(style=me.Style(
                background="#1E272E",
                padding=me.Padding.symmetric(vertical=8, horizontal=16),
                border_radius=20,
                font_size=13,
            )):
                me.text(example)
