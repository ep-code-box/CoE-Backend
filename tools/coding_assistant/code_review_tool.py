"""
코드 리뷰 도구 - 코드 품질 분석, 개선 제안, 버그 탐지 등을 수행합니다.
"""

from typing import Dict, Any, List
from core.schemas import ChatState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 라우터 프롬프트에 사용될 도구 설명
code_review_description = {
    "name": "code_review",
    "description": "코드를 분석하여 품질 개선 제안, 버그 탐지, 성능 최적화 방안을 제시합니다. 코드 리뷰와 개선 사항을 제공합니다."
}

# 코드 리뷰를 위한 프롬프트 템플릿
CODE_REVIEW_PROMPT = ChatPromptTemplate.from_template("""당신은 시니어 소프트웨어 개발자이자 코드 리뷰 전문가입니다. 제공된 코드를 철저히 분석하여 종합적인 리뷰를 제공해주세요.

**리뷰 기준:**
1. **코드 품질**: 가독성, 유지보수성, 일관성
2. **성능**: 시간/공간 복잡도, 최적화 가능성
3. **보안**: 보안 취약점, 입력 검증
4. **설계**: 아키텍처, 디자인 패턴, SOLID 원칙
5. **테스트**: 테스트 가능성, 에지 케이스
6. **문서화**: 주석, 독스트링, 명명 규칙

**분석할 코드:**
```{language}
{code}
```

**언어/프레임워크:** {language}
**추가 컨텍스트:** {context}

다음 형식으로 상세한 리뷰를 제공해주세요:

## 📊 전체 평가
**점수**: [1-10점]
**전반적 평가**: [한 줄 요약]

## ✅ 잘된 점
- [좋은 점들 나열]

## ⚠️ 개선이 필요한 점
### 1. 코드 품질
- [구체적인 개선 사항]

### 2. 성능 최적화
- [성능 개선 방안]

### 3. 보안 고려사항
- [보안 관련 이슈]

### 4. 설계 개선
- [아키텍처/설계 개선안]

## 🐛 잠재적 버그
- [발견된 버그나 문제점]

## 🔧 개선된 코드 제안
```{language}
[개선된 코드 예시]
```

## 📝 추가 권장사항
- [테스트, 문서화, 모니터링 등]

## 🎯 우선순위
1. [가장 중요한 개선사항]
2. [두 번째 중요한 개선사항]
3. [세 번째 중요한 개선사항]
""")

def extract_code_from_input(user_input: str) -> Dict[str, str]:
    """사용자 입력에서 코드와 메타데이터를 추출합니다."""
    
    result = {
        "code": "",
        "language": "python",  # 기본값
        "context": ""
    }
    
    # 코드 블록 추출 (```로 감싸진 부분)
    import re
    
    # 언어가 명시된 코드 블록 찾기
    code_block_pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(code_block_pattern, user_input, re.DOTALL)
    
    if matches:
        # 첫 번째 코드 블록 사용
        lang, code = matches[0]
        result["code"] = code.strip()
        if lang:
            result["language"] = lang.lower()
    else:
        # 코드 블록이 없으면 전체 입력을 코드로 간주
        # 단, "리뷰", "분석" 등의 키워드가 있으면 해당 부분 제외
        lines = user_input.split('\n')
        code_lines = []
        for line in lines:
            if not any(keyword in line.lower() for keyword in ['리뷰', '분석', '검토', '개선']):
                code_lines.append(line)
        result["code"] = '\n'.join(code_lines).strip()
    
    # 언어 감지 (코드 내용 기반)
    if not result["code"]:
        result["code"] = user_input.strip()
    
    # 언어 추론
    language_indicators = {
        "python": ["def ", "import ", "from ", "class ", "if __name__"],
        "javascript": ["function ", "const ", "let ", "var ", "=>", "console.log"],
        "typescript": ["interface ", "type ", ": string", ": number", "export "],
        "java": ["public class", "private ", "public static void main", "import java"],
        "cpp": ["#include", "using namespace", "int main()", "std::"],
        "csharp": ["using System", "public class", "namespace ", "Console.WriteLine"],
        "go": ["package ", "func ", "import (", "fmt.Print"],
        "rust": ["fn ", "let mut", "use std::", "impl "],
        "kotlin": ["fun ", "val ", "var ", "class ", "package "],
        "swift": ["func ", "var ", "let ", "class ", "import Foundation"]
    }
    
    code_lower = result["code"].lower()
    for lang, indicators in language_indicators.items():
        if any(indicator.lower() in code_lower for indicator in indicators):
            result["language"] = lang
            break
    
    return result

def code_review_node(state: ChatState) -> Dict[str, Any]:
    """코드 리뷰 노드 - 제공된 코드를 분석하고 개선 제안을 제공합니다."""
    
    try:
        # 사용자 입력 추출
        user_content = state.get("original_input", "")
        if not user_content:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "리뷰할 코드를 입력해주세요.\n\n예시:\n```python\ndef calculate_sum(numbers):\n    total = 0\n    for num in numbers:\n        total += num\n    return total\n```\n\n또는 코드와 함께 '이 코드를 리뷰해줘'라고 요청해주세요."
                }]
            }
        
        # 코드 추출
        code_info = extract_code_from_input(user_content)
        
        if not code_info["code"]:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "리뷰할 코드를 찾을 수 없습니다. 코드를 ```로 감싸서 제공하거나, 명확한 코드 내용을 입력해주세요."
                }]
            }
        
        # LLM 클라이언트 가져오기
        from core.llm_client import langchain_client
        
        # 코드 리뷰 체인 실행
        chain = CODE_REVIEW_PROMPT | langchain_client | StrOutputParser()
        result = chain.invoke(code_info)
        
        return {
            "messages": [{
                "role": "assistant",
                "content": f"🔍 **코드 리뷰 완료**\n\n**언어**: {code_info['language']}\n**코드 길이**: {len(code_info['code'].split())} 단어\n\n{result}"
            }],
            "review_result": result,
            "reviewed_code": code_info["code"],
            "language": code_info["language"]
        }
        
    except Exception as e:
        error_message = f"코드 리뷰 중 오류가 발생했습니다: {str(e)}"
        print(f"ERROR in code_review_node: {error_message}")
        return {
            "messages": [{
                "role": "system",
                "content": error_message
            }]
        }