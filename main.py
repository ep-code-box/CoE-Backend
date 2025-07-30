import json
import os
from typing import Dict
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

# 분리된 모듈에서 스키마와 도구 노드 가져오기
from schemas import ChatState, ChatRequest, ChatResponse, Message
from llm_client import client, default_model # LLM 클라이언트와 기본 모델 정보 가져오기
from tools.utils import find_last_user_message
from tools.registry import load_all_tools
from models import model_registry # 모델 레지스트리 가져오기

# 1) 도구 레지스트리를 통해 모든 노드, 설명, 엣지를 동적으로 로드
all_nodes, all_tool_descriptions, all_special_edges = load_all_tools()

# 'end' 도구에 대한 설명 추가
all_tool_descriptions.append({
    "name": "end",
    "description": "사용자가 대화를 끝내고 싶어할 때 사용합니다."
})

# 2) 라우터가 사용할 유효한 도구 이름 목록 생성
VALID_TOOL_NAMES = [tool['name'] for tool in all_tool_descriptions]

# 3) 라우터 노드: 동적으로 생성된 설명을 기반으로 프롬프트 구성
def router_node(state: ChatState) -> dict:
    # 마지막 사용자 메시지를 original_input에 저장
    last_user_message = find_last_user_message(state["messages"]) # utils에서 가져온 함수 사용
    
    # 동적으로 도구 설명 목록 생성
    tool_descriptions_string = "\n".join(
        [f"- '{tool['name']}': {tool['description']}" for tool in all_tool_descriptions]
    )
    
    # 시스템 프롬프트 구성
    system_prompt = f"""사용자의 요청에 가장 적합한 도구를 다음 중에서 선택하세요.
{tool_descriptions_string}

특별 규칙:
- 만약 바로 이전의 시스템 메시지가 승인을 요청하는 내용이고 사용자가 'approve' 또는 'reject'와 유사한 응답을 했다면, 반드시 'process_approval' 도구를 선택해야 합니다.

응답은 반드시 다음 JSON 형식이어야 합니다: {{"next_tool": "선택한 도구"}}"""

    prompt_messages = state["messages"] + [
        {"role": "system", "content": system_prompt}
    ]
    try:
        resp = client.chat.completions.create(
            model=default_model.model_id, # 기본 모델 ID 사용
            messages=prompt_messages,
            response_format={"type": "json_object"} # JSON 모드 활성화
        )
        # OpenAI 객체를 dict로 변환하여 타입 일관성 유지
        response_message = resp.choices[0].message.model_dump()

        try:
            # LLM 응답(JSON) 파싱
            choice_json = json.loads(response_message["content"])
            choice = choice_json.get("next_tool")
            print(f"🤖[Router]: LLM이 선택한 도구: {choice}")
            if choice not in VALID_TOOL_NAMES: # 유효한 도구 이름 목록으로 검사
                raise ValueError(f"LLM이 유효하지 않은 도구({choice})를 반환했습니다.")
            # 다음 노드를 상태에 저장하고, LLM의 응답도 기록에 추가
            return {"messages": [response_message], "next_node": choice, "original_input": last_user_message}
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # 파싱 실패 시 오류 메시지를 기록하고 그래프 종료
            error_msg = f"라우터가 LLM 응답을 파싱하는 데 실패했습니다: {e}"
            print(f"🤖[Router]: Error - {error_msg}")
            return {"messages": [response_message, {"role": "system", "content": error_msg}], "next_node": "error"}

    except Exception as e:
        # API 호출 실패 시 오류 메시지를 기록하고 그래프 종료
        error_msg = f"라우터 API 호출에 실패했습니다: {e}"
        print(f"🤖[Router]: Error - {error_msg}")
        return {"messages": [{"role": "system", "content": error_msg}], "next_node": "error"}

# 5) 그래프 구성 및 컴파일 (모든 노드와 엣지 추가)
graph = StateGraph(ChatState)

# 라우터 노드 추가
graph.add_node("router", router_node)

# 레지스트리에서 로드한 모든 도구 노드를 동적으로 추가
for name, node_func in all_nodes.items():
    graph.add_node(name, node_func)

# 그래프의 시작점을 라우터로 설정
graph.set_entry_point("router")

# 라우터의 결정에 따라 다음 노드로 분기하도록 동적으로 엣지 매핑 생성
routable_tool_names = [tool['name'] for tool in all_tool_descriptions if tool['name'] != 'end']
edge_mapping = {name: name for name in routable_tool_names}
edge_mapping["combined_tool"] = "api_call"  # 'combined_tool'은 'api_call'로 시작하는 특별 케이스
edge_mapping["end"] = END
edge_mapping["error"] = END

graph.add_conditional_edges(
    "router",
    lambda state: state["next_node"],
    edge_mapping
)

# 레지스트리에서 로드한 특별한 엣지들을 동적으로 추가
special_edge_sources = set()
for edge_config in all_special_edges:
    source_node = edge_config["source"]
    special_edge_sources.add(source_node)
    if edge_config["type"] == "conditional":
        graph.add_conditional_edges(
            source_node,
            edge_config["condition"],
            edge_config["path_map"]
        )
    elif edge_config["type"] == "standard":
        graph.add_edge(source_node, edge_config["target"])

# 특별한 엣지가 정의된 노드와 라우터를 제외한 나머지 모든 노드는 작업 완료 후 종료(END)로 연결
nodes_with_special_outgoing_edges = special_edge_sources.union({"router"})
for node_name in all_nodes:
    if node_name not in nodes_with_special_outgoing_edges:
        graph.add_edge(node_name, END)

agent = graph.compile(interrupt_after=["human_approval"])

# 7) FastAPI 앱 생성 및 엔드포인트
app = FastAPI()

@app.get("/v1/models")
async def list_models():
    """
    models.json에 정의된 사용 가능한 모든 모델의 목록을 반환합니다.
    OpenAI의 /v1/models 엔드포인트와 호환되는 형식입니다.
    """
    all_models = model_registry.get_models()
    model_data = [
        {"id": model.model_id, "object": "model", "created": 1686935002, "owned_by": model.provider}
        for model in all_models
    ]
    return JSONResponse(content={
        "object": "list",
        "data": model_data
    })

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # Pydantic 모델을 내부 상태(dict)로 변환
    state = {
        "messages": [msg.model_dump() for msg in req.messages],
    }
    # 에이전트 실행 (비동기 방식으로 변경)
    result = await agent.ainvoke(state)
    return ChatResponse(messages=result["messages"])

if __name__ == "__main__":
    import uvicorn

    # .env 파일 로드 (개발 환경에서만 필요)
    load_dotenv()

    # 환경 변수를 통해 개발 모드와 프로덕션 모드를 구분합니다.
    # APP_ENV가 'development'일 때만 hot-reloading을 활성화합니다.
    is_development = os.getenv("APP_ENV") == "development"

    print(f"🚀 Starting server in {'development (hot-reload enabled)' if is_development else 'production'} mode.")

    uvicorn.run(
        "main:app",
        host="0.0.0.0", port=8000, reload=is_development
    )
