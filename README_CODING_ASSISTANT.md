# 🤖 코딩어시스턴트 기능 가이드

CoE-Backend에 새롭게 추가된 코딩어시스턴트 기능들에 대한 상세 가이드입니다.

## ✨ 주요 기능

### 1. 코드 생성 (Code Generation)
- **기능**: 요구사항을 바탕으로 함수, 클래스, 모듈 등의 코드를 자동 생성
- **지원 언어**: Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, Kotlin, Swift
- **도구**: `code_generation_tool.py`

### 2. 코드 리뷰 (Code Review)
- **기능**: 코드 품질 분석, 개선 제안, 버그 탐지, 성능 최적화 방안 제시
- **분석 항목**: 가독성, 성능, 보안, 설계, 테스트 가능성, 문서화
- **도구**: `code_review_tool.py`

### 3. 코드 리팩토링 (Code Refactoring)
- **기능**: 기존 코드를 개선하고 최적화
- **리팩토링 유형**: 성능, 가독성, 구조, 유지보수성, 테스트, 보안
- **도구**: `code_refactoring_tool.py`

### 4. 테스트 생성 (Test Generation)
- **기능**: 단위 테스트, 통합 테스트 코드 자동 생성
- **테스트 프레임워크**: pytest, jest, junit, nunit 등
- **도구**: `test_generation_tool.py`

### 5. 코드 분석 및 파싱
- **기능**: 코드 구조 분석, 함수/클래스 추출, 복잡도 계산
- **유틸리티**: `code_parser.py`

### 6. 코드 템플릿 관리
- **기능**: 재사용 가능한 코드 템플릿 관리 및 렌더링
- **템플릿 유형**: 함수, 클래스, API, 테스트, 설정 파일
- **유틸리티**: `template_manager.py`

## 🚀 사용 방법

### 1. 채팅 인터페이스를 통한 사용

#### 코드 생성
```
사용자: Python으로 파일 업로드 API 함수 만들어줘
에이전트: [code_generation 도구 실행] → 완전한 FastAPI 업로드 함수 생성
```

#### 코드 리뷰
```
사용자: 이 코드를 리뷰해줘
```python
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
```
에이전트: [code_review 도구 실행] → 상세한 코드 리뷰 및 개선 제안
```

#### 코드 리팩토링
```
사용자: 이 코드를 성능 최적화 중심으로 리팩토링해줘
```python
def find_duplicates(numbers):
    duplicates = []
    for i in range(len(numbers)):
        for j in range(i+1, len(numbers)):
            if numbers[i] == numbers[j] and numbers[i] not in duplicates:
                duplicates.append(numbers[i])
    return duplicates
```
에이전트: [code_refactoring 도구 실행] → 최적화된 코드 제공
```

#### 테스트 생성
```
사용자: 이 함수에 대한 단위 테스트를 생성해줘
```python
def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)
```
에이전트: [test_generation 도구 실행] → 포괄적인 테스트 코드 생성
```

### 2. REST API를 통한 사용

#### 코드 분석 API
```bash
curl -X POST "http://localhost:8000/coding-assistant/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def hello(name):\n    return f\"Hello, {name}!\"",
    "language": "python"
  }'
```

#### 템플릿 조회 API
```bash
curl -X GET "http://localhost:8000/coding-assistant/templates?language=python&template_type=function"
```

#### 템플릿 렌더링 API
```bash
curl -X POST "http://localhost:8000/coding-assistant/templates/render" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "python_function",
    "variables": {
      "function_name": "calculate_sum",
      "parameters": "numbers: List[int]",
      "return_type": "int",
      "description": "Calculate sum of numbers",
      "args_doc": "numbers: List of integers",
      "return_doc": "Sum of all numbers",
      "body": "    return sum(numbers)"
    }
  }'
```

#### 코드 생성 API
```bash
curl -X POST "http://localhost:8000/coding-assistant/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": "Create a REST API endpoint for user authentication",
    "language": "python",
    "template_name": "fastapi_endpoint"
  }'
```

#### 코드 리뷰 API
```bash
curl -X POST "http://localhost:8000/coding-assistant/review" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n    return result",
    "language": "python"
  }'
```

#### 테스트 생성 API
```bash
curl -X POST "http://localhost:8000/coding-assistant/test/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "def calculate_average(numbers):\n    if not numbers:\n        return 0\n    return sum(numbers) / len(numbers)",
    "language": "python",
    "test_type": "unit",
    "test_framework": "pytest"
  }'
```

#### 지원 언어 조회 API
```bash
curl -X GET "http://localhost:8000/coding-assistant/languages"
```

## 🏗️ 아키텍처

### 디렉토리 구조
```
CoE-Backend/
├── tools/coding_assistant/          # 코딩어시스턴트 도구들
│   ├── __init__.py
│   ├── code_generation_tool.py      # 코드 생성 도구
│   ├── code_review_tool.py          # 코드 리뷰 도구
│   ├── code_refactoring_tool.py     # 코드 리팩토링 도구
│   └── test_generation_tool.py      # 테스트 생성 도구
├── utils/coding_assistant/          # 공통 유틸리티들
│   ├── __init__.py
│   ├── code_parser.py               # 코드 파싱 및 분석
│   └── template_manager.py          # 템플릿 관리
├── api/coding_assistant/            # 전용 API 엔드포인트들
│   ├── __init__.py
│   └── code_api.py                  # REST API 엔드포인트
└── test_coding_assistant.py         # 테스트 스크립트
```

