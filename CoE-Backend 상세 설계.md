<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# CoE-Backend 상세 설계

CoE-Backend README를 기반으로 한 상세 설계를 정리하면 다음과 같습니다:

## 1. 사용자 관리 및 세션 관리

### 1.1 사용자 인증 시스템[^1][^2][^3]

```python
# core/auth.py
from fastapi_users import FastAPIUsers, BaseUserManager
from fastapi_users.authentication import JWTAuthentication
from fastapi_users.db import SQLAlchemyUserDatabase

class UserManager(BaseUserManager):
    user_db_model = User
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

# JWT 기반 인증
jwt_authentication = JWTAuthentication(
    secret=settings.SECRET_KEY,
    lifetime_seconds=3600,
    tokenUrl="auth/jwt/login",
)

fastapi_users = FastAPIUsers(
    user_manager,
    [jwt_authentication],
    User,
    UserCreate,
    UserUpdate,
    UserDB,
)
```


### 1.2 세션 관리[^1][^4]

```python
# core/database.py - 세션 데이터 모델
class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_token = Column(String(255), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # 3턴 멀티턴 대화 지원
    conversation_turns = Column(Integer, default=0)
    max_turns = Column(Integer, default=3)

# 채팅 메시지 히스토리
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"))
    role = Column(String(50))  # user, assistant, system
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    turn_number = Column(Integer)

# 대화 요약
class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"))
    summary_content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```


## 2. 인증 관리 및 API 보안

### 2.1 API 키 기반 인증[^5]

```python
# core/auth.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """API 키 검증"""
    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")
    
    # DB에서 API 키 검증
    api_key = await get_api_key(credentials.credentials)
    if not api_key or not api_key.is_active:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return api_key.user

# 권한 기반 접근 제어
async def require_permission(permission: str):
    def permission_checker(current_user = Depends(get_current_user)):
        if not has_permission(current_user, permission):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return permission_checker
```


### 2.2 사용자 권한 관리

```python
# core/models.py
class UserRole(Base):
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)  # admin, user, developer
    permissions = Column(JSON)  # ["chat:create", "tools:execute", "flows:manage"]

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True)
    email = Column(String(255), unique=True)
    hashed_password = Column(String(255))
    role_id = Column(Integer, ForeignKey("user_roles.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```


## 3. OpenWebUI \& LangFlow 백엔드 기능

### 3.1 OpenWebUI 호환 API[^6][^7][^8]

```python
# api/chat_api.py - OpenAI 호환 채팅 API
@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    current_user = Depends(get_current_user)
):
    """OpenWebUI 호환 채팅 API"""
    
    # 세션 관리
    session = await get_or_create_session(current_user.id)
    
    # 3턴 제한 확인
    if session.conversation_turns >= session.max_turns:
        # 새 세션 생성 또는 요약 후 리셋
        session = await reset_session_with_summary(session)
    
    # LangGraph 에이전트 실행
    if request.model == "coe-agent-v1":
        response = await execute_langgraph_agent(request, session)
    else:
        # 직접 LLM 프록시
        response = await proxy_to_llm(request)
    
    # 메시지 저장
    await save_chat_messages(session.id, request.messages, response)
    
    return response

@router.get("/v1/models")
async def list_models():
    """사용 가능한 모델 목록"""
    return {
        "data": [
            {"id": "coe-agent-v1", "object": "model"},
            {"id": "gpt-4o-mini", "object": "model"},
            {"id": "claude-3-sonnet", "object": "model"},
            {"id": "gpt-4o", "object": "model"}
        ]
    }
```


### 3.2 LangFlow 워크플로우 관리[^7]

```python
# api/flows_api.py
@router.post("/flows/save")
async def save_flow(
    flow_data: FlowSaveRequest,
    current_user = Depends(require_permission("flows:manage"))
):
    """LangFlow 워크플로우 저장"""
    
    flow = WorkflowFlow(
        name=flow_data.name,
        description=flow_data.description,
        flow_data=flow_data.flow_data,
        user_id=current_user.id,
        created_at=datetime.utcnow()
    )
    
    await save_to_database(flow)
    await save_to_file(f"flows/{flow.name}.json", flow.flow_data)
    
    return {"status": "success", "flow_id": flow.id}

# core/models.py - LangFlow 데이터 모델
class WorkflowFlow(Base):
    __tablename__ = "workflow_flows"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    description = Column(Text)
    flow_data = Column(JSON)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
```


