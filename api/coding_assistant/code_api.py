"""
코딩어시스턴트 전용 API 엔드포인트들
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from utils.coding_assistant.code_parser import CodeParser, CodeLanguage, CodeBlock, FunctionInfo, ClassInfo
from utils.coding_assistant.template_manager import template_manager, TemplateType

router = APIRouter(prefix="/coding-assistant", tags=["💻 Coding Assistant"])

# Request/Response 모델들
class CodeAnalysisRequest(BaseModel):
    code: str
    language: Optional[str] = None

class CodeAnalysisResponse(BaseModel):
    language: str
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    imports: List[str]
    line_stats: Dict[str, int]

class TemplateRequest(BaseModel):
    template_name: str
    variables: Dict[str, str]

class TemplateResponse(BaseModel):
    rendered_code: str
    template_name: str
    variables_used: Dict[str, str]

class CodeGenerationRequest(BaseModel):
    requirements: str
    language: str = "python"
    template_name: Optional[str] = None
    additional_context: Optional[str] = None

class CodeReviewRequest(BaseModel):
    code: str
    language: Optional[str] = None
    focus_areas: Optional[List[str]] = None

class TestGenerationRequest(BaseModel):
    source_code: str
    language: Optional[str] = None
    test_type: str = "unit"
    test_framework: Optional[str] = None

@router.post("/analyze", response_model=CodeAnalysisResponse)
async def analyze_code(request: CodeAnalysisRequest):
    """
    코드를 분석하여 함수, 클래스, import 등의 정보를 추출합니다.
    """
    try:
        # 언어 감지
        if request.language:
            try:
                language = CodeLanguage(request.language.lower())
            except ValueError:
                language = CodeParser.detect_language(request.code)
        else:
            language = CodeParser.detect_language(request.code)
        
        # 함수 분석 (현재는 Python만 지원)
        functions = []
        classes = []
        
        if language == CodeLanguage.PYTHON:
            functions_info = CodeParser.parse_python_functions(request.code)
            functions = [
                {
                    "name": func.name,
                    "parameters": func.parameters,
                    "return_type": func.return_type,
                    "docstring": func.docstring,
                    "complexity": func.complexity,
                    "line_count": func.line_count
                }
                for func in functions_info
            ]
            
            classes_info = CodeParser.parse_python_classes(request.code)
            classes = [
                {
                    "name": cls.name,
                    "methods": [
                        {
                            "name": method.name,
                            "parameters": method.parameters,
                            "return_type": method.return_type,
                            "complexity": method.complexity
                        }
                        for method in cls.methods
                    ],
                    "attributes": cls.attributes,
                    "inheritance": cls.inheritance,
                    "docstring": cls.docstring
                }
                for cls in classes_info
            ]
        
        # Import 분석
        imports = CodeParser.extract_imports(request.code, language)
        
        # 라인 통계
        line_stats = CodeParser.count_lines_of_code(request.code)
        
        return CodeAnalysisResponse(
            language=language.value,
            functions=functions,
            classes=classes,
            imports=imports,
            line_stats=line_stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"코드 분석 중 오류가 발생했습니다: {str(e)}")

@router.get("/templates")
async def get_templates(
    template_type: Optional[str] = Query(None, description="템플릿 유형 (function, class, api, test 등)"),
    language: Optional[str] = Query(None, description="프로그래밍 언어"),
    search: Optional[str] = Query(None, description="검색 키워드")
):
    """
    사용 가능한 코드 템플릿 목록을 조회합니다.
    """
    try:
        templates = list(template_manager.templates.values())
        
        # 필터링
        if template_type:
            try:
                filter_type = TemplateType(template_type.lower())
                templates = [t for t in templates if t.type == filter_type]
            except ValueError:
                pass
        
        if language:
            templates = [t for t in templates if t.language.lower() == language.lower()]
        
        if search:
            templates = template_manager.search_templates(search)
        
        # 응답 형식으로 변환
        result = []
        for template in templates:
            result.append({
                "name": template.name,
                "type": template.type.value,
                "language": template.language,
                "description": template.description,
                "variables": template.variables,
                "tags": template.tags or [],
                "examples": template.examples or []
            })
        
        return {"templates": result, "total": len(result)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"템플릿 조회 중 오류가 발생했습니다: {str(e)}")

@router.post("/templates/render", response_model=TemplateResponse)
async def render_template(request: TemplateRequest):
    """
    템플릿을 변수로 렌더링하여 코드를 생성합니다.
    """
    try:
        rendered_code = template_manager.render_template(
            request.template_name, 
            request.variables
        )
        
        if rendered_code is None:
            raise HTTPException(status_code=404, detail=f"템플릿 '{request.template_name}'을 찾을 수 없습니다.")
        
        return TemplateResponse(
            rendered_code=rendered_code,
            template_name=request.template_name,
            variables_used=request.variables
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"템플릿 렌더링 중 오류가 발생했습니다: {str(e)}")

@router.get("/templates/{template_name}/variables")
async def get_template_variables(template_name: str):
    """
    특정 템플릿의 필수 변수 목록을 조회합니다.
    """
    try:
        variables = template_manager.get_template_variables(template_name)
        
        if variables is None:
            raise HTTPException(status_code=404, detail=f"템플릿 '{template_name}'을 찾을 수 없습니다.")
        
        template = template_manager.get_template(template_name)
        
        return {
            "template_name": template_name,
            "variables": variables,
            "description": template.description,
            "examples": template.examples or []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"템플릿 변수 조회 중 오류가 발생했습니다: {str(e)}")

@router.post("/generate")
async def generate_code(request: CodeGenerationRequest):
    """
    요구사항을 바탕으로 코드를 생성합니다.
    """
    try:
        # 템플릿 기반 생성인 경우
        if request.template_name:
            template = template_manager.get_template(request.template_name)
            if not template:
                raise HTTPException(status_code=404, detail=f"템플릿 '{request.template_name}'을 찾을 수 없습니다.")
            
            # 간단한 변수 추출 (실제로는 더 정교한 NLP 처리 필요)
            variables = {}
            for var in template.variables:
                if var in request.requirements.lower():
                    # 간단한 키워드 매칭 (실제 구현에서는 더 정교하게)
                    variables[var] = f"extracted_{var}"
                else:
                    variables[var] = f"default_{var}"
            
            generated_code = template_manager.render_template(request.template_name, variables)
            
            return {
                "generated_code": generated_code,
                "method": "template",
                "template_used": request.template_name,
                "variables": variables,
                "language": request.language
            }
        
        # LLM 기반 생성 (기존 도구 사용)
        else:
            # 여기서는 간단한 응답만 제공 (실제로는 LLM 호출)
            return {
                "generated_code": f"# Generated code for: {request.requirements}\n# Language: {request.language}\n# TODO: Implement the requested functionality",
                "method": "llm",
                "requirements": request.requirements,
                "language": request.language,
                "note": "실제 코드 생성을 위해서는 /v1/chat/completions 엔드포인트를 사용하세요."
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"코드 생성 중 오류가 발생했습니다: {str(e)}")

@router.post("/review")
async def review_code(request: CodeReviewRequest):
    """
    코드를 리뷰하고 개선 제안을 제공합니다.
    """
    try:
        # 언어 감지
        if request.language:
            try:
                language = CodeLanguage(request.language.lower())
            except ValueError:
                language = CodeParser.detect_language(request.code)
        else:
            language = CodeParser.detect_language(request.code)
        
        # 기본적인 코드 분석
        line_stats = CodeParser.count_lines_of_code(request.code)
        
        # 간단한 리뷰 포인트 (실제로는 더 정교한 분석 필요)
        review_points = []
        
        if line_stats['code'] > 50:
            review_points.append({
                "type": "complexity",
                "severity": "medium",
                "message": "함수가 너무 길어 보입니다. 더 작은 함수로 분리하는 것을 고려해보세요.",
                "line": None
            })
        
        if line_stats['comment'] == 0:
            review_points.append({
                "type": "documentation",
                "severity": "low",
                "message": "주석이나 독스트링을 추가하여 코드의 가독성을 높여보세요.",
                "line": None
            })
        
        # Python 특화 분석
        if language == CodeLanguage.PYTHON:
            functions = CodeParser.parse_python_functions(request.code)
            for func in functions:
                if func.complexity > 10:
                    review_points.append({
                        "type": "complexity",
                        "severity": "high",
                        "message": f"함수 '{func.name}'의 복잡도가 높습니다 (복잡도: {func.complexity}). 리팩토링을 고려해보세요.",
                        "line": None
                    })
        
        return {
            "language": language.value,
            "line_stats": line_stats,
            "review_points": review_points,
            "overall_score": max(1, 10 - len(review_points)),
            "recommendations": [
                "코드 리뷰를 위해서는 /v1/chat/completions 엔드포인트의 code_review 도구를 사용하세요.",
                "더 상세한 분석을 원하시면 전체 코드와 함께 요청해주세요."
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"코드 리뷰 중 오류가 발생했습니다: {str(e)}")

@router.post("/test/generate")
async def generate_test(request: TestGenerationRequest):
    """
    소스 코드에 대한 테스트 코드를 생성합니다.
    """
    try:
        # 언어 감지
        if request.language:
            try:
                language = CodeLanguage(request.language.lower())
            except ValueError:
                language = CodeParser.detect_language(request.source_code)
        else:
            language = CodeParser.detect_language(request.source_code)
        
        # 테스트 프레임워크 결정
        framework_map = {
            "python": "pytest",
            "javascript": "jest",
            "typescript": "jest",
            "java": "junit"
        }
        
        test_framework = request.test_framework or framework_map.get(language.value, "unittest")
        
        # 기본적인 함수 분석
        functions = []
        if language == CodeLanguage.PYTHON:
            functions = CodeParser.parse_python_functions(request.source_code)
        
        # 간단한 테스트 코드 생성 (실제로는 더 정교한 생성 필요)
        test_code_template = f"""# Generated test code for {language.value}
# Test framework: {test_framework}
# Test type: {request.test_type}

# TODO: Implement comprehensive tests
# Functions found: {[f.name for f in functions] if functions else 'None'}

# For detailed test generation, use the /v1/chat/completions endpoint with test_generation tool
"""
        
        return {
            "test_code": test_code_template,
            "language": language.value,
            "test_framework": test_framework,
            "test_type": request.test_type,
            "functions_found": len(functions),
            "recommendations": [
                "상세한 테스트 생성을 위해서는 /v1/chat/completions 엔드포인트의 test_generation 도구를 사용하세요.",
                f"발견된 함수: {[f.name for f in functions] if functions else '없음'}"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 생성 중 오류가 발생했습니다: {str(e)}")

@router.get("/languages")
async def get_supported_languages():
    """
    지원하는 프로그래밍 언어 목록을 조회합니다.
    """
    languages = [
        {
            "code": lang.value,
            "name": lang.name.title(),
            "supported_features": {
                "analysis": lang == CodeLanguage.PYTHON,  # 현재는 Python만 완전 지원
                "templates": True,
                "generation": True,
                "review": True,
                "test_generation": True
            }
        }
        for lang in CodeLanguage
    ]
    
    return {"languages": languages, "total": len(languages)}