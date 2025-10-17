from typing import Annotated, List, Literal, Dict, Any, Optional, Union
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, root_validator
from datetime import datetime
import json


# --- Modal Context Protocol State ---
class AgentState(TypedDict):
    """
    Modal Context Protocol을 위한 새로운 에이전트 상태입니다.
    OpenAI 함수 호출에 최적화된 구조를 가집니다.
    """
    
    # 현재 에이전트의 작동 모드 (예: 'coding', 'chat', 'planning')
    mode: str

    # 마지막 사용자 입력을 저장합니다.
    input: str
    
    # OpenAI 'messages'와 동일한 형식의 대화 기록입니다.
    # Annotated를 사용하여 LangGraph에서 메시지가 덮어쓰여지지 않고 추가되도록 합니다.
    history: Annotated[list, lambda x, y: x + y]

    # 도구 실행 결과 등 임시 데이터를 저장하기 위한 공간입니다.
    scratchpad: dict

    # 세션 ID를 상태에 포함하여 로깅 및 추적에 사용합니다.
    session_id: Optional[str]
    model_id: str
    group_name: Optional[str]

    # Front-end에서 전달된 도구 이름과 입력
    tool_input: Optional[Dict[str, Any]]
    context: Optional[str] # 도구 컨텍스트 (e.g., 'aider', 'continue.dev')
    tools: Optional[List["Tool"]] = None # 클라이언트에서 받은 도구 목록
    proactive_tool_call_made: Optional[bool] = False # 선제적 도구 호출 여부
    requested_tool_choice: Optional[Union[str, Dict[str, Any]]] = None


# --- OpenAI 호환 Tool Calling 스키마 ---

class Function(BaseModel):
    """Tool로 호출될 함수의 명세를 정의합니다."""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]

class Tool(BaseModel):
    """LLM이 사용할 수 있는 Tool의 명세를 정의합니다."""
    type: Literal["function"] = "function"
    function: Function

class ToolCallFunction(BaseModel):
    """모델이 호출하려는 함수의 이름과 인자를 담습니다."""
    name: str
    arguments: str

class ToolCall(BaseModel):
    """모델의 Tool 호출 요청 정보를 담습니다."""
    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction

# --- 메시지 타입 스키마 ---

class TextContentPart(BaseModel):
    """텍스트 기반 메시지 조각"""
    type: Literal["text", "input_text"]
    text: str


class ImageBase64ContentPart(BaseModel):
    """Base64 이미지 메시지 조각"""
    type: Literal["image_base64", "input_image"]
    image_base64: str
    mime_type: Optional[str] = None
    detail: Optional[str] = None


class ImageURLContentPart(BaseModel):
    """URL 기반 이미지 메시지 조각"""
    type: Literal["image_url"]
    image_url: Dict[str, Any]
    detail: Optional[str] = None


class FileBase64ContentPart(BaseModel):
    """Base64 일반 파일 메시지 조각"""
    type: Literal["file_base64", "input_file"]
    file_base64: str
    mime_type: Optional[str] = None
    filename: Optional[str] = None
    detail: Optional[str] = None


ChatContentPart = Union[
    TextContentPart,
    ImageBase64ContentPart,
    ImageURLContentPart,
    FileBase64ContentPart,
]
ChatMessageContent = Union[str, List[ChatContentPart]]


class SystemMessage(BaseModel):
    """시스템 메시지"""
    role: Literal["system"]
    content: ChatMessageContent


class UserMessage(BaseModel):
    """사용자 메시지"""
    role: Literal["user"]
    content: ChatMessageContent


class AssistantMessage(BaseModel):
    """어시스턴트 메시지. Tool 호출을 포함할 수 있습니다."""
    role: Literal["assistant"]
    content: Optional[ChatMessageContent] = None
    tool_calls: Optional[List[ToolCall]] = None


class ToolMessage(BaseModel):
    """Tool 실행 결과 메시지"""
    role: Literal["tool"]
    content: ChatMessageContent
    tool_call_id: str

# 메시지 리스트에 포함될 수 있는 모든 메시지 타입의 Union
# Pydantic이 JSON을 파싱할 때 'role' 필드를 보고 어떤 모델을 사용할지 결정합니다.
Message = Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage]


# FastAPI 요청·응답 모델
class ChatRequest(BaseModel):
    messages: List[Message]


