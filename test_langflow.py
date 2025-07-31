#!/usr/bin/env python3
"""
LangFlow 기능 테스트 스크립트
"""
import json
import requests
import time

BASE_URL = "http://localhost:8000"

def test_save_flow():
    """플로우 저장 테스트"""
    print("🧪 플로우 저장 테스트...")
    
    # 샘플 LangFlow JSON 데이터
    sample_flow = {
        "description": "간단한 채팅 플로우",
        "name": "simple_chat",
        "id": "test_flow_001",
        "data": {
            "nodes": [
                {
                    "id": "input_1",
                    "type": "ChatInput",
                    "position": {"x": 100, "y": 100},
                    "data": {
                        "input_value": "",
                        "sender": "User",
                        "sender_name": "User",
                        "session_id": "",
                        "should_store_message": True
                    }
                },
                {
                    "id": "llm_1", 
                    "type": "ChatOpenAI",
                    "position": {"x": 300, "y": 100},
                    "data": {
                        "model": "gpt-3.5-turbo",
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                },
                {
                    "id": "output_1",
                    "type": "ChatOutput", 
                    "position": {"x": 500, "y": 100},
                    "data": {
                        "data_template": "{text}",
                        "input_value": "",
                        "sender": "AI",
                        "sender_name": "AI",
                        "session_id": "",
                        "should_store_message": True
                    }
                }
            ],
            "edges": [
                {
                    "id": "edge_1",
                    "source": "input_1",
                    "target": "llm_1",
                    "sourceHandle": "output",
                    "targetHandle": "input"
                },
                {
                    "id": "edge_2", 
                    "source": "llm_1",
                    "target": "output_1",
                    "sourceHandle": "output",
                    "targetHandle": "input"
                }
            ],
            "viewport": {"x": 0, "y": 0, "zoom": 1}
        },
        "is_component": False
    }
    
    payload = {
        "name": "테스트플로우",
        "flow_data": sample_flow,
        "description": "LangFlow 기능 테스트용 플로우"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/flows/save", json=payload)
        if response.status_code == 200:
            print("✅ 플로우 저장 성공!")
            print(f"   응답: {response.json()}")
            return True
        else:
            print(f"❌ 플로우 저장 실패: {response.status_code}")
            print(f"   오류: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 플로우 저장 중 예외 발생: {e}")
        return False

def test_list_flows():
    """플로우 목록 조회 테스트"""
    print("\n🧪 플로우 목록 조회 테스트...")
    
    try:
        response = requests.get(f"{BASE_URL}/flows/list")
        if response.status_code == 200:
            print("✅ 플로우 목록 조회 성공!")
            flows = response.json()["flows"]
            print(f"   저장된 플로우 수: {len(flows)}")
            for flow in flows:
                print(f"   - {flow['name']}: {flow['description']}")
            return True
        else:
            print(f"❌ 플로우 목록 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 플로우 목록 조회 중 예외 발생: {e}")
        return False

def test_get_flow():
    """특정 플로우 조회 테스트"""
    print("\n🧪 특정 플로우 조회 테스트...")
    
    try:
        response = requests.get(f"{BASE_URL}/flows/테스트플로우")
        if response.status_code == 200:
            print("✅ 플로우 조회 성공!")
            flow_data = response.json()
            print(f"   플로우 이름: {flow_data.get('saved_name')}")
            print(f"   노드 수: {len(flow_data.get('data', {}).get('nodes', []))}")
            return True
        else:
            print(f"❌ 플로우 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 플로우 조회 중 예외 발생: {e}")
        return False

def test_chat_langflow_list():
    """채팅을 통한 LangFlow 목록 조회 테스트"""
    print("\n🧪 채팅을 통한 LangFlow 목록 조회 테스트...")
    
    payload = {
        "messages": [
            {"role": "user", "content": "저장된 langflow 목록을 보여주세요"}
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        if response.status_code == 200:
            print("✅ 채팅 응답 성공!")
            messages = response.json()["messages"]
            for msg in messages:
                if msg["role"] == "assistant":
                    print(f"   AI 응답: {msg['content'][:200]}...")
            return True
        else:
            print(f"❌ 채팅 응답 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 채팅 중 예외 발생: {e}")
        return False

def test_chat_langflow_execute():
    """채팅을 통한 LangFlow 실행 테스트"""
    print("\n🧪 채팅을 통한 LangFlow 실행 테스트...")
    
    payload = {
        "messages": [
            {"role": "user", "content": "테스트플로우 실행해주세요"}
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        if response.status_code == 200:
            print("✅ 채팅 응답 성공!")
            messages = response.json()["messages"]
            for msg in messages:
                if msg["role"] == "assistant":
                    print(f"   AI 응답: {msg['content'][:300]}...")
            return True
        else:
            print(f"❌ 채팅 응답 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 채팅 중 예외 발생: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 LangFlow 기능 테스트 시작\n")
    
    # 서버가 실행 중인지 확인
    try:
        response = requests.get(f"{BASE_URL}/v1/models", timeout=5)
        if response.status_code != 200:
            print("❌ 서버가 실행되지 않았습니다. python3 main.py로 서버를 먼저 시작하세요.")
            return
    except Exception:
        print("❌ 서버에 연결할 수 없습니다. python3 main.py로 서버를 먼저 시작하세요.")
        return
    
    print("✅ 서버 연결 확인됨\n")
    
    # 테스트 실행
    tests = [
        test_save_flow,
        test_list_flows, 
        test_get_flow,
        test_chat_langflow_list,
        test_chat_langflow_execute
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        time.sleep(1)  # 테스트 간 간격
    
    print(f"\n📊 테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️  일부 테스트가 실패했습니다.")

if __name__ == "__main__":
    main()