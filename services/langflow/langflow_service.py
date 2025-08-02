"""
LangFlow 실행 서비스
실제 LangFlow 엔진과 연동하여 플로우를 실행합니다.
"""

import os
import time
import json
import httpx
import aiohttp
from typing import Dict, Any, Optional
from core.schemas import ExecuteFlowResponse
from core.database import SessionLocal
from services.db_service import LangFlowService


class LangFlowExecutionService:
    """LangFlow 실행을 담당하는 서비스 클래스"""
    
    def __init__(self, langflow_url: str = None):
        """
        LangFlow 서비스 초기화
        
        Args:
            langflow_url: LangFlow 서버 URL (기본값: 환경변수 LANGFLOW_URL 또는 http://localhost:7860)
        """
        self.langflow_url = langflow_url or os.getenv("LANGFLOW_URL", "http://localhost:7860")
        self.api_key = os.getenv("LANGFLOW_API_KEY")  # 선택적 API 키
        
    async def execute_flow_by_name(
        self, 
        flow_name: str, 
        inputs: Optional[Dict[str, Any]] = None,
        tweaks: Optional[Dict[str, Any]] = None
    ) -> ExecuteFlowResponse:
        """
        저장된 플로우 이름으로 LangFlow 실행
        
        Args:
            flow_name: 실행할 플로우 이름
            inputs: 플로우 입력 데이터
            tweaks: 플로우 파라미터 조정
            
        Returns:
            ExecuteFlowResponse: 실행 결과
        """
        start_time = time.time()
        
        try:
            # 데이터베이스에서 플로우 조회
            db = SessionLocal()
            try:
                db_flow = LangFlowService.get_flow_by_name(db, flow_name)
                if not db_flow:
                    return ExecuteFlowResponse(
                        success=False,
                        error=f"Flow '{flow_name}' not found in database"
                    )
                
                # 플로우 데이터 파싱
                flow_data = json.loads(db_flow.flow_data)
                flow_id = flow_data.get("id")
                
                if not flow_id:
                    return ExecuteFlowResponse(
                        success=False,
                        error=f"Flow '{flow_name}' does not have a valid flow ID"
                    )
                
            finally:
                db.close()
            
            # LangFlow API로 실행
            result = await self.execute_flow_by_id(flow_id, inputs, tweaks)
            result.execution_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            return ExecuteFlowResponse(
                success=False,
                error=f"Error executing flow '{flow_name}': {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def execute_flow_by_id(
        self, 
        flow_id: str, 
        inputs: Optional[Dict[str, Any]] = None,
        tweaks: Optional[Dict[str, Any]] = None
    ) -> ExecuteFlowResponse:
        """
        플로우 ID로 LangFlow 실행
        
        Args:
            flow_id: LangFlow 플로우 ID
            inputs: 플로우 입력 데이터
            tweaks: 플로우 파라미터 조정
            
        Returns:
            ExecuteFlowResponse: 실행 결과
        """
        start_time = time.time()
        
        try:
            # API 엔드포인트 구성
            url = f"{self.langflow_url}/api/v1/run/{flow_id}"
            
            # 요청 데이터 구성
            payload = {}
            if inputs:
                payload["input_value"] = inputs.get("input_value", "")
                payload["inputs"] = inputs
            if tweaks:
                payload["tweaks"] = tweaks
            
            # HTTP 헤더 구성
            headers = {
                "Content-Type": "application/json"
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # HTTP 요청 실행
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    result_data = response.json()
                    
                    return ExecuteFlowResponse(
                        success=True,
                        session_id=result_data.get("session_id"),
                        outputs=result_data.get("outputs", {}),
                        execution_time=time.time() - start_time
                    )
                else:
                    error_msg = f"LangFlow API error: {response.status_code} - {response.text}"
                    return ExecuteFlowResponse(
                        success=False,
                        error=error_msg,
                        execution_time=time.time() - start_time
                    )
                    
        except httpx.TimeoutException:
            return ExecuteFlowResponse(
                success=False,
                error="LangFlow execution timeout",
                execution_time=time.time() - start_time
            )
        except httpx.ConnectError:
            return ExecuteFlowResponse(
                success=False,
                error=f"Cannot connect to LangFlow server at {self.langflow_url}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ExecuteFlowResponse(
                success=False,
                error=f"Unexpected error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def check_langflow_health(self) -> bool:
        """
        LangFlow 서버 상태 확인
        
        Returns:
            bool: 서버가 정상 동작하면 True
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.langflow_url}/health")
                return response.status_code == 200
        except:
            return False
    
    def get_langflow_url(self) -> str:
        """현재 설정된 LangFlow URL 반환"""
        return self.langflow_url


# 전역 서비스 인스턴스
langflow_service = LangFlowExecutionService()