# OpenAI 호환 채팅 요청 스키마
class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    session_id: Optional[str] = None
    # Tool Calling 관련 필드 추가
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[Literal["auto", "none"], Dict[str, Any]]] = None
    group_name: Optional[str] = None # RAG group_name 필드 추가
    # Front-end에서 전달된 도구 이름과 입력
    tool_input: Optional[Dict[str, Any]] = None
    context: Optional[str] = None # 도구 컨텍스트 (e.g., 'aider', 'continue.dev')


class AiderChatRequest(OpenAIChatRequest):
    group_name: Optional[str] = None # aider 전용 group_name 필드 추가


class ChatResponse(BaseModel):
    messages: List[dict]
    session_id: str


# LangFlow 관련 스키마
class LangFlowNode(BaseModel):
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]

class LangFlowEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None

class LangFlowData(BaseModel):
    nodes: List[LangFlowNode]
    edges: List[LangFlowEdge]
    viewport: Optional[Dict[str, Any]] = None

class LangFlowJSON(BaseModel):
    description: Optional[str] = None
    name: str
    id: str
    data: LangFlowData
    is_component: Optional[bool] = False

class SaveFlowRequest(BaseModel):
    name: str
    flow_data: LangFlowJSON
    description: Optional[str] = None

class FlowListResponse(BaseModel):
    flows: List[Dict[str, str]]  # [{"name": "flow_name", "id": "flow_id", "description": "..."}]

class ExecuteFlowRequest(BaseModel):
    flow_name: str
    inputs: Optional[Dict[str, Any]] = None
    tweaks: Optional[Dict[str, Any]] = None
    langflow_url: Optional[str] = None

class ExecuteFlowResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None

class ExposeFlowApiRequest(BaseModel):
    endpoint: str
    description: Optional[str] = None
    flow_body: LangFlowJSON
    flow_id: Optional[str] = None # Assuming langFlow provides this


# --- Dynamic Flow Schemas ---

class FlowCreate(BaseModel):
    endpoint: str = Field(..., description="API endpoint path for the flow. Must be unique.")
    description: Optional[str] = Field(None, description="A description for the flow.")
    flow_body: LangFlowJSON = Field(..., description="The JSON object defining the LangFlow.")
    flow_id: str = Field(..., description="The unique ID for the flow, typically from LangFlow itself.")
    # LangFlow를 사용할 수 있는 프론트 컨텍스트 지정 (예: 'aider', 'continue.dev', 'openWebUi')
    # 호환성: context는 문자열 또는 문자열 배열 모두 허용
    context: Optional[Union[str, List[str]]] = Field(
        None,
        description="Single context tag or array of tags to expose this flow."
    )
    contexts: Optional[List[str]] = Field(None, description="Context tags to expose this flow.")
    context_groups: Optional[List["FlowContextGroup"]] = Field(
        None,
        description="Optional list of context/group mappings. Each item specifies a context and its allowed group names."
    )


class FlowContextGroup(BaseModel):
    context: str = Field(..., description="Context name (e.g., 'aider').")
    group_names: Optional[List[str]] = Field(
        None,
        description="Group names allowed for this context. Omit or empty to mark the context as public."
    )


FlowCreate.model_rebuild()

class FlowRead(BaseModel):
    id: int
    endpoint: str
    description: Optional[str]
    flow_body: LangFlowJSON
    flow_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @root_validator(pre=True)
    def map_db_to_api_fields(cls, obj):
        # When loading from the DB model, 'name' and 'flow_data' will be present.
        # Create a dictionary from the ORM object's attributes
        mapped_values = {}
        if hasattr(obj, 'name'):
            mapped_values['endpoint'] = obj.name
        if hasattr(obj, 'flow_data'):
            flow_data_str = obj.flow_data
            if isinstance(flow_data_str, str):
                 mapped_values['flow_body'] = json.loads(flow_data_str)
            else:
                 mapped_values['flow_body'] = flow_data_str
        
        # Copy other attributes directly
        for attr in ['id', 'description', 'flow_id', 'is_active', 'created_at', 'updated_at']:
            if hasattr(obj, attr):
                mapped_values[attr] = getattr(obj, attr)

        return mapped_values


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    dependencies: Dict[str, str]

class ModelDetail(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "user"

class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelDetail]
