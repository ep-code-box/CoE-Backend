"""
스키마 모듈 단위 테스트
"""
import pytest
from typing import List
from pydantic import ValidationError

from core.schemas import (
    ChatState,
    Message,
    ChatRequest,
    OpenAIChatRequest,
    ChatResponse,
    LangFlowNode,
    LangFlowEdge
)


class TestMessage:
    """메시지 스키마 테스트"""
    
    def test_valid_message_creation(self):
        """유효한 메시지 생성"""
        message = Message(role="user", content="Hello, world!")
        
        assert message.role == "user"
        assert message.content == "Hello, world!"
    
    def test_message_role_validation(self):
        """메시지 역할 검증"""
        # 유효한 역할들
        valid_roles = ["system", "user", "assistant"]
        for role in valid_roles:
            message = Message(role=role, content="Test content")
            assert message.role == role
        
        # 잘못된 역할
        with pytest.raises(ValidationError):
            Message(role="invalid_role", content="Test content")
    
    def test_message_content_required(self):
        """메시지 내용 필수 검증"""
        with pytest.raises(ValidationError):
            Message(role="user")  # content 누락
    
    def test_message_serialization(self):
        """메시지 직렬화"""
        message = Message(role="assistant", content="Test response")
        data = message.model_dump()
        
        assert data == {
            "role": "assistant",
            "content": "Test response"
        }


class TestChatRequest:
    """채팅 요청 스키마 테스트"""
    
    def test_valid_chat_request(self):
        """유효한 채팅 요청"""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!")
        ]
        request = ChatRequest(messages=messages)
        
        assert len(request.messages) == 2
        assert request.messages[0].role == "user"
        assert request.messages[1].role == "assistant"
    
    def test_empty_messages_list(self):
        """빈 메시지 리스트"""
        request = ChatRequest(messages=[])
        assert request.messages == []
    
    def test_chat_request_serialization(self):
        """채팅 요청 직렬화"""
        messages = [Message(role="user", content="Test")]
        request = ChatRequest(messages=messages)
        data = request.model_dump()
        
        assert "messages" in data
        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "user"


