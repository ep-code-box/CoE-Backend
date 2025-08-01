"""
테스트 코드 생성 도구 - 단위 테스트, 통합 테스트 등을 자동으로 생성합니다.
"""

from typing import Dict, Any, List
from core.schemas import ChatState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.coding_assistant.code_parser import CodeParser, CodeLanguage

# 라우터 프롬프트에 사용될 도구 설명
test_generation_description = {
    "name": "test_generation",
    "description": "제공된 코드에 대한 단위 테스트, 통합 테스트 코드를 자동으로 생성합니다. 다양한 테스트 케이스와 모킹을 포함합니다."
}

# 테스트 생성을 위한 프롬프트 템플릿
TEST_GENERATION_PROMPT = ChatPromptTemplate.from_template("""당신은 테스트 코드 작성 전문가입니다. 제공된 코드에 대한 포괄적인 테스트 코드를 생성해주세요.

**테스트 작성 원칙:**
1. **완전성**: 모든 함수와 메서드에 대한 테스트 포함
2. **경계값 테스트**: 정상, 경계, 예외 상황 모두 테스트
3. **모킹**: 외부 의존성에 대한 적절한 모킹 사용
4. **가독성**: 명확한 테스트 이름과 구조
5. **유지보수성**: 변경에 강한 테스트 코드

**테스트 유형:** {test_type}

**원본 코드:**
```{language}
{source_code}
```

**언어/프레임워크:** {language}
**테스트 프레임워크:** {test_framework}

다음 형식으로 테스트 코드를 생성해주세요:

## 🧪 생성된 테스트 코드
```{language}
[완전한 테스트 코드]
```

## 📋 테스트 케이스 설명
### 1. 정상 케이스 테스트
- [정상 동작 테스트 케이스들]

### 2. 경계값 테스트
- [경계값 및 극한 상황 테스트]

### 3. 예외 상황 테스트
- [에러 및 예외 상황 테스트]

### 4. 통합 테스트
- [컴포넌트 간 상호작용 테스트]

## 🔧 테스트 실행 방법
```bash
[테스트 실행 명령어]
```

## 📊 커버리지 분석
- **예상 커버리지**: [예상 코드 커버리지 %]
- **테스트된 함수**: [테스트된 함수 목록]
- **미테스트 영역**: [추가 테스트가 필요한 부분]

## 💡 테스트 개선 제안
- [테스트 품질 향상을 위한 제안사항]

## ⚠️ 주의사항
- [테스트 실행 시 고려해야 할 점들]
""")

def extract_test_info(user_input: str) -> Dict[str, str]:
    """사용자 입력에서 테스트 생성 정보를 추출합니다."""
    
    result = {
        "source_code": "",
        "language": "python",
        "test_type": "unit",
        "test_framework": ""
    }
    
    # 코드 블록 추출
    import re
    
    code_block_pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(code_block_pattern, user_input, re.DOTALL)
    
    if matches:
        lang, code = matches[0]
        result["source_code"] = code.strip()
        if lang:
            result["language"] = lang.lower()
    else:
        # 코드 블록이 없으면 전체 입력에서 코드 부분 추출
        lines = user_input.split('\n')
        code_lines = []
        for line in lines:
            # 테스트 관련 키워드가 없는 라인을 코드로 간주
            if not any(keyword in line.lower() for keyword in ['테스트', '생성', '만들어', '작성']):
                code_lines.append(line)
        
        if code_lines:
            result["source_code"] = '\n'.join(code_lines).strip()
        else:
            result["source_code"] = user_input.strip()
    
    # 언어 감지
    if result["source_code"]:
        detected_language = CodeParser.detect_language(result["source_code"])
        result["language"] = detected_language.value
    
    # 테스트 유형 감지
    test_type_keywords = {
        "unit": ["단위", "unit", "함수", "메서드"],
        "integration": ["통합", "integration", "연동", "전체"],
        "e2e": ["e2e", "end-to-end", "종단", "전체"],
        "performance": ["성능", "performance", "부하", "속도"],
        "security": ["보안", "security", "취약점"]
    }
    
    user_lower = user_input.lower()
    for test_type, keywords in test_type_keywords.items():
        if any(keyword in user_lower for keyword in keywords):
            result["test_type"] = test_type
            break
    
    # 테스트 프레임워크 설정
    framework_map = {
        "python": "pytest",
        "javascript": "jest",
        "typescript": "jest",
        "java": "junit",
        "csharp": "nunit",
        "go": "testing",
        "rust": "cargo test"
    }
    
    result["test_framework"] = framework_map.get(result["language"], "unittest")
    
    # 특정 프레임워크가 언급된 경우
    framework_keywords = {
        "pytest": ["pytest"],
        "unittest": ["unittest"],
        "jest": ["jest"],
        "mocha": ["mocha"],
        "junit": ["junit"],
        "nunit": ["nunit"],
        "xunit": ["xunit"]
    }
    
    for framework, keywords in framework_keywords.items():
        if any(keyword in user_lower for keyword in keywords):
            result["test_framework"] = framework
            break
    
    return result

def test_generation_node(state: ChatState) -> Dict[str, Any]:
    """테스트 생성 노드 - 제공된 코드에 대한 테스트 코드를 생성합니다."""
    
    try:
        # 사용자 입력 추출
        user_content = state.get("original_input", "")
        if not user_content:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "테스트를 생성할 코드를 입력해주세요.\n\n예시:\n```python\ndef calculate_average(numbers):\n    if not numbers:\n        return 0\n    return sum(numbers) / len(numbers)\n```\n\n이 함수에 대한 단위 테스트를 생성해줘"
                }]
            }
        
        # 테스트 정보 추출
        test_info = extract_test_info(user_content)
        
        if not test_info["source_code"]:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "테스트를 생성할 코드를 찾을 수 없습니다. 코드를 ```로 감싸서 제공하거나, 명확한 코드 내용을 입력해주세요."
                }]
            }
        
        # LLM 클라이언트 가져오기
        from core.llm_client import langchain_client
        
        # 테스트 생성 체인 실행
        chain = TEST_GENERATION_PROMPT | langchain_client | StrOutputParser()
        result = chain.invoke(test_info)
        
        return {
            "messages": [{
                "role": "assistant",
                "content": f"🧪 **테스트 코드 생성 완료**\n\n**언어**: {test_info['language']}\n**테스트 유형**: {test_info['test_type']}\n**테스트 프레임워크**: {test_info['test_framework']}\n**원본 코드 길이**: {len(test_info['source_code'].split())} 단어\n\n{result}"
            }],
            "test_code": result,
            "source_code": test_info["source_code"],
            "language": test_info["language"],
            "test_type": test_info["test_type"],
            "test_framework": test_info["test_framework"]
        }
        
    except Exception as e:
        error_message = f"테스트 생성 중 오류가 발생했습니다: {str(e)}"
        print(f"ERROR in test_generation_node: {error_message}")
        return {
            "messages": [{
                "role": "system",
                "content": error_message
            }]
        }