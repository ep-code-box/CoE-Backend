"""
코드 생성 도구 - 함수, 클래스, 모듈 등을 자동으로 생성합니다.
"""

from typing import Dict, Any, Optional
from core.schemas import ChatState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 라우터 프롬프트에 사용될 도구 설명
code_generation_description = {
    "name": "code_generation",
    "description": "함수, 클래스, 모듈 등의 코드를 자동으로 생성합니다. 요구사항을 바탕으로 완전한 코드를 작성해드립니다."
}

# 코드 생성을 위한 프롬프트 템플릿
CODE_GENERATION_PROMPT = ChatPromptTemplate.from_template("""당신은 숙련된 소프트웨어 개발자입니다. 사용자의 요구사항을 바탕으로 고품질의 코드를 생성해주세요.

**코드 생성 가이드라인:**
1. 클린 코드 원칙을 따라 가독성 높은 코드 작성
2. 적절한 주석과 독스트링 포함
3. 타입 힌트 사용 (Python의 경우)
4. 에러 처리 및 예외 상황 고려
5. 테스트 가능한 구조로 설계
6. 보안 및 성능 고려사항 반영

**요구사항:**
{requirements}

**언어/프레임워크:** {language}
**추가 컨텍스트:** {context}

생성된 코드와 함께 다음 정보를 포함해주세요:
- 코드 설명
- 사용 방법
- 주요 기능
- 고려사항

응답 형식:
## 생성된 코드
```{language}
[코드 내용]
```

## 코드 설명
[코드에 대한 상세 설명]

## 사용 방법
[코드 사용 예시]

## 주요 기능
[주요 기능 목록]

## 고려사항
[성능, 보안, 유지보수 관련 고려사항]
""")

def extract_code_requirements(user_input: str) -> Dict[str, str]:
    """사용자 입력에서 코드 생성 요구사항을 추출합니다."""
    
    # 기본값 설정
    requirements = {
        "requirements": user_input,
        "language": "python",  # 기본 언어
        "context": ""
    }
    
    # 언어 감지
    language_keywords = {
        "python": ["python", "파이썬", "py"],
        "javascript": ["javascript", "js", "자바스크립트", "node"],
        "typescript": ["typescript", "ts", "타입스크립트"],
        "java": ["java", "자바"],
        "cpp": ["c++", "cpp", "시플플"],
        "csharp": ["c#", "csharp", "시샵"],
        "go": ["go", "golang", "고"],
        "rust": ["rust", "러스트"],
        "kotlin": ["kotlin", "코틀린"],
        "swift": ["swift", "스위프트"]
    }
    
    user_lower = user_input.lower()
    for lang, keywords in language_keywords.items():
        if any(keyword in user_lower for keyword in keywords):
            requirements["language"] = lang
            break
    
    # 특정 키워드로 컨텍스트 추출
    context_keywords = ["프레임워크", "라이브러리", "패턴", "아키텍처"]
    context_parts = []
    for keyword in context_keywords:
        if keyword in user_input:
            # 키워드 주변 텍스트 추출 (간단한 구현)
            context_parts.append(f"{keyword} 관련 요구사항 포함")
    
    if context_parts:
        requirements["context"] = ", ".join(context_parts)
    
    return requirements

def code_generation_node(state: ChatState) -> Dict[str, Any]:
    """코드 생성 노드 - 사용자 요구사항을 바탕으로 코드를 생성합니다."""
    
    try:
        # 사용자 입력 추출
        user_content = state.get("original_input", "")
        if not user_content:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "코드 생성을 위한 요구사항을 입력해주세요.\n\n예시:\n- 'Python으로 파일 업로드 API 함수 만들어줘'\n- 'JavaScript로 데이터 검증 클래스 생성해줘'\n- 'REST API 클라이언트 클래스를 TypeScript로 작성해줘'"
                }]
            }
        
        # 요구사항 추출
        requirements = extract_code_requirements(user_content)
        
        # LLM 클라이언트 가져오기
        from core.llm_client import langchain_client
        
        # 코드 생성 체인 실행
        chain = CODE_GENERATION_PROMPT | langchain_client | StrOutputParser()
        result = chain.invoke(requirements)
        
        return {
            "messages": [{
                "role": "assistant",
                "content": f"🔧 **코드 생성 완료**\n\n**언어**: {requirements['language']}\n**요구사항**: {requirements['requirements']}\n\n{result}"
            }],
            "generated_code": result,
            "language": requirements["language"],
            "requirements": requirements["requirements"]
        }
        
    except Exception as e:
        error_message = f"코드 생성 중 오류가 발생했습니다: {str(e)}"
        print(f"ERROR in code_generation_node: {error_message}")
        return {
            "messages": [{
                "role": "system",
                "content": error_message
            }]
        }