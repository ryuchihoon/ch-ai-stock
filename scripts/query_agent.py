"""
Agent 직접 질의 스크립트 (Mesop UI 없이 터미널에서 테스트)

사용법:
    uv run python scripts/query_agent.py "애플(AAPL) RSI 전략 신호 알려줘"
    uv run python scripts/query_agent.py "NVDA, TSLA 수익률 비교해줘"
    uv run python scripts/query_agent.py  # 인수 없으면 대화형 모드
"""

import asyncio
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from src.agent import create_agent

APP_NAME = "ch_ai_stock"
USER_ID = "user"
SESSION_ID = "session"


async def query(text: str) -> str:
    runner = InMemoryRunner(agent=create_agent(), app_name=APP_NAME)
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    content = genai_types.Content(
        role="user", parts=[genai_types.Part(text=text)]
    )
    for event in runner.run(
        user_id=USER_ID, session_id=SESSION_ID, new_message=content
    ):
        if event.is_final_response() and event.content:
            return event.content.parts[0].text
    return "(응답 없음)"


def main():
    if len(sys.argv) > 1:
        # 인수로 질문 전달: uv run python scripts/query_agent.py "질문"
        question = " ".join(sys.argv[1:])
        print(f"Q: {question}\n")
        try:
            answer = asyncio.run(query(question))
            print(f"A: {answer}")
        except Exception:
            traceback.print_exc()
    else:
        # 대화형 모드
        print("CH AI Stock Agent (종료: Ctrl+C 또는 'exit')\n")
        while True:
            try:
                question = input("Q: ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not question or question.lower() == "exit":
                break
            try:
                answer = asyncio.run(query(question))
                print(f"A: {answer}\n")
            except Exception:
                traceback.print_exc()


if __name__ == "__main__":
    main()
