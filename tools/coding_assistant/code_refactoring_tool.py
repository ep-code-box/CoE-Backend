"""
코드 리팩토링 도구 - 기존 코드를 개선하고 최적화합니다.
"""

from typing import Dict, Any, List
from core.schemas import ChatState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 라우터 프롬프트에 사용될 도구 설명
code_refactoring_description = {
    "name": "code_refactoring",
    "description": "기존 코드를 리팩토링하여 가독성, 성능, 유지보수성을 개선합니다. 코드 구조 개선과 최적화를 제공합니다."
}

# 코드 리팩토링을 위한 프롬프트 템플릿
CODE_REFACTORING_PROMPT = ChatPromptTemplate.from_template("""당신은 코드 리팩토링 전문가입니다. 제공된 코드를 분석하여 다양한 리팩토링 기법을 적용해 개선된 코드를 제공해주세요.

**리팩토링 목표:**
1. **가독성 향상**: 명확한 변수명, 함수 분리, 주석 개선
2. **성능 최적화**: 알고리즘 개선, 메모리 사용량 최적화
3. **유지보수성**: 모듈화, 중복 제거, 확장성 고려
4. **코드 품질**: 디자인 패턴 적용, SOLID 원칙 준수
5. **테스트 용이성**: 의존성 주입, 순수 함수 분리

**리팩토링 유형:** {refactoring_type}

**원본 코드:**
```{language}
{original_code}
```

**언어/프레임워크:** {language}
**추가 요구사항:** {requirements}

다음 형식으로 리팩토링 결과를 제공해주세요:

## 🔄 리팩토링 분석
**적용된 기법**: [사용된 리팩토링 기법들]
**주요 개선사항**: [핵심 개선 포인트]

## ✨ 리팩토링된 코드
```{language}
[개선된 코드]
```

## 📋 변경사항 상세
### 1. 구조적 개선
- [코드 구조 변경사항]

### 2. 성능 개선
- [성능 관련 최적화]

### 3. 가독성 향상
- [가독성 개선사항]

### 4. 유지보수성 강화
- [유지보수 관련 개선]

## 🔍 Before vs After 비교
| 항목 | Before | After | 개선효과 |
|------|--------|-------|----------|
| 복잡도 | [이전] | [이후] | [개선도] |
| 가독성 | [이전] | [이후] | [개선도] |
| 성능 | [이전] | [이후] | [개선도] |

## 💡 추가 개선 제안
- [더 나은 개선 방향]

## ⚠️ 주의사항
- [리팩토링 시 고려해야 할 점들]
""")

def extract_refactoring_info(user_input: str) -> Dict[str, str]:
    """사용자 입력에서 리팩토링 정보를 추출합니다."""
    
    result = {
        "original_code": "",
        "language": "python",
        "refactoring_type": "general",
        "requirements": ""
    }
    
    # 코드 블록 추출
    import re
    
    code_block_pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(code_block_pattern, user_input, re.DOTALL)
    
    if matches:
        lang, code = matches[0]
        result["original_code"] = code.strip()
        if lang:
            result["language"] = lang.lower()
    else:
        # 코드 블록이 없으면 전체 입력에서 코드 부분 추출
        lines = user_input.split('\n')
        code_lines = []
        for line in lines:
            # 리팩토링 관련 키워드가 없는 라인을 코드로 간주
            if not any(keyword in line.lower() for keyword in ['리팩토링', '개선', '최적화', '수정']):
                code_lines.append(line)
        
        if code_lines:
            result["original_code"] = '\n'.join(code_lines).strip()
        else:
            result["original_code"] = user_input.strip()
    
    # 리팩토링 유형 감지
    refactoring_keywords = {
        "performance": ["성능", "최적화", "속도", "메모리", "효율"],
        "readability": ["가독성", "읽기", "이해", "명확"],
        "structure": ["구조", "아키텍처", "설계", "모듈"],
        "maintainability": ["유지보수", "확장", "수정", "관리"],
        "testing": ["테스트", "단위테스트", "검증"],
        "security": ["보안", "안전", "취약점"]
    }
    
    user_lower = user_input.lower()
    for ref_type, keywords in refactoring_keywords.items():
        if any(keyword in user_lower for keyword in keywords):
            result["refactoring_type"] = ref_type
            break
    
    # 추가 요구사항 추출
    requirement_indicators = ["요구사항", "조건", "제약", "필요"]
    for indicator in requirement_indicators:
        if indicator in user_input:
            # 간단한 요구사항 추출 로직
            result["requirements"] = "사용자 지정 요구사항 포함"
            break
    
    return result

def code_refactoring_node(state: ChatState) -> Dict[str, Any]:
    """코드 리팩토링 노드 - 기존 코드를 개선하고 최적화합니다."""
    
    try:
        # 사용자 입력 추출
        user_content = state.get("original_input", "")
        if not user_content:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "리팩토링할 코드를 입력해주세요.\n\n예시:\n```python\ndef process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n    return result\n```\n\n리팩토링해줘 (성능 최적화 중심으로)"
                }]
            }
        
        # 리팩토링 정보 추출
        refactoring_info = extract_refactoring_info(user_content)
        
        if not refactoring_info["original_code"]:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "리팩토링할 코드를 찾을 수 없습니다. 코드를 ```로 감싸서 제공하거나, 명확한 코드 내용을 입력해주세요."
                }]
            }
        
        # LLM 클라이언트 가져오기
        from core.llm_client import langchain_client
        
        # 코드 리팩토링 체인 실행
        chain = CODE_REFACTORING_PROMPT | langchain_client | StrOutputParser()
        result = chain.invoke(refactoring_info)
        
        return {
            "messages": [{
                "role": "assistant",
                "content": f"🔄 **코드 리팩토링 완료**\n\n**언어**: {refactoring_info['language']}\n**리팩토링 유형**: {refactoring_info['refactoring_type']}\n**원본 코드 길이**: {len(refactoring_info['original_code'].split())} 단어\n\n{result}"
            }],
            "refactoring_result": result,
            "original_code": refactoring_info["original_code"],
            "language": refactoring_info["language"],
            "refactoring_type": refactoring_info["refactoring_type"]
        }
        
    except Exception as e:
        error_message = f"코드 리팩토링 중 오류가 발생했습니다: {str(e)}"
        print(f"ERROR in code_refactoring_node: {error_message}")
        return {
            "messages": [{
                "role": "system",
                "content": error_message
            }]
        }