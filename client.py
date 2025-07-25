import json
import sys
from typing import Any, Dict, List

import requests

# FastAPI 서버 주소
API_URL = "http://127.0.0.1:8000/chat"


def run_chat_session() -> None:
    """
    FastAPI 서버와 상호작용하는 인터랙티브 챗 세션을 실행합니다.
    사용자 입력을 받아 API 서버로 전송하고, 에이전트의 응답을 출력합니다.
    대화 기록은 세션 내에서 유지되어 컨텍스트를 보존합니다.
    """
    # 대화 기록을 저장할 리스트
    messages: List[Dict[str, Any]] = []

    print("=========================================")
    print(" 인터랙티브 챗 클라이언트를 시작합니다. ")
    print(" 종료하려면 'quit' 또는 'exit'을 입력하세요. ")
    print("=========================================\n")

    while True:
        try:
            # 사용자 입력 받기
            user_input = input("You: ")

            # 종료 명령어 확인
            if user_input.lower() in ["quit", "exit"]:
                print("\n채팅을 종료합니다.")
                break

            # 대화 기록에 사용자 메시지 추가
            messages.append({"role": "user", "content": user_input})

            # API 요청 페이로드 생성
            payload = {"messages": messages}

            # API 서버에 POST 요청 보내기 (타임아웃 설정)
            response = requests.post(API_URL, json=payload, timeout=60)
            response.raise_for_status()  # 2xx가 아닌 상태 코드에 대해 HTTPError 발생

            # 응답 파싱
            response_data = response.json()

            # 전체 대화 기록을 서버의 응답으로 업데이트하여 다음 요청에 컨텍스트 유지
            messages = response_data.get("messages", [])

            # 마지막 메시지(에이전트 또는 시스템의 최종 응답)를 찾아 출력
            if messages and messages[-1].get("role") != "user":
                print(f"Agent: {messages[-1].get('content')}")

        except requests.exceptions.ConnectionError:
            print(f"\n[오류] API 서버({API_URL})에 연결할 수 없습니다. 'python main.py'가 실행 중인지 확인하세요.")
            break
        except KeyboardInterrupt:
            print("\n\n[알림] 사용자에 의해 클라이언트가 중단되었습니다.")
            sys.exit(0)
        except Exception as e:
            print(f"\n[오류] 예상치 못한 오류가 발생했습니다: {e}")
            break


if __name__ == "__main__":
    run_chat_session()