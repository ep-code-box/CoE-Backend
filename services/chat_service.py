"""
채팅 관련 비즈니스 로직을 담당하는 서비스 모듈입니다.
대화 이력 저장, 세션 관리, 도구 실행 정보 추적 등을 처리합니다.
"""

import uuid
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.database import ChatMessage, ConversationSummary, APILog, redis_client

logger = logging.getLogger(__name__)


class ChatService:
    """채팅 관련 서비스 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_session(self, session_id: Optional[str] = None, 
                            user_agent: Optional[str] = None, 
                            ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        세션을 가져오거나 새로 생성합니다. Redis를 사용합니다.
        
        Args:
            session_id: 세션 ID (없으면 새로 생성)
            user_agent: 사용자 에이전트
            ip_address: IP 주소
            
        Returns:
            Dict[str, Any]: 세션 데이터 딕셔너리
        """
        if session_id:
            session_data_str = redis_client.get(f"chat_session:{session_id}")
            if session_data_str:
                session_data = json.loads(session_data_str)
                # 마지막 활동 시간 업데이트
                session_data["last_activity"] = datetime.utcnow().isoformat()
                redis_client.set(f"chat_session:{session_id}", json.dumps(session_data))
                return session_data
        
        # 새 세션 생성
        new_session_id = session_id or str(uuid.uuid4())
        session_data = {
            "session_id": new_session_id,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "conversation_turns": 0,
            "max_turns": 3,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        redis_client.set(f"chat_session:{new_session_id}", json.dumps(session_data))
        
        logger.info(f"새 세션 생성: {new_session_id}")
        return session_data
    
    def save_chat_message(self, session_id: str, role: str, content: str, 
                         turn_number: int, selected_tool: Optional[str] = None,
                         tool_execution_time_ms: Optional[int] = None,
                         tool_success: Optional[bool] = None,
                         tool_metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        """
        채팅 메시지를 저장합니다.
        
        Args:
            session_id: 세션 ID
            role: 메시지 역할 (user, assistant, system)
            content: 메시지 내용
            turn_number: 턴 번호
            selected_tool: 선택된 도구명
            tool_execution_time_ms: 도구 실행 시간 (밀리초)
            tool_success: 도구 실행 성공 여부
            tool_metadata: 도구 관련 메타데이터
            
        Returns:
            ChatMessage: 저장된 메시지 객체
        """
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            turn_number=turn_number,
            selected_tool=selected_tool,
            tool_execution_time_ms=tool_execution_time_ms,
            tool_success=tool_success,
            tool_metadata=tool_metadata
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        logger.info(f"메시지 저장: session={session_id}, role={role}, tool={selected_tool}")
        return message
    
    def get_chat_history(self, session_id: str, limit: int = 10) -> List[ChatMessage]:
        """
        채팅 이력을 조회합니다.
        
        Args:
            session_id: 세션 ID
            limit: 조회할 메시지 수
            
        Returns:
            List[ChatMessage]: 메시지 목록 (최신순)
        """
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(desc(ChatMessage.timestamp)).limit(limit).all()
        
        return list(reversed(messages))  # 시간순으로 정렬
    
    def update_session_turns(self, session_id: str) -> Dict[str, Any]:
        """
        세션의 대화 턴 수를 업데이트합니다. Redis를 사용합니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Dict[str, Any]: 업데이트된 세션 데이터 딕셔너리
        """
        session_data_str = redis_client.get(f"chat_session:{session_id}")
        if session_data_str:
            session_data = json.loads(session_data_str)
            session_data["conversation_turns"] += 1
            session_data["last_activity"] = datetime.utcnow().isoformat()
            
            # 최대 턴 수 초과 시 세션 비활성화
            if session_data["conversation_turns"] >= session_data["max_turns"]:
                session_data["is_active"] = False
                logger.info(f"세션 {session_id} 최대 턴 수 도달로 비활성화")
            
            redis_client.set(f"chat_session:{session_id}", json.dumps(session_data))
            return session_data
        return {} # 세션을 찾을 수 없는 경우 빈 딕셔너리 반환
    
    def log_api_call(self, session_id: str, endpoint: str, method: str,
                    request_data: Optional[Dict] = None, response_status: Optional[int] = None,
                    response_time_ms: Optional[int] = None, error_message: Optional[str] = None,
                    selected_tool: Optional[str] = None, tool_execution_time_ms: Optional[int] = None,
                    tool_success: Optional[bool] = None, tool_error_message: Optional[str] = None) -> APILog:
        """
        API 호출을 로깅합니다.
        
        Args:
            session_id: 세션 ID
            endpoint: API 엔드포인트
            method: HTTP 메소드
            request_data: 요청 데이터
            response_status: 응답 상태 코드
            response_time_ms: 응답 시간 (밀리초)
            error_message: 오류 메시지
            selected_tool: 선택된 도구명
            tool_execution_time_ms: 도구 실행 시간 (밀리초)
            tool_success: 도구 실행 성공 여부
            tool_error_message: 도구 실행 오류 메시지
            
        Returns:
            APILog: 저장된 로그 객체
        """
        from core.database import HTTPMethod
        
        # HTTPMethod enum으로 변환
        http_method = getattr(HTTPMethod, method.upper(), HTTPMethod.GET)
        
        api_log = APILog(
            session_id=session_id,
            endpoint=endpoint,
            method=http_method,
            request_data=request_data,
            response_status=response_status,
            response_time_ms=response_time_ms,
            error_message=error_message,
            selected_tool=selected_tool,
            tool_execution_time_ms=tool_execution_time_ms,
            tool_success=tool_success,
            tool_error_message=tool_error_message
        )
        
        self.db.add(api_log)
        self.db.commit()
        self.db.refresh(api_log)
        
        return api_log
    
    def create_conversation_summary(self, session_id: str) -> ConversationSummary:
        """
        대화 요약을 생성합니다.
        
        Args:
            session_id: 세션 ID
            
        Returns:
            ConversationSummary: 생성된 요약 객체
        """
        # 해당 세션의 모든 메시지 조회
        messages = self.get_chat_history(session_id, limit=100)
        
        # 사용된 도구들 통계 생성
        tools_used = {}
        for message in messages:
            if message.selected_tool:
                tool_name = message.selected_tool
                if tool_name not in tools_used:
                    tools_used[tool_name] = {
                        'count': 0,
                        'success_count': 0,
                        'total_execution_time_ms': 0
                    }
                
                tools_used[tool_name]['count'] += 1
                if message.tool_success:
                    tools_used[tool_name]['success_count'] += 1
                if message.tool_execution_time_ms:
                    tools_used[tool_name]['total_execution_time_ms'] += message.tool_execution_time_ms
        
        # 요약 내용 생성
        summary_content = f"총 {len(messages)}개의 메시지, {len(tools_used)}개의 도구 사용"
        if tools_used:
            summary_content += f"\n사용된 도구: {', '.join(tools_used.keys())}"
        
        summary = ConversationSummary(
            session_id=session_id,
            summary_content=summary_content,
            total_turns=len([m for m in messages if m.role == 'user']),
            tools_used=tools_used
        )
        
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        
        logger.info(f"대화 요약 생성: session={session_id}, tools={len(tools_used)}")
        return summary


def get_chat_service(db: Session) -> ChatService:
    """ChatService 인스턴스를 반환합니다."""
    return ChatService(db)