### 주요 클래스 및 함수

#### CodeParser 클래스
```python
class CodeParser:
    @staticmethod
    def detect_language(code: str) -> CodeLanguage
    def extract_code_blocks(text: str) -> List[CodeBlock]
    def parse_python_functions(code: str) -> List[FunctionInfo]
    def parse_python_classes(code: str) -> List[ClassInfo]
    def extract_imports(code: str, language: CodeLanguage) -> List[str]
    def count_lines_of_code(code: str) -> Dict[str, int]
```

#### TemplateManager 클래스
```python
class TemplateManager:
    def add_template(self, template: CodeTemplate)
    def get_template(self, name: str) -> Optional[CodeTemplate]
    def get_templates_by_type(self, template_type: TemplateType) -> List[CodeTemplate]
    def get_templates_by_language(self, language: str) -> List[CodeTemplate]
    def search_templates(self, query: str) -> List[CodeTemplate]
    def render_template(self, template_name: str, variables: Dict[str, str]) -> Optional[str]
```

## 🧪 테스트

### 테스트 실행
```bash
cd CoE-Backend
python3 test_coding_assistant.py
```

### 테스트 항목
1. **모듈 Import 테스트**: 모든 모듈이 정상적으로 로드되는지 확인
2. **코드 파서 테스트**: 언어 감지, 함수/클래스 파싱, 라인 통계 기능 테스트
3. **템플릿 매니저 테스트**: 템플릿 로드, 렌더링 기능 테스트
4. **API 엔드포인트 테스트**: REST API 경로 구조 확인

## 🔧 설정 및 확장

### 새로운 언어 지원 추가
1. `CodeLanguage` enum에 새 언어 추가
2. `CodeParser.detect_language()`에 언어 감지 패턴 추가
3. 해당 언어용 파싱 함수 구현
4. 템플릿 매니저에 언어별 템플릿 추가

### 새로운 템플릿 추가
```python
from utils.coding_assistant.template_manager import template_manager, CodeTemplate, TemplateType

# 새 템플릿 생성
new_template = CodeTemplate(
    name="my_custom_template",
    type=TemplateType.FUNCTION,
    language="python",
    description="My custom template",
    template="def {function_name}():\n    {body}",
    variables=["function_name", "body"],
    tags=["custom", "python"],
    examples=["def my_function():"]
)

# 템플릿 추가
template_manager.add_template(new_template)
```

### 새로운 도구 추가
1. `tools/coding_assistant/` 디렉토리에 새 도구 파일 생성
2. `{tool_name}_description` 변수와 `{tool_name}_node` 함수 구현
3. 도구 레지스트리가 자동으로 감지하여 에이전트에 등록

## 📚 예시 및 사용 사례

### 1. 전체 프로젝트 구조 생성
```
사용자: FastAPI 프로젝트 구조를 만들어줘. 사용자 인증, 데이터베이스 연동, API 문서화가 포함된 구조로
에이전트: [여러 도구 조합 실행] → 완전한 프로젝트 구조 및 코드 생성
```

### 2. 레거시 코드 현대화
```
사용자: 이 오래된 Python 2 코드를 Python 3.9+ 버전으로 리팩토링하고 타입 힌트를 추가해줘
에이전트: [code_refactoring 도구 실행] → 현대적인 Python 코드로 변환
```

### 3. 포괄적인 테스트 스위트 생성
```
사용자: 이 API 클래스에 대한 완전한 테스트 스위트를 만들어줘. 단위 테스트, 통합 테스트, 모킹 모두 포함해서
에이전트: [test_generation 도구 실행] → 포괄적인 테스트 코드 생성
```

## 🔍 문제 해결

### 일반적인 문제들

#### 1. 모듈 Import 오류
```bash
# 해결방법: Python 경로 확인
export PYTHONPATH="${PYTHONPATH}:/path/to/CoE-Backend"
```

#### 2. 템플릿 렌더링 오류
```python
# 필수 변수 확인
variables = template_manager.get_template_variables("template_name")
print(f"필수 변수: {variables}")
```

#### 3. 코드 파싱 오류
```python
# 지원되는 언어 확인
from utils.coding_assistant.code_parser import CodeLanguage
print(f"지원 언어: {[lang.value for lang in CodeLanguage]}")
```

## 🚀 향후 개발 계획

### 단기 계획
- [ ] 더 많은 프로그래밍 언어 지원 (PHP, Ruby, Scala 등)
- [ ] 코드 품질 메트릭 고도화
- [ ] 실시간 코드 분석 및 제안

### 중기 계획
- [ ] AI 기반 코드 최적화 엔진
- [ ] 프로젝트 전체 구조 분석 및 리팩토링
- [ ] 코드 스타일 가이드 자동 적용

### 장기 계획
- [ ] 자연어를 통한 복잡한 소프트웨어 아키텍처 생성
- [ ] 버그 예측 및 자동 수정 시스템
- [ ] 개발팀 협업을 위한 코드 리뷰 자동화

## 📞 지원 및 문의

코딩어시스턴트 기능에 대한 문의사항이나 개선 제안이 있으시면 언제든지 연락해주세요.

- **이슈 리포팅**: GitHub Issues
- **기능 제안**: Feature Request
- **문서 개선**: Documentation PR

---

**Happy Coding! 🎉**