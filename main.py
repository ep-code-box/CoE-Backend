import json
from typing import Dict
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from langgraph.graph import StateGraph, START, END

# 분리된 모듈에서 스키마와 도구 노드 가져오기
from schemas import ChatState, ChatRequest, ChatResponse, Message
from llm_client import client, MODEL_NAME # LLM 클라이언트와 모델 이름 가져오기

# 모든 도구 노드 가져오기
from tools.api_tool import api_call_node
from tools.class_tool import class_call_node, class_analysis_node
from tools.human_tool import human_approval_node
from tools.subgraph_tool import sub_graph_node
from tools.langchain_tool import langchain_chain_node
from tools.basic_tools import tool1_node, tool2_node
from tools.utils import find_last_user_message

# 3) 라우터 노드: LLM에 분기 요청 (모든 도구를 포함하도록 프롬프트 확장)
def router_node(state: ChatState) -> dict:
    # 마지막 사용자 메시지를 original_input에 저장
    last_user_message = find_last_user_message(state["messages"]) # utils에서 가져온 함수 사용

    prompt_messages = state["messages"] + [
        {"role":"system","content":
         """사용자의 요청에 가장 적합한 도구를 다음 중에서 선택하세요.
         - 'tool1': 텍스트를 대문자로 변환합니다.
         - 'tool2': 텍스트를 역순으로 변환합니다.
         - 'api_call': 외부 API를 호출하여 사용자 정보를 가져옵니다. (예: "1번 사용자 정보 알려줘")
         - 'class_call': 텍스트를 분석합니다. (예: "이 문장 분석해줘")
         - 'sub_graph': 인사를 처리합니다. (예: "안녕")
         - 'human_approval': 사람의 승인이 필요한 작업을 요청합니다. (예: "중요한 작업 승인해줘")
         - 'langchain_chain': 텍스트를 요약합니다. (예: "이 긴 글을 요약해줘")
         - 'combined_tool': API로 데이터를 가져와 클래스로 분석하는 조합 작업입니다. (예: "1번 사용자 데이터 분석해줘")
         - 'end': 사용자가 대화를 끝내고 싶어할 때 사용합니다.

         응답은 반드시 다음 JSON 형식이어야 합니다: {"next_tool": "선택한 도구"}"""}
    ]
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME, # 환경 변수에서 읽은 모델 이름 사용
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
            if choice not in ["tool1", "tool2", "api_call", "class_call", "sub_graph", "human_approval", "langchain_chain", "combined_tool", "end"]:
                raise ValueError(f"LLM이 유효하지 않은 도구({choice})를 반환했습니다.")
            # 다음 노드를 상태에 저장하고, LLM의 응답도 기록에 추가
            return {"messages": [response_message], "next_node": choice, "original_input": last_user_message}
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # 파싱 실패 시 오류 메시지를 기록하고 그래프 종료
            error_msg = f"라우터가 LLM 응답을 파싱하는 데 실패했습니다: {e}"
            print(f"🤖[Router]: Error - {error_msg}")
            return {"messages": [response_message, {"role": "system", "content": error_msg}], "next_node": "error", "original_input": last_user_message}

    except Exception as e:
        # API 호출 실패 시 오류 메시지를 기록하고 그래프 종료
        error_msg = f"라우터 API 호출에 실패했습니다: {e}"
        print(f"🤖[Router]: Error - {error_msg}")
        return {"messages": [{"role": "system", "content": error_msg}], "next_node": "error"}

# 5) 그래프 구성 및 컴파일 (모든 노드와 엣지 추가)
graph = StateGraph(ChatState)

# 라우터와 모든 도구 노드를 그래프에 추가
graph.add_node("router", router_node)
graph.add_node("tool1", tool1_node)
graph.add_node("tool2", tool2_node)
graph.add_node("api_call", api_call_node)
graph.add_node("class_call", class_call_node)
graph.add_node("sub_graph", sub_graph_node)
graph.add_node("human_approval", human_approval_node)
graph.add_node("langchain_chain", langchain_chain_node)
graph.add_node("class_analysis", class_analysis_node)

graph.set_entry_point("router")

# 'router' 노드의 결과('next_node' 상태)에 따라 분기
graph.add_conditional_edges(
    "router",
    lambda state: state["next_node"],
    {
        "tool1": "tool1",
        "tool2": "tool2",
        "api_call": "api_call",
        "class_call": "class_call",
        "sub_graph": "sub_graph",
        "human_approval": "human_approval",
        "langchain_chain": "langchain_chain",
        "combined_tool": "api_call", # 조합 호출의 시작점
        "end": END,
        "error": END, # 'error'일 경우 그래프 종료
    }
)

# 조합 호출을 위한 엣지 연결 (API 호출 후 클래스 분석)
graph.add_edge("api_call", "class_analysis")
graph.add_edge("class_analysis", END)

# 단일 작업 노드들은 모두 종료(END)로 연결
graph.add_edge("tool1", END)
graph.add_edge("tool2", END)
graph.add_edge("class_call", END)
graph.add_edge("sub_graph", END)
graph.add_edge("human_approval", END) # Human-in-the-loop은 여기서 중단됨
graph.add_edge("langchain_chain", END)

agent = graph.compile(interrupt_after=["human_approval"])

# 7) FastAPI 앱 생성 및 엔드포인트
app = FastAPI()

@app.get("/v1/models")
async def list_models():
    """
    LangChain의 ChatOpenAI 클라이언트가 모델 목록을 조회할 때 사용하는
    OpenAI 호환 엔드포인트를 구현합니다.
    """
    return JSONResponse(content={
        "object": "list",
        "data": [{
            "id": MODEL_NAME,
            "object": "model",
            "created": 1686935002,
            "owned_by": "user"
        }]
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
    # app: FastAPI 인스턴스
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    import uvicorn
    # app: FastAPI 인스턴스
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)