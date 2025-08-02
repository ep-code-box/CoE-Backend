#!/usr/bin/env python3
"""
LangFlow API 엔드포인트 테스트 스크립트
"""

import requests
import json
import time
from typing import Dict, Any


class LangFlowAPITester:
    """LangFlow API 테스트 클래스"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_health_check(self) -> bool:
        """LangFlow 서버 상태 확인 테스트"""
        print("🔍 LangFlow 서버 상태 확인 중...")
        
        try:
            response = self.session.get(f"{self.base_url}/flows/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 상태 확인 성공:")
                print(f"   - LangFlow URL: {data.get('langflow_url')}")
                print(f"   - 연결 상태: {data.get('status')}")
                print(f"   - 건강 상태: {data.get('is_healthy')}")
                return data.get('is_healthy', False)
            else:
                print(f"❌ 상태 확인 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 상태 확인 중 오류: {str(e)}")
            return False
    
    def test_list_flows(self) -> list:
        """저장된 플로우 목록 조회 테스트"""
        print("\n📋 저장된 플로우 목록 조회 중...")
        
        try:
            response = self.session.get(f"{self.base_url}/flows/list")
            
            if response.status_code == 200:
                data = response.json()
                flows = data.get('flows', [])
                print(f"✅ 플로우 목록 조회 성공: {len(flows)}개 플로우 발견")
                
                for i, flow in enumerate(flows, 1):
                    print(f"   {i}. {flow.get('name')} (ID: {flow.get('id')})")
                    print(f"      설명: {flow.get('description', '없음')}")
                
                return flows
            else:
                print(f"❌ 플로우 목록 조회 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 플로우 목록 조회 중 오류: {str(e)}")
            return []
    
    def test_save_sample_flow(self) -> bool:
        """샘플 플로우 저장 테스트"""
        print("\n💾 샘플 플로우 저장 중...")
        
        sample_flow = {
            "name": "test_flow_api",
            "description": "API 테스트용 샘플 플로우",
            "flow_data": {
                "description": "Simple test flow",
                "name": "test_flow_api",
                "id": "test-flow-api-001",
                "data": {
                    "nodes": [
                        {
                            "id": "input-1",
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
                            "id": "output-1", 
                            "type": "ChatOutput",
                            "position": {"x": 400, "y": 100},
                            "data": {
                                "input_value": "",
                                "sender": "Machine",
                                "sender_name": "AI",
                                "session_id": "",
                                "data_template": "{text}",
                                "should_store_message": True
                            }
                        }
                    ],
                    "edges": [
                        {
                            "id": "edge-1",
                            "source": "input-1",
                            "target": "output-1",
                            "sourceHandle": "text",
                            "targetHandle": "input_value"
                        }
                    ]
                },
                "is_component": False
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/flows/save",
                json=sample_flow,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 샘플 플로우 저장 성공:")
                print(f"   - ID: {data.get('id')}")
                print(f"   - 파일명: {data.get('filename')}")
                return True
            else:
                print(f"❌ 샘플 플로우 저장 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 샘플 플로우 저장 중 오류: {str(e)}")
            return False
    
    def test_execute_flow(self, flow_name: str = "test_flow_api") -> bool:
        """플로우 실행 테스트"""
        print(f"\n🚀 플로우 '{flow_name}' 실행 중...")
        
        execute_request = {
            "flow_name": flow_name,
            "inputs": {
                "input_value": "안녕하세요! 이것은 API 테스트입니다.",
                "message": "테스트 메시지"
            },
            "tweaks": {}
        }
        
        try:
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/flows/execute",
                json=execute_request,
                headers={"Content-Type": "application/json"}
            )
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 플로우 실행 완료 (소요시간: {execution_time:.2f}초):")
                print(f"   - 성공 여부: {data.get('success')}")
                print(f"   - 세션 ID: {data.get('session_id')}")
                print(f"   - 실행 시간: {data.get('execution_time', 0):.2f}초")
                
                if data.get('success'):
                    outputs = data.get('outputs', {})
                    if outputs:
                        print(f"   - 출력 결과:")
                        print(f"     {json.dumps(outputs, indent=6, ensure_ascii=False)}")
                    else:
                        print(f"   - 출력 결과: 없음")
                else:
                    print(f"   - 오류: {data.get('error')}")
                
                return data.get('success', False)
            else:
                print(f"❌ 플로우 실행 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 플로우 실행 중 오류: {str(e)}")
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🧪 LangFlow API 테스트 시작\n" + "="*50)
        
        # 1. 서버 상태 확인
        health_ok = self.test_health_check()
        
        # 2. 기존 플로우 목록 확인
        flows = self.test_list_flows()
        
        # 3. 샘플 플로우 저장 (기존에 없는 경우)
        flow_exists = any(flow.get('name') == 'test_flow_api' for flow in flows)
        if not flow_exists:
            save_ok = self.test_save_sample_flow()
        else:
            print("\n💾 샘플 플로우가 이미 존재합니다.")
            save_ok = True
        
        # 4. 플로우 실행 테스트
        if save_ok:
            execute_ok = self.test_execute_flow()
        else:
            execute_ok = False
        
        # 결과 요약
        print("\n" + "="*50)
        print("📊 테스트 결과 요약:")
        print(f"   - 서버 상태: {'✅ 정상' if health_ok else '❌ 비정상'}")
        print(f"   - 플로우 저장: {'✅ 성공' if save_ok else '❌ 실패'}")
        print(f"   - 플로우 실행: {'✅ 성공' if execute_ok else '❌ 실패'}")
        
        if health_ok and save_ok and execute_ok:
            print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
        else:
            print("\n⚠️  일부 테스트가 실패했습니다. 로그를 확인해주세요.")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LangFlow API 테스트")
    parser.add_argument("--url", default="http://localhost:8000", help="API 서버 URL")
    parser.add_argument("--flow", help="실행할 특정 플로우 이름")
    
    args = parser.parse_args()
    
    tester = LangFlowAPITester(args.url)
    
    if args.flow:
        # 특정 플로우만 실행
        tester.test_execute_flow(args.flow)
    else:
        # 전체 테스트 실행
        tester.run_all_tests()


if __name__ == "__main__":
    main()