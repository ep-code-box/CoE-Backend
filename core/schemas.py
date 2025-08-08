from typing import Annotated, List, Literal, Dict, Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel


# LangGraph 상태 스키마
class ChatState(TypedDict):
    # messages는 항상 list로 초기화되도록 기본값 제공
    messages: Annotated[list, lambda x, y: x + y]
    # 라우팅 결정을 저장할 필드
    next_node: str
    # 조합 호출 예제를 위한 필드
    original_input: str | None
    api_data: dict | None


# FastAPI 요청·응답 모델
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

# OpenWebUI 호환을 위한 요청 스키마
class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    session_id: Optional[str] = None
    # 다른 OpenAI 파라미터들도 필요에 따라 추가 가능

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



class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None