"""
LangFlow 실행 서비스
외부 LangFlow 서버의 API를 호출하여 플로우를 실행합니다.
"""

import os
import time
import httpx
from typing import Dict, Any, Optional
from core.schemas import ExecuteFlowResponse
from services.db_service import LangFlowService, SessionLocal

class LangFlowExecutionService:
    """LangFlow 실행을 담당하는 서비스 클래스 (API 기반)"""
    
    def __init__(self, langflow_url: str = None, api_key: str = None):
        """
        LangFlow 서비스 초기화
        """
        self.base_url = langflow_url or os.getenv("LANGFLOW_URL", "http://localhost:7860")
        self.api_key = api_key or os.getenv("LANGFLOW_API_KEY")
        self.headers = {"x-api-key": self.api_key} if self.api_key else {}
        
    async def execute_flow(
        self, 
        flow_id_or_name: str, 
        inputs: Optional[Dict[str, Any]] = None,
        tweaks: Optional[Dict[str, Any]] = None
    ) -> ExecuteFlowResponse:
        """
        지정된 ID 또는 이름으로 LangFlow를 API를 통해 실행합니다.
        
        Args:
            flow_id_or_name: 실행할 플로우의 ID 또는 이름
            inputs: 플로우 입력 데이터
            tweaks: 플로우 파라미터 조정
            
        Returns:
            ExecuteFlowResponse: 실행 결과
        """
        start_time = time.time()
        request_body = {
            "input_value": inputs.get("input_value", ""),
            "tweaks": tweaks or {}
        }
        
        # LangFlow는 chat_history, session_id 등을 지원합니다.
        # 필요에 따라 inputs에서 다른 키들을 추출하여 request_body에 추가할 수 있습니다.
        if inputs:
            for key in ["chat_history", "session_id"]:
                if key in inputs:
                    request_body[key] = inputs[key]

        endpoint = f"/api/v1/run/{flow_id_or_name}"
        url = f"{self.base_url.rstrip('/')}{endpoint}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=request_body,
                    timeout=300  # 5분 타임아웃
                )
                response.raise_for_status()  # 오류 발생 시 예외 처리
                
                result_data = response.json()
                # LangFlow의 실제 응답 구조에 따라 결과 파싱이 필요할 수 있습니다.
                # 예: result_data.get('outputs', [{}])[0].get('results', {})
                outputs = result_data.get("outputs", [{}])[0]

                return ExecuteFlowResponse(
                    success=True,
                    session_id=result_data.get("session_id", f"api-{int(time.time())}"),
                    outputs=outputs,
                    execution_time=time.time() - start_time
                )

        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            return ExecuteFlowResponse(success=False, error=error_detail, execution_time=time.time() - start_time)
        except Exception as e:
            return ExecuteFlowResponse(success=False, error=str(e), execution_time=time.time() - start_time)

    # execute_flow_by_name 및 execute_flow_by_id는 execute_flow를 호출하도록 단순화합니다.
    async def execute_flow_by_name(self, *args, **kwargs) -> ExecuteFlowResponse:
        return await self.execute_flow(*args, **kwargs)

    async def execute_flow_by_id(self, *args, **kwargs) -> ExecuteFlowResponse:
        return await self.execute_flow(*args, **kwargs)

    async def check_langflow_health(self) -> bool:
        """LangFlow 서버의 상태를 확인합니다."""
        try:
            async with httpx.AsyncClient() as client:
                # LangFlow는 별도의 health 엔드포인트가 없을 수 있으므로, 기본 URL로 확인
                response = await client.get(self.base_url, timeout=10)
                return response.status_code == 200
        except Exception:
            return False

    def get_langflow_url(self) -> str:
        """현재 설정된 LangFlow URL을 반환합니다."""
        return self.base_url

# 전역 서비스 인스턴스
langflow_service = LangFlowExecutionService()
