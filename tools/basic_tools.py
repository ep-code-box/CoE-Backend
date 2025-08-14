"""
기본적인 텍스트 처리 도구를 정의합니다.
"""
import json
from typing import Dict, Any, List

# --- Tool Implementations ---

def to_uppercase(text: str) -> str:
    """
    입력된 텍스트를 대문자로 변환합니다.
    """
    print(f"Executing to_uppercase with: {text}")
    return text.upper()

def reverse_string(text: str) -> str:
    """
    입력된 텍스트의 순서를 반대로 뒤집습니다.
    """
    print(f"Executing reverse_string with: {text}")
    return text[::-1]

# --- LLM에 제공될 Tool 명세 (OpenAI 호환) ---

# 각 함수에 대한 JSON 스키마 정의
to_uppercase_schema = {
    "type": "function",
    "function": {
        "name": "to_uppercase",
        "description": "입력된 텍스트를 대문자로 변환합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "대문자로 변환할 텍스트",
                }
            },
            "required": ["text"],
        },
    },
}

reverse_string_schema = {
    "type": "function",
    "function": {
        "name": "reverse_string",
        "description": "입력된 텍스트의 순서를 반대로 뒤집습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "순서를 뒤집을 텍스트",
                },
            },
            "required": ["text"],
        },
    },
}

# --- Registry에 등록할 변수 ---

# 서버에서 사용 가능한 Tool 목록
available_tools: List[Dict[str, Any]] = [
    to_uppercase_schema,
    reverse_string_schema
]

# Tool 이름과 실제 함수 구현을 매핑
tool_functions: Dict[str, callable] = {
    "to_uppercase": to_uppercase,
    "reverse_string": reverse_string,
}
