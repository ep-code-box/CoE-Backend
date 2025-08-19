from fastapi import FastAPI, APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from core import schemas
from core.database import get_db
# from langflow import run_flow_from_json # 가상 langflow 라이브러리 함수

# 임시로 langflow 실행 함수를 흉내 냅니다.
def run_flow_from_json(flow_definition: Dict[str, Any], user_input: Dict[str, Any]) -> Dict[str, Any]:
    print(f"--- Running Flow: {flow_definition.get('name')} ---")
    print(f"Input: {user_input}")
    # 실제로는 여기서 langflow 라이브러리가 복잡한 처리를 합니다.
    # 결과물은 flow의 마지막 노드 출력이라고 가정합니다.
    result = {"message": f"Flow executed successfully with input: {user_input.get('text', '')}"}
    print(f"Output: {result}")
    return result

class FlowRouterService:
    def __init__(self, app: FastAPI):
        self.app = app
        self.dynamic_routers: Dict[str, APIRouter] = {}

    def add_flow_route(self, flow: schemas.FlowRead):
        """Adds a new API endpoint to the application based on a flow."""
        endpoint = f"/flows/run/{flow.endpoint}"
        if endpoint in self.dynamic_routers:
            print(f"Route {endpoint} already exists. Skipping.")
            return

        router = APIRouter()

        @router.post(endpoint, tags=["Runnable Flows"], summary=flow.description)
        def execute_flow_endpoint(user_input: Dict[str, Any], db: Session = Depends(get_db)):
            # 여기서 flow_body를 직접 사용합니다.
            flow_definition = flow.flow_body.model_dump()
            
            # langflow 라이브러리를 사용하여 flow 실행
            try:
                result = run_flow_from_json(
                    flow_definition=flow_definition,
                    user_input=user_input
                )
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}

        self.app.include_router(router)
        self.dynamic_routers[endpoint] = router
        print(f"✅ Dynamically added route: POST {endpoint}")

    def remove_flow_route(self, flow_endpoint: str):
        """Removes an API endpoint from the application."""
        # FastAPI는 라우터 제거를 직접 지원하지 않습니다.
        # 대신, 해당 라우트를 비활성화하거나, 서버 재시작 시에만 라우트가 재구성되도록 합니다.
        # 여기서는 일단 비활성화 상태를 출력으로만 표시합니다.
        endpoint = f"/flows/run/{flow_endpoint}"
        if endpoint in self.dynamic_routers:
            # self.app.routes = [r for r in self.app.routes if r not in self.dynamic_routers[endpoint].routes]
            del self.dynamic_routers[endpoint]
            print(f"⚠️ Dynamically 'deactivated' route: {endpoint}. Full removal requires restart.")
        else:
            print(f"Route {endpoint} not found for removal.")

# 이 서비스는 main.py에서 app 객체와 함께 초기화되어야 합니다.
# flow_router_service = FlowRouterService(app)
