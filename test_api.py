#!/usr/bin/env python3
"""API 엔드포인트 테스트 스크립트"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_db_tables():
    """DB 테이블 정보 조회 테스트"""
    print("=== DB 테이블 정보 조회 테스트 ===")
    try:
        response = requests.get(f"{BASE_URL}/db/tables")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 테이블 정보 조회 성공: {len(data['tables'])}개 테이블")
            for table in data['tables']:
                print(f"   - {table['table_name']}: {table['row_count']}행")
        else:
            print(f"❌ 테이블 정보 조회 실패: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 테이블 정보 조회 오류: {e}")

def test_save_flow():
    """LangFlow 저장 테스트"""
    print("\n=== LangFlow 저장 테스트 ===")
    try:
        flow_data = {
            "name": "api_test_flow",
            "description": "API 테스트용 플로우",
            "flow_data": {
                "name": "api_test_flow",
                "id": "api_test_flow_id",
                "description": "API 테스트용 플로우",
                "data": {
                    "nodes": [
                        {
                            "id": "1", 
                            "type": "input", 
                            "position": {"x": 100, "y": 100},
                            "data": {"label": "Input Node"}
                        },
                        {
                            "id": "2", 
                            "type": "llm", 
                            "position": {"x": 300, "y": 100},
                            "data": {"label": "LLM Node"}
                        },
                        {
                            "id": "3", 
                            "type": "output", 
                            "position": {"x": 500, "y": 100},
                            "data": {"label": "Output Node"}
                        }
                    ],
                    "edges": [
                        {"id": "e1", "source": "1", "target": "2"},
                        {"id": "e2", "source": "2", "target": "3"}
                    ]
                }
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/flows/save",
            json=flow_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 플로우 저장 성공: ID={data.get('id')}, Name={data.get('name')}")
            return data.get('name')
        else:
            print(f"❌ 플로우 저장 실패: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ 플로우 저장 오류: {e}")
        return None

def test_list_flows():
    """LangFlow 목록 조회 테스트"""
    print("\n=== LangFlow 목록 조회 테스트 ===")
    try:
        response = requests.get(f"{BASE_URL}/flows/list")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 플로우 목록 조회 성공: {len(data['flows'])}개 플로우")
            for flow in data['flows']:
                print(f"   - {flow['name']}: {flow['description']}")
        else:
            print(f"❌ 플로우 목록 조회 실패: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 플로우 목록 조회 오류: {e}")

def test_get_flow(flow_name):
    """특정 LangFlow 조회 테스트"""
    print(f"\n=== LangFlow '{flow_name}' 조회 테스트 ===")
    try:
        response = requests.get(f"{BASE_URL}/flows/{flow_name}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 플로우 조회 성공: {data.get('name')}")
            print(f"   - 설명: {data.get('description')}")
            print(f"   - 노드 수: {len(data.get('data', {}).get('nodes', []))}")
        else:
            print(f"❌ 플로우 조회 실패: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 플로우 조회 오류: {e}")

def test_delete_flow(flow_name):
    """LangFlow 삭제 테스트"""
    print(f"\n=== LangFlow '{flow_name}' 삭제 테스트 ===")
    try:
        response = requests.delete(f"{BASE_URL}/flows/{flow_name}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 플로우 삭제 성공: {data.get('message')}")
        else:
            print(f"❌ 플로우 삭제 실패: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 플로우 삭제 오류: {e}")

def test_db_query():
    """DB 쿼리 실행 테스트"""
    print("\n=== DB 쿼리 실행 테스트 ===")
    try:
        query_data = {
            "query": "SELECT COUNT(*) as total_flows FROM langflows WHERE is_active = 1"
        }
        
        response = requests.post(
            f"{BASE_URL}/db/query",
            json=query_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 쿼리 실행 성공: {data}")
        else:
            print(f"❌ 쿼리 실행 실패: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 쿼리 실행 오류: {e}")

def main():
    """메인 테스트 함수"""
    print("🧪 CoE 백엔드 API 테스트 시작\n")
    
    # 1. DB 테이블 정보 조회
    test_db_tables()
    
    # 2. LangFlow 저장
    flow_name = test_save_flow()
    
    # 3. LangFlow 목록 조회
    test_list_flows()
    
    # 4. 특정 LangFlow 조회
    if flow_name:
        test_get_flow(flow_name)
    
    # 5. DB 쿼리 실행
    test_db_query()
    
    # 6. LangFlow 삭제
    if flow_name:
        test_delete_flow(flow_name)
    
    print("\n🎉 API 테스트 완료!")

if __name__ == "__main__":
    main()