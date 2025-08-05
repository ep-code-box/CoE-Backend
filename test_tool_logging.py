#!/usr/bin/env python3
"""
도구 로깅 기능을 테스트하는 스크립트입니다.
"""

import requests
import json
import time

def test_tool_logging():
    """도구 로깅 기능을 테스트합니다."""
    
    base_url = "http://localhost:8000"
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "기본 인사",
            "message": "안녕하세요"
        },
        {
            "name": "API 호출 요청",
            "message": "https://api.github.com/users/octocat 이 URL을 호출해주세요"
        },
        {
            "name": "코드 생성 요청", 
            "message": "Python으로 Hello World를 출력하는 코드를 작성해주세요"
        },
        {
            "name": "대화 종료",
            "message": "대화를 끝내고 싶습니다"
        }
    ]
    
    print("🧪 도구 로깅 기능 테스트 시작")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 테스트 {i}: {test_case['name']}")
        print(f"입력: {test_case['message']}")
        print("-" * 30)
        
        # API 요청
        payload = {
            "model": "coe-agent-v1",
            "messages": [{"role": "user", "content": test_case['message']}],
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    print(f"✅ 응답: {content[:100]}{'...' if len(content) > 100 else ''}")
                else:
                    print(f"⚠️  응답 형식 오류: {result}")
            else:
                print(f"❌ HTTP 오류: {response.status_code}")
                print(f"응답: {response.text}")
                
        except requests.exceptions.Timeout:
            print("⏰ 요청 타임아웃")
        except requests.exceptions.RequestException as e:
            print(f"🚨 요청 오류: {e}")
        
        # 다음 테스트 전 잠시 대기
        if i < len(test_cases):
            time.sleep(2)
    
    print("\n" + "=" * 50)
    print("🏁 테스트 완료")
    print("\n📋 로그 확인 방법:")
    print("1. 서버 콘솔에서 '🔧 TOOL_TRACKER' 로그 확인")
    print("2. 'TOOL_SELECTED', 'TOOL_EXECUTION_START', 'TOOL_EXECUTION_COMPLETE' 메시지 확인")
    print("3. 각 도구의 실행 시간도 함께 기록됨")

if __name__ == "__main__":
    test_tool_logging()