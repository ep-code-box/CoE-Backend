from fastapi import FastAPI, APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from core import schemas
from core.database import get_db
from services.langflow.langflow_service import langflow_service

logger = logging.getLogger(__name__)

class FlowRouterService:
    def __init__(self, app: FastAPI):
        self.app = app
        self.dynamic_routers: Dict[str, APIRouter] = {}

    def add_flow_route(self, flow: schemas.FlowRead):
        """Adds a new API endpoint to the application based on a flow."""
        # /flows/run/ 대신 더 직접적인 /run/ 경로 사용
        endpoint = f"/run/{flow.endpoint}"
        if endpoint in self.dynamic_routers:
            logger.info(f"Route {endpoint} already exists. Skipping.")
            return

        router = APIRouter()

        @router.post(endpoint, tags=["Runnable Flows"], summary=flow.description)
        async def execute_flow_endpoint(user_input: Dict[str, Any], db: Session = Depends(get_db)):
            # 여기서 flow_body를 직접 사용합니다.
            flow_definition = flow.flow_body.model_dump() if hasattr(flow.flow_body, 'model_dump') else flow.flow_body
            
            # langflow 라이브러리를 사용하여 flow 실행
            try:
                # inputs는 {'input_value': '...'} 형식이거나 직접적인 딕셔너리일 수 있음
                # langflow_service.execute_flow는 내부적으로 이를 처리함
                execution_result = await langflow_service.execute_flow(
                    flow_data=flow_definition,
                    inputs=user_input
                )
                
                if execution_result.success:
                    return {
                        "success": True, 
                        "result": execution_result.outputs,
                        "session_id": execution_result.session_id,
                        "execution_time": execution_result.execution_time
                    }
                else:
                    return {"success": False, "error": execution_result.error}
            except Exception as e:
                logger.error(f"Error executing dynamic flow '{flow.endpoint}': {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        self.app.include_router(router)
        self.dynamic_routers[endpoint] = router
        
        # OpenAPI 스키마 초기화 (새로운 라우트 반영을 위해)
        self.app.openapi_schema = None
        
        logger.info(f"✅ Dynamically added route: POST {endpoint}")

    def remove_flow_route(self, flow_endpoint: str):
        """Removes an API endpoint from the application."""
        endpoint = f"/run/{flow_endpoint}"
        if endpoint in self.dynamic_routers:
            del self.dynamic_routers[endpoint]
            self.app.openapi_schema = None
            logger.info(f"⚠️ Dynamically 'deactivated' route: {endpoint}. Full removal requires restart.")
        else:
            logger.warning(f"Route {endpoint} not found for removal.")

# 이 서비스는 main.py에서 app 객체와 함께 초기화되어야 합니다.
# flow_router_service = FlowRouterService(app)
