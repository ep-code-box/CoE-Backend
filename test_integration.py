#!/usr/bin/env python3

"""
가이드 추출 도구 통합 테스트 스크립트
CoE-Backend와 CoE-RagPipeline 간의 통합을 테스트합니다.
"""

import requests
import json
import time
import sys

def test_rag_pipeline_connection():
    """RAG Pipeline 연결 테스트"""
    try:
        response = requests.get("http://127.0.0.1:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ CoE-RagPipeline 서버 연결 성공")
            return True
        else:
            print(f"❌ CoE-RagPipeline 서버 응답 오류: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ CoE-RagPipeline 서버 연결 실패: {e}")
        return False

def get_latest_analysis_id():
    """최신 분석 결과 ID 가져오기"""
    try:
        response = requests.get("http://127.0.0.1:8001/results", timeout=10)
        if response.status_code == 200:
            results = response.json()
            if results:
                # 가장 최근 완료된 분석 결과 선택
                completed_results = [r for r in results if r['status'] == 'completed']
                if completed_results:
                    latest = max(completed_results, key=lambda x: x['created_at'])
                    print(f"✅ 최신 분석 결과 ID: {latest['analysis_id']}")
                    return latest['analysis_id']
                else:
                    print("❌ 완료된 분석 결과가 없습니다.")
                    return None
            else:
                print("❌ 분석 결과가 없습니다.")
                return None
        else:
            print(f"❌ 분석 결과 조회 실패: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"❌ 분석 결과 조회 중 오류: {e}")
        return None

def test_guide_extraction_direct():
    """가이드 추출 함수 직접 테스트"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from tools.guide_extraction_tool import get_rag_analysis_result, extract_git_urls_from_analysis
        
        print("\n=== 직접 RAG Pipeline 연결 테스트 ===")
        
        # 최신 분석 결과 가져오기
        analysis_data = get_rag_analysis_result()
        
        if analysis_data:
            print(f"✅ 분석 결과 가져오기 성공")
            print(f"분석 ID: {analysis_data.get('analysis_id', 'N/A')}")
            print(f"상태: {analysis_data.get('status', 'N/A')}")
            print(f"레포지토리 수: {len(analysis_data.get('repositories', []))}")
            
            # Git URL 추출 테스트
            git_urls = extract_git_urls_from_analysis(analysis_data)
            print(f"Git URLs: {git_urls}")
            
            return True
        else:
            print("❌ 분석 결과를 가져올 수 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ 직접 테스트 중 오류: {e}")
        return False

def test_backend_server():
    """Backend 서버 연결 테스트"""
    try:
        # Backend 서버가 실행 중인지 확인
        response = requests.get("http://127.0.0.1:8000/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ CoE-Backend 서버 연결 성공")
            return True
        else:
            print(f"❌ CoE-Backend 서버 응답 오류: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ CoE-Backend 서버 연결 실패: {e}")
        print("Backend 서버를 먼저 실행해주세요: cd CoE-Backend && python main.py")
        return False

def test_chat_with_guide_extraction():
    """채팅을 통한 가이드 추출 테스트"""
    try:
        # 최신 분석 ID 가져오기
        analysis_id = get_latest_analysis_id()
        if not analysis_id:
            print("❌ 사용할 분석 결과가 없습니다.")
            return False
        
        # 채팅 요청 데이터 (올바른 스키마 형식)
        chat_data = {
            "messages": [
                {
                    "role": "user",
                    "content": f"analysis_id {analysis_id}로 개발 가이드를 추출해줘"
                }
            ]
        }
        
        print(f"\n=== 채팅 API 테스트 ===")
        print(f"요청 메시지: {chat_data['messages'][0]['content']}")
        
        response = requests.post(
            "http://127.0.0.1:8000/chat",
            json=chat_data,
            timeout=60  # 가이드 추출은 시간이 걸릴 수 있음
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 채팅 API 응답 성공")
            print(f"응답 길이: {len(result.get('response', ''))}")
            print(f"응답 미리보기: {result.get('response', '')[:200]}...")
            return True
        else:
            print(f"❌ 채팅 API 오류: {response.status_code}")
            print(f"응답: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ 채팅 API 테스트 중 오류: {e}")
        return False

def main():
    print("🧪 가이드 추출 도구 통합 테스트 시작\n")
    
    # 1. RAG Pipeline 연결 테스트
    if not test_rag_pipeline_connection():
        print("\n❌ RAG Pipeline 서버를 먼저 실행해주세요:")
        print("cd CoE-RagPipeline && python main.py")
        return
    
    # 2. 직접 연결 테스트
    if not test_guide_extraction_direct():
        print("\n❌ 직접 연결 테스트 실패")
        return
    
    # 3. Backend 서버 테스트
    if not test_backend_server():
        return
    
    # 4. 전체 플로우 테스트
    if test_chat_with_guide_extraction():
        print("\n🎉 모든 테스트 성공!")
    else:
        print("\n❌ 통합 테스트 실패")

if __name__ == "__main__":
    main()