## 4. LangGraph 기반 AI4X 모델 도구 선택

### 4.1 동적 도구 레지스트리[^9][^10][^11]

```python
# tools/registry.py - 확장된 도구 레지스트리
class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.tool_descriptions = {}
        self.tool_embeddings = {}  # 도구 선택 최적화용
    
    async def load_all_tools(self):
        """도구 동적 로딩"""
        tools_dir = Path("tools")
        
        for file_path in tools_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
                
            module = await self._load_module(file_path)
            await self._register_tools_from_module(module)
    
    async def select_relevant_tools(self, query: str, max_tools: int = 5) -> List[str]:
        """LLM 쿼리 기반 관련 도구 선택"""
        
        # 의미적 유사성 기반 도구 선택
        query_embedding = await get_embedding(query)
        
        similarities = []
        for tool_name, tool_embedding in self.tool_embeddings.items():
            similarity = cosine_similarity(query_embedding, tool_embedding)
            similarities.append((tool_name, similarity))
        
        # 상위 N개 도구 선택
        top_tools = sorted(similarities, key=lambda x: x[^1], reverse=True)[:max_tools]
        return [tool[^0] for tool in top_tools]
```


### 4.2 LangGraph 에이전트 구성[^11][^12][^13]

```python
# core/graph_builder.py - AI4X 모델 기반 도구 라우팅
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic  # AI4X 모델

class CoEAgent:
    def __init__(self):
        self.llm = ChatAnthropic(model="claude-3-sonnet-20240229")  # AI4X 모델
        self.tool_registry = ToolRegistry()
        self.graph = None
    
    async def build_graph(self):
        """동적 그래프 구성"""
        
        # 상태 스키마 정의
        workflow = StateGraph(ChatState)
        
        # 핵심 노드들
        workflow.add_node("tool_selector", self.tool_selection_node)
        workflow.add_node("router", self.router_node)
        workflow.add_node("executor", self.tool_execution_node)
        workflow.add_node("summarizer", self.response_generation_node)
        
        # 조건부 엣지 (AI4X 모델 기반 라우팅)
        workflow.add_conditional_edges(
            "router",
            self.route_based_on_llm_decision,
            {
                "execute_tool": "executor",
                "direct_response": "summarizer",
                "need_more_info": "tool_selector",
                END: END
            }
        )
        
        workflow.set_entry_point("tool_selector")
        self.graph = workflow.compile()
    
    async def tool_selection_node(self, state: ChatState) -> Dict:
        """관련 도구 선택"""
        query = state["messages"][-1]["content"]
        
        # 최대 5개 관련 도구 선택
        relevant_tools = await self.tool_registry.select_relevant_tools(query, max_tools=5)
        
        return {
            **state,
            "available_tools": relevant_tools,
            "tool_selection_reasoning": f"Selected {len(relevant_tools)} relevant tools"
        }
    
    async def router_node(self, state: ChatState) -> Dict:
        """AI4X 모델 기반 라우팅 결정"""
        
        # AI4X 모델에게 다음 행동 결정 요청
        system_prompt = """
        당신은 사용자 요청을 분석하여 적절한 도구를 선택하는 라우터입니다.
        
        사용 가능한 도구들: {available_tools}
        사용자 요청: {user_query}
        
        다음 중 하나를 선택하세요:
        1. execute_tool: 특정 도구 실행이 필요한 경우
        2. direct_response: 도구 없이 직접 응답 가능한 경우  
        3. need_more_info: 더 많은 정보나 다른 도구가 필요한 경우
        4. END: 작업 완료
        
        응답 형식: {{"action": "선택한_액션", "selected_tool": "도구명", "reasoning": "선택 이유"}}
        """.format(
            available_tools=state.get("available_tools", []),
            user_query=state["messages"][-1]["content"]
        )
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["messages"][-1]["content"]}
        ])
        
        decision = parse_llm_decision(response.content)
        
        return {
            **state,
            "routing_decision": decision,
            "selected_tool": decision.get("selected_tool"),
            "routing_reasoning": decision.get("reasoning")
        }
    
    async def route_based_on_llm_decision(self, state: ChatState) -> str:
        """라우팅 결정 해석"""
        decision = state.get("routing_decision", {})
        return decision.get("action", "direct_response")
```


### 4.3 도구 실행 및 응답 생성

