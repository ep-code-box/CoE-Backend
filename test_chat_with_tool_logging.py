#!/usr/bin/env python3
"""
도구 선택 로그가 대화 이력에 저장되는지 테스트하는 스크립트
"""

import asyncio
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_chat_with_tool_logging():
    """채팅 API를 통해 도구 선택 및 실행 로깅을 테스트합니다."""
    
    try:
        # 필요한 모듈들 import
        import sys
        sys.path.append('.')
        
        from core.database import init_database, get_db, SessionLocal
        from services.chat_service import get_chat_service
        from core.graph_builder import build_agent_graph
        from core.schemas import OpenAIChatRequest
        
        print("🔄 데이터베이스 초기화 중...")
        init_database()
        
        print("🔄 에이전트 그래프 빌드 중...")
        agent, tool_descriptions, agent_model_id = build_agent_graph()
        
        print(f"✅ 에이전트 준비 완료: {len(tool_descriptions)}개 도구 로드됨")
        
        # 테스트 세션 생성
        db = SessionLocal()
        chat_service = get_chat_service(db)
        
        session = chat_service.get_or_create_session(
            session_id="test-session-001",
            user_agent="Test Agent",
            ip_address="127.0.0.1"
        )
        
        print(f"✅ 테스트 세션 생성: {session.session_id}")
        
        # 테스트 메시지들
        test_messages = [
            "안녕하세요",  # sub_graph 도구가 선택될 것으로 예상
            "HELLO WORLD",  # tool1 (대문자 변환) 도구가 선택될 것으로 예상
            "1번 사용자 정보 알려줘",  # api_call 도구가 선택될 것으로 예상
        ]
        
        for i, user_message in enumerate(test_messages, 1):
            print(f"\n🧪 테스트 {i}: '{user_message}'")
            
            # 채팅 상태 준비
            state = {
                "messages": [{"role": "user", "content": user_message}],
                "_tool_context": {
                    "session_id": session.session_id,
                    "chat_service": chat_service,
                    "turn_number": i
                }
            }
            
            # 사용자 메시지 저장
            chat_service.save_chat_message(
                session_id=session.session_id,
                role="user",
                content=user_message,
                turn_number=i
            )
            
            try:
                # 에이전트 실행
                result = await agent.ainvoke(state)
                
                # 결과에서 어시스턴트 응답 추출
                assistant_message = None
                if "messages" in result:
                    for msg in reversed(result["messages"]):
                        if isinstance(msg, dict) and msg.get("role") == "assistant":
                            assistant_message = msg.get("content", "")
                            break
                
                if assistant_message:
                    # 어시스턴트 메시지 저장
                    chat_service.save_chat_message(
                        session_id=session.session_id,
                        role="assistant",
                        content=assistant_message,
                        turn_number=i
                    )
                    print(f"✅ 응답: {assistant_message[:100]}...")
                else:
                    print("⚠️ 어시스턴트 응답을 찾을 수 없음")
                
            except Exception as e:
                print(f"❌ 에이전트 실행 오류: {e}")
                continue
            
            # 세션 턴 수 업데이트
            chat_service.update_session_turns(session.session_id)
        
        # 대화 이력 조회 및 출력
        print(f"\n📊 대화 이력 조회 (세션: {session.session_id})")
        chat_history = chat_service.get_chat_history(session.session_id, limit=50)
        
        print(f"총 {len(chat_history)}개의 메시지:")
        for msg in chat_history:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            tool_info = f" [도구: {msg.selected_tool}]" if msg.selected_tool else ""
            execution_time = f" ({msg.tool_execution_time_ms}ms)" if msg.tool_execution_time_ms else ""
            success_info = f" {'✅' if msg.tool_success else '❌'}" if msg.tool_success is not None else ""
            
            print(f"  [{timestamp}] {msg.role}: {msg.content[:80]}...{tool_info}{execution_time}{success_info}")
        
        # 대화 요약 생성
        print(f"\n📝 대화 요약 생성 중...")
        summary = chat_service.create_conversation_summary(session.session_id)
        print(f"요약: {summary.summary_content}")
        if summary.tools_used:
            print("사용된 도구 통계:")
            for tool_name, stats in summary.tools_used.items():
                success_rate = (stats['success_count'] / stats['count']) * 100 if stats['count'] > 0 else 0
                avg_time = stats['total_execution_time_ms'] / stats['count'] if stats['count'] > 0 else 0
                print(f"  - {tool_name}: {stats['count']}회 사용, 성공률 {success_rate:.1f}%, 평균 실행시간 {avg_time:.0f}ms")
        
        db.close()
        print("\n✅ 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat_with_tool_logging())