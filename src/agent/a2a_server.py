"""
A2A 프로토콜 서버

agent.json 없이 to_a2a()로 Agent Card를 인메모리에서 자동 생성합니다.

실행:
    uvicorn src.agent.a2a_server:app --host localhost --port 8001

Agent Card 확인:
    curl http://localhost:8001/.well-known/agent-card.json
"""

from dotenv import load_dotenv

load_dotenv()

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from src.agent import create_agent

app = to_a2a(create_agent(), host="localhost", port=8001)
