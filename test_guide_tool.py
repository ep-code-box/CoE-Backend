#!/usr/bin/env python3

"""
가이드 추출 도구 테스트 스크립트
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tool_loading():
    """도구 로딩 테스트"""
    try:
        from tools.registry import load_all_tools
        nodes, descriptions, edges = load_all_tools()
        
        print("=== 로드된 도구들 ===")
        for desc in descriptions:
            print(f"- {desc['name']}: {desc['description']}")
        
        print(f"\n총 {len(descriptions)}개의 도구가 로드되었습니다.")
        
        # guide_extraction 도구가 포함되었는지 확인
        guide_tool = next((desc for desc in descriptions if desc['name'] == 'guide_extraction'), None)
        if guide_tool:
            print(f"\n✅ guide_extraction 도구가 성공적으로 로드되었습니다!")
            print(f"설명: {guide_tool['description']}")
        else:
            print(f"\n❌ guide_extraction 도구를 찾을 수 없습니다.")
            
        return True
        
    except Exception as e:
        print(f"도구 로딩 중 오류 발생: {e}")
        return False

def test_guide_extraction_function():
    """가이드 추출 함수 테스트"""
    try:
        from tools.guide_extraction_tool import guide_extraction_node
        from schemas import ChatState
        
        # 테스트 상태 생성
        test_state = ChatState({
            "original_input": "이 프로젝트의 개발 가이드를 추출해줘",
            "messages": []
        })
        
        print("\n=== 가이드 추출 함수 테스트 ===")
        print("테스트 입력:", test_state.get("original_input"))
        
        # 함수 실행 (실제 RAG Pipeline 연결 없이)
        result = guide_extraction_node(test_state)
        
        print("함수 실행 결과:")
        if "messages" in result:
            for msg in result["messages"]:
                print(f"- {msg['role']}: {msg['content'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"가이드 추출 함수 테스트 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    print("🧪 가이드 추출 도구 테스트 시작\n")
    
    # 1. 도구 로딩 테스트
    if test_tool_loading():
        print("\n" + "="*50)
        
        # 2. 함수 테스트
        test_guide_extraction_function()
    
    print("\n🏁 테스트 완료")