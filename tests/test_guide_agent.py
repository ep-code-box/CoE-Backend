import asyncio
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

fake_langchain = types.ModuleType("langchain_openai")


class _FakeChatOpenAI:
    def __init__(self, *args, **kwargs):  # pragma: no cover - stub
        pass


fake_langchain.ChatOpenAI = _FakeChatOpenAI
sys.modules.setdefault("langchain_openai", fake_langchain)

fake_pidpy = types.ModuleType("pidpy")
fake_pidpy.__file__ = __file__
fake_pidpython = types.ModuleType("pidpy.pidpython")


class _FakePID:
    @staticmethod
    def Init(*args, **kwargs):  # pragma: no cover - stub
        return True

    @staticmethod
    def SetOption(*args, **kwargs):  # pragma: no cover - stub
        return None

    @staticmethod
    def RunType(text, parts, *_args, **_kwargs):  # pragma: no cover - stub
        return None

    @staticmethod
    def GetTypeSimpleName(_type):  # pragma: no cover - stub
        return "fake"

    @staticmethod
    def Terminate():  # pragma: no cover - stub
        return None


class StrPartVector(list):  # pragma: no cover - stub
    pass


PID_BIT_ALL = 0
PID_OPTION_CHECK_DIGIT = 0

fake_pidpython.PID = _FakePID
fake_pidpython.StrPartVector = StrPartVector
fake_pidpython.PID_BIT_ALL = PID_BIT_ALL
fake_pidpython.PID_OPTION_CHECK_DIGIT = PID_OPTION_CHECK_DIGIT

sys.modules.setdefault("pidpy", fake_pidpy)
sys.modules.setdefault("pidpy.pidpython", fake_pidpython)

from api.chat_api import _should_route_to_guide
from core.guide_agent.agent import GuideAgent
from core.guide_agent.formatter import format_result_as_markdown
from core.schemas import OpenAIChatRequest, UserMessage


class FakeRagClient:
    async def semantic_search(self, *, query: str, k: int = 5, **_: object):
        return [
            {
                "content": f"{query} 관련 테스트 케이스",
                "metadata": {"file_path": "tests/test_example.py"},
            }
        ]


def test_guide_agent_generates_recommendations():
    agent = GuideAgent(rag_client=FakeRagClient())

    result = asyncio.run(
        agent.run(
            prompt="테스트 전략 개선",
            paths=("src/example.py",),
        )
    )

    assert result.plan
    assert result.recommendations
    assert any("테스트" in insight for insight in result.insights)

    markdown = format_result_as_markdown(result)
    assert "요약" in markdown
    assert "추천" in markdown


def _req(**kwargs) -> OpenAIChatRequest:
    base = dict(
        model="test-model",
        messages=[UserMessage(role="user", content="hello")],
    )
    base.update(kwargs)
    return OpenAIChatRequest(**base)


def test_should_route_to_guide_by_context():
    req = _req(context="guide")
    assert _should_route_to_guide(req) is True


def test_should_route_to_guide_via_tool_input_flag():
    req = _req(tool_input={"guide_mode": True})
    assert _should_route_to_guide(req) is True


def test_should_route_to_guide_truthy_strings():
    req = _req(tool_input={"guide_agent": "Yes"})
    assert _should_route_to_guide(req) is True


def test_should_not_route_without_flags():
    req = _req(context="aider", tool_input={"guide_mode": False})
    assert _should_route_to_guide(req) is False
