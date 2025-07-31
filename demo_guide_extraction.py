#!/usr/bin/env python3

"""
가이드 추출 도구 데모 스크립트
실제 사용 예시를 보여줍니다.
"""

import requests
import json
import time

def demo_guide_extraction():
    """가이드 추출 데모"""
    print("🎯 가이드 추출 도구 데모 시작\n")
    
    # 1. 최신 분석 결과 ID 가져오기
    print("1️⃣ 최신 분석 결과 조회...")
    try:
        response = requests.get("http://127.0.0.1:8001/results")
        if response.status_code == 200:
            results = response.json()
            if results:
                latest = max(results, key=lambda x: x['created_at'])
                analysis_id = latest['analysis_id']
                print(f"✅ 분석 ID: {analysis_id}")
                print(f"   상태: {latest['status']}")
                print(f"   생성일: {latest['created_at']}")
                print(f"   레포지토리 수: {latest['repository_count']}")
            else:
                print("❌ 분석 결과가 없습니다.")
                return
        else:
            print(f"❌ 분석 결과 조회 실패: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 오류: {e}")
        return
    
    print("\n" + "="*60)
    
    # 2. 가이드 추출 요청
    print("2️⃣ 가이드 추출 요청...")
    
    chat_request = {
        "messages": [
            {
                "role": "user",
                "content": f"analysis_id {analysis_id}로 이 프로젝트의 표준개발가이드, 공통코드화, 공통함수 가이드를 추출해줘"
            }
        ]
    }
    
    print(f"📤 요청 메시지: {chat_request['messages'][0]['content']}")
    print("⏳ LLM이 분석 중입니다... (30-60초 소요)")
    
    try:
        response = requests.post(
            "http://127.0.0.1:8000/chat",
            json=chat_request,
            timeout=120  # 2분 타임아웃
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n" + "="*60)
            print("3️⃣ 가이드 추출 결과")
            print("="*60)
            
            # 응답에서 메시지 추출
            if 'messages' in result and result['messages']:
                for msg in result['messages']:
                    if msg.get('role') == 'assistant':
                        content = msg.get('content', '')
                        print(content)
                        
                        # 결과를 파일로 저장
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        filename = f"extracted_guides_{timestamp}.md"
                        
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(f"# 개발 가이드 추출 결과\n\n")
                            f.write(f"**분석 ID**: {analysis_id}\n")
                            f.write(f"**추출 시간**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                            f.write("---\n\n")
                            f.write(content)
                        
                        print(f"\n💾 결과가 {filename} 파일로 저장되었습니다.")
                        break
            else:
                print("❌ 응답에서 메시지를 찾을 수 없습니다.")
                print(f"전체 응답: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
        else:
            print(f"❌ 요청 실패: {response.status_code}")
            print(f"응답: {response.text}")
            
    except requests.Timeout:
        print("❌ 요청 시간 초과 (2분)")
        print("LLM 처리 시간이 오래 걸릴 수 있습니다. 잠시 후 다시 시도해주세요.")
    except Exception as e:
        print(f"❌ 오류: {e}")

def show_usage():
    """사용법 안내"""
    print("📖 가이드 추출 도구 사용법")
    print("="*50)
    print()
    print("1. 사전 준비:")
    print("   - CoE-RagPipeline 서버 실행: cd CoE-RagPipeline && python main.py")
    print("   - CoE-Backend 서버 실행: cd CoE-Backend && python main.py")
    print("   - Git 레포지토리 분석 완료 상태")
    print()
    print("2. 직접 채팅으로 사용:")
    print("   - 클라이언트 실행: python client.py")
    print("   - 메시지 입력: 'analysis_id [ID]로 개발 가이드를 추출해줘'")
    print()
    print("3. API로 사용:")
    print("   POST http://127.0.0.1:8000/chat")
    print("   {")
    print('     "messages": [')
    print('       {')
    print('         "role": "user",')
    print('         "content": "analysis_id [ID]로 개발 가이드를 추출해줘"')
    print('       }')
    print('     ]')
    print("   }")
    print()
    print("4. 추출되는 가이드:")
    print("   - 표준개발가이드: 코딩 스타일, 네이밍 컨벤션, 아키텍처 패턴")
    print("   - 공통코드화: 중복 코드 패턴, 재사용 가능한 컴포넌트")
    print("   - 공통함수 가이드: 자주 사용되는 함수 패턴, 유틸리티 함수")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_usage()
    else:
        demo_guide_extraction()