```python
# core/graph_builder.py 계속
    async def tool_execution_node(self, state: ChatState) -> Dict:
        """선택된 도구 실행"""
        tool_name = state.get("selected_tool")
        
        if not tool_name or tool_name not in self.tool_registry.tools:
            return {
                **state,
                "tool_result": "도구를 찾을 수 없습니다.",
                "execution_status": "failed"
            }
        
        try:
            tool = self.tool_registry.tools[tool_name]
            result = await tool.ainvoke(state)
            
            return {
                **state,
                "tool_result": result,
                "execution_status": "success"
            }
        except Exception as e:
            return {
                **state,
                "tool_result": f"도구 실행 오류: {str(e)}",
                "execution_status": "error"
            }
    
    async def response_generation_node(self, state: ChatState) -> Dict:
        """최종 응답 생성"""
        
        # 컨텍스트 구성
        context = {
            "user_query": state["messages"][-1]["content"],
            "tool_results": state.get("tool_result", ""),
            "execution_status": state.get("execution_status", ""),
            "conversation_history": state["messages"][:-1]
        }
        
        # AI4X 모델로 최종 응답 생성
        system_prompt = """
        사용자의 요청에 대해 도구 실행 결과를 바탕으로 종합적인 답변을 제공하세요.
        
        실행된 도구 결과: {tool_results}
        실행 상태: {execution_status}
        
        답변은 정확하고 도움이 되며, 필요시 추가 질문을 유도하세요.
        """.format(**context)
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": system_prompt},
            *state["messages"]
        ])
        
        return {
            **state,
            "messages": state["messages"] + [
                {"role": "assistant", "content": response.content}
            ],
            "final_response": response.content
        }
```


## 5. 추가 고려사항

### 5.1 성능 최적화

- **도구 선택 캐싱**: 자주 사용되는 도구 조합 캐싱
- **임베딩 캐싱**: 도구 설명 임베딩 사전 계산 및 캐싱
- **세션 풀링**: 연결 풀을 통한 데이터베이스 성능 최적화


### 5.2 보안 강화

- **API 레이트 리미팅**: 사용자별/IP별 요청 제한
- **입력 검증**: 모든 사용자 입력에 대한 철저한 검증
- **감사 로깅**: 모든 API 호출 및 도구 실행 로그


### 5.3 모니터링 및 디버깅

- **실시간 모니터링**: 에이전트 실행 상태 실시간 추적
- **성능 메트릭**: 도구 선택 정확도, 응답 시간 측정
- **오류 추적**: 실패한 도구 실행 및 라우팅 결정 분석

이러한 설계를 통해 CoE-Backend는 안전하고 확장 가능한 AI 에이전트 플랫폼으로 동작하며, OpenWebUI와 LangFlow의 완벽한 백엔드 역할을 수행할 수 있습니다.

<div style="text-align: center">⁂</div>

[^1]: https://jordanisaacs.github.io/fastapi-sessions/guide/getting_started/

[^2]: https://github.com/fastapi-users/fastapi-users

[^3]: https://betterstack.com/community/guides/scaling-python/authentication-fastapi/

[^4]: https://recording-it.tistory.com/93

[^5]: https://fastapi.tiangolo.com/tutorial/security/

[^6]: https://docs.openwebui.com/features/

[^7]: https://docs.openwebui.com/openapi-servers/open-webui/

[^8]: https://docs.openwebui.com

[^9]: https://www.reddit.com/r/LangChain/comments/1fo7vft/bindtools_vs_router_llm_node_which_one_is_better/

[^10]: https://langchain-ai.github.io/langgraph/how-tos/many-tools/

[^11]: https://dev.to/jamesli/advanced-langgraph-implementing-conditional-edges-and-tool-calling-agents-3pdn

[^12]: https://phase2online.com/2025/02/24/executive-overview-understanding-langgraph-for-llm-powered-workflows/

[^13]: https://langchain-ai.github.io/langgraph/concepts/agentic_concepts/

[^14]: README.md

[^15]: https://stackoverflow.com/questions/78628681/how-to-do-session-based-authentication-when-combining-fastapi-with-django

[^16]: https://open-webui.com/comfyui/

[^17]: https://rudaks.tistory.com/entry/langgraph-많은-수의-도구tool를-처리하는-방법

[^18]: https://github.com/open-webui/open-webui

[^19]: https://wikidocs.net/176934

[^20]: https://docs.openwebui.com/getting-started/advanced-topics/development/

[^21]: https://blog.langchain.com/langgraph-multi-agent-workflows/