class TestOpenAIChatRequest:
    """OpenAI 채팅 요청 스키마 테스트"""
    
    def test_minimal_openai_request(self):
        """최소한의 OpenAI 요청"""
        messages = [Message(role="user", content="Hello")]
        request = OpenAIChatRequest(
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        assert request.model == "gpt-3.5-turbo"
        assert len(request.messages) == 1
        assert request.stream is False  # 기본값
        assert request.temperature == 0.7  # 기본값
    
    def test_full_openai_request(self):
        """전체 옵션이 포함된 OpenAI 요청"""
        messages = [Message(role="user", content="Hello")]
        request = OpenAIChatRequest(
            model="gpt-4",
            messages=messages,
            stream=True,
            temperature=0.9,
            max_tokens=1000
        )
        
        assert request.model == "gpt-4"
        assert request.stream is True
        assert request.temperature == 0.9
        assert request.max_tokens == 1000
    
    def test_openai_request_validation(self):
        """OpenAI 요청 검증"""
        # model 필드 누락
        with pytest.raises(ValidationError):
            OpenAIChatRequest(messages=[])
        
        # messages 필드 누락
        with pytest.raises(ValidationError):
            OpenAIChatRequest(model="gpt-3.5-turbo")
    
    def test_temperature_bounds(self):
        """온도 값 경계 테스트"""
        messages = [Message(role="user", content="Test")]
        
        # 유효한 온도 값들
        valid_temps = [0.0, 0.5, 1.0, 2.0]
        for temp in valid_temps:
            request = OpenAIChatRequest(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temp
            )
            assert request.temperature == temp


class TestChatResponse:
    """채팅 응답 스키마 테스트"""
    
    def test_chat_response_creation(self):
        """채팅 응답 생성"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        response = ChatResponse(messages=messages)
        
        assert len(response.messages) == 2
        assert response.messages[0]["role"] == "user"
        assert response.messages[1]["role"] == "assistant"
    
    def test_empty_chat_response(self):
        """빈 채팅 응답"""
        response = ChatResponse(messages=[])
        assert response.messages == []


class TestLangFlowNode:
    """LangFlow 노드 스키마 테스트"""
    
    def test_valid_langflow_node(self):
        """유효한 LangFlow 노드"""
        node = LangFlowNode(
            id="node-1",
            type="TextInput",
            position={"x": 100.0, "y": 200.0},
            data={"text": "Hello, world!", "template": "input"}
        )
        
        assert node.id == "node-1"
        assert node.type == "TextInput"
        assert node.position["x"] == 100.0
        assert node.position["y"] == 200.0
        assert node.data["text"] == "Hello, world!"
    
    def test_langflow_node_required_fields(self):
        """LangFlow 노드 필수 필드"""
        # 필수 필드 누락 테스트
        with pytest.raises(ValidationError):
            LangFlowNode(type="TextInput", position={"x": 0, "y": 0}, data={})
        
        with pytest.raises(ValidationError):
            LangFlowNode(id="node-1", position={"x": 0, "y": 0}, data={})
        
        with pytest.raises(ValidationError):
            LangFlowNode(id="node-1", type="TextInput", data={})
        
        with pytest.raises(ValidationError):
            LangFlowNode(id="node-1", type="TextInput", position={"x": 0, "y": 0})
    
    def test_langflow_node_serialization(self):
        """LangFlow 노드 직렬화"""
        node = LangFlowNode(
            id="test-node",
            type="CustomNode",
            position={"x": 50.0, "y": 75.0},
            data={"config": {"param1": "value1"}}
        )
        
        data = node.model_dump()
        expected = {
            "id": "test-node",
            "type": "CustomNode",
            "position": {"x": 50.0, "y": 75.0},
            "data": {"config": {"param1": "value1"}}
        }
        
        assert data == expected


class TestLangFlowEdge:
    """LangFlow 엣지 스키마 테스트"""
    
    def test_valid_langflow_edge(self):
        """유효한 LangFlow 엣지"""
        edge = LangFlowEdge(
            id="edge-1",
            source="node-1",
            target="node-2",
            sourceHandle="output",
            targetHandle="input"
        )
        
        assert edge.id == "edge-1"
        assert edge.source == "node-1"
        assert edge.target == "node-2"
        assert edge.sourceHandle == "output"
    
    def test_langflow_edge_minimal(self):
        """최소한의 LangFlow 엣지"""
        edge = LangFlowEdge(
            id="edge-1",
            source="node-1",
            target="node-2"
        )
        
        assert edge.id == "edge-1"
        assert edge.source == "node-1"
        assert edge.target == "node-2"
        assert edge.sourceHandle is None  # 기본값
    
    def test_langflow_edge_required_fields(self):
        """LangFlow 엣지 필수 필드"""
        # 필수 필드 누락 테스트
        with pytest.raises(ValidationError):
            LangFlowEdge(source="node-1", target="node-2")  # id 누락
        
        with pytest.raises(ValidationError):
            LangFlowEdge(id="edge-1", target="node-2")  # source 누락
        
        with pytest.raises(ValidationError):
            LangFlowEdge(id="edge-1", source="node-1")  # target 누락


class TestChatState:
    """채팅 상태 스키마 테스트"""
    
    def test_chat_state_creation(self):
        """채팅 상태 생성"""
        state = ChatState(
            messages=[{"role": "user", "content": "Hello"}],
            next_node="router",
            original_input="Hello",
            api_data={"key": "value"}
        )
        
        assert len(state["messages"]) == 1
        assert state["next_node"] == "router"
        assert state["original_input"] == "Hello"
        assert state["api_data"]["key"] == "value"
    
    def test_chat_state_message_accumulation(self):
        """채팅 상태 메시지 누적 테스트"""
        # TypedDict의 Annotated 동작 테스트는 실제 LangGraph 컨텍스트에서 수행됨
        # 여기서는 기본 구조만 테스트
        state = ChatState(
            messages=[],
            next_node="start",
            original_input=None,
            api_data=None
        )
        
        assert state["messages"] == []
        assert state["next_node"] == "start"
        assert state["original_input"] is None
        assert state["api_data"] is None


@pytest.mark.unit
class TestSchemaIntegration:
    """스키마 통합 테스트"""
    
    def test_message_to_chat_request_flow(self):
        """메시지에서 채팅 요청까지의 플로우"""
        # 1. 개별 메시지 생성
        user_msg = Message(role="user", content="Hello")
        assistant_msg = Message(role="assistant", content="Hi!")
        
        # 2. 채팅 요청 생성
        chat_request = ChatRequest(messages=[user_msg, assistant_msg])
        
        # 3. OpenAI 요청으로 변환
        openai_request = OpenAIChatRequest(
            model="gpt-3.5-turbo",
            messages=chat_request.messages,
            stream=False
        )
        
        assert len(openai_request.messages) == 2
        assert openai_request.messages[0].role == "user"
        assert openai_request.messages[1].role == "assistant"
    
    def test_langflow_node_edge_relationship(self):
        """LangFlow 노드와 엣지 관계 테스트"""
        # 노드 생성
        node1 = LangFlowNode(
            id="input-node",
            type="TextInput",
            position={"x": 0, "y": 0},
            data={"text": "Input"}
        )
        
        node2 = LangFlowNode(
            id="output-node",
            type="TextOutput",
            position={"x": 200, "y": 0},
            data={"text": "Output"}
        )
        
        # 엣지 생성
        edge = LangFlowEdge(
            id="connection-1",
            source=node1.id,
            target=node2.id
        )
        
        assert edge.source == node1.id
        assert edge.target == node2.id