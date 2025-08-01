"""
코드 템플릿 관리 유틸리티
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import os

class TemplateType(Enum):
    """템플릿 유형"""
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    API = "api"
    TEST = "test"
    CONFIG = "config"

@dataclass
class CodeTemplate:
    """코드 템플릿 정보"""
    name: str
    type: TemplateType
    language: str
    description: str
    template: str
    variables: List[str]
    tags: List[str] = None
    examples: List[str] = None

class TemplateManager:
    """코드 템플릿 관리자"""
    
    def __init__(self):
        self.templates: Dict[str, CodeTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """기본 템플릿들을 로드합니다."""
        
        # Python 함수 템플릿
        self.add_template(CodeTemplate(
            name="python_function",
            type=TemplateType.FUNCTION,
            language="python",
            description="Python 함수 기본 템플릿",
            template='''def {function_name}({parameters}) -> {return_type}:
    """
    {description}
    
    Args:
        {args_doc}
    
    Returns:
        {return_doc}
    """
    {body}''',
            variables=["function_name", "parameters", "return_type", "description", "args_doc", "return_doc", "body"],
            tags=["python", "function", "basic"],
            examples=[
                "def calculate_sum(numbers: List[int]) -> int:",
                "def process_data(data: Dict[str, Any]) -> Optional[str]:"
            ]
        ))
        
        # Python 클래스 템플릿
        self.add_template(CodeTemplate(
            name="python_class",
            type=TemplateType.CLASS,
            language="python",
            description="Python 클래스 기본 템플릿",
            template='''class {class_name}{inheritance}:
    """
    {description}
    
    Attributes:
        {attributes_doc}
    """
    
    def __init__(self{init_params}):
        """
        Initialize {class_name}.
        
        Args:
            {init_args_doc}
        """
        {init_body}
    
    {methods}''',
            variables=["class_name", "inheritance", "description", "attributes_doc", "init_params", "init_args_doc", "init_body", "methods"],
            tags=["python", "class", "oop"],
            examples=[
                "class DataProcessor:",
                "class APIClient(BaseClient):"
            ]
        ))
        
        # FastAPI 엔드포인트 템플릿
        self.add_template(CodeTemplate(
            name="fastapi_endpoint",
            type=TemplateType.API,
            language="python",
            description="FastAPI 엔드포인트 템플릿",
            template='''@router.{method}("{path}")
async def {function_name}({parameters}) -> {response_model}:
    """
    {description}
    
    Args:
        {args_doc}
    
    Returns:
        {return_doc}
    
    Raises:
        HTTPException: {error_doc}
    """
    try:
        {body}
        
        return {response}
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{error_message}: {{str(e)}}"
        )''',
            variables=["method", "path", "function_name", "parameters", "response_model", "description", "args_doc", "return_doc", "error_doc", "body", "response", "error_message"],
            tags=["python", "fastapi", "api", "endpoint"],
            examples=[
                "@router.post('/users')",
                "@router.get('/users/{user_id}')"
            ]
        ))
        
        # JavaScript 함수 템플릿
        self.add_template(CodeTemplate(
            name="javascript_function",
            type=TemplateType.FUNCTION,
            language="javascript",
            description="JavaScript 함수 기본 템플릿",
            template='''/**
 * {description}
 * 
 * @param {{{param_types}}} {param_names} - {param_descriptions}
 * @returns {{{return_type}}} {return_description}
 */
{async_keyword}function {function_name}({parameters}) {{
    {body}
}}''',
            variables=["description", "param_types", "param_names", "param_descriptions", "return_type", "return_description", "async_keyword", "function_name", "parameters", "body"],
            tags=["javascript", "function", "basic"],
            examples=[
                "function calculateSum(numbers)",
                "async function fetchData(url)"
            ]
        ))
        
        # React 컴포넌트 템플릿
        self.add_template(CodeTemplate(
            name="react_component",
            type=TemplateType.CLASS,
            language="javascript",
            description="React 함수형 컴포넌트 템플릿",
            template='''import React{imports} from 'react';
{additional_imports}

/**
 * {description}
 * 
 * @param {{{props_type}}} props - {props_description}
 * @returns {{JSX.Element}} {component_description}
 */
const {component_name} = ({props}) => {{
    {hooks}
    
    {handlers}
    
    return (
        {jsx}
    );
}};

export default {component_name};''',
            variables=["imports", "additional_imports", "description", "props_type", "props_description", "component_description", "component_name", "props", "hooks", "handlers", "jsx"],
            tags=["javascript", "react", "component", "frontend"],
            examples=[
                "const UserProfile = ({ user }) =>",
                "const DataTable = ({ data, onSort }) =>"
            ]
        ))
        
        # Python 테스트 템플릿
        self.add_template(CodeTemplate(
            name="python_test",
            type=TemplateType.TEST,
            language="python",
            description="Python 단위 테스트 템플릿",
            template='''import unittest
from unittest.mock import Mock, patch
{additional_imports}

class Test{class_name}(unittest.TestCase):
    """
    {description}
    """
    
    def setUp(self):
        """테스트 설정"""
        {setup_code}
    
    def tearDown(self):
        """테스트 정리"""
        {teardown_code}
    
    def test_{test_name}(self):
        """
        {test_description}
        """
        # Arrange
        {arrange}
        
        # Act
        {act}
        
        # Assert
        {assert_code}
    
    {additional_tests}

if __name__ == '__main__':
    unittest.main()''',
            variables=["additional_imports", "class_name", "description", "setup_code", "teardown_code", "test_name", "test_description", "arrange", "act", "assert_code", "additional_tests"],
            tags=["python", "test", "unittest", "testing"],
            examples=[
                "class TestDataProcessor(unittest.TestCase):",
                "def test_calculate_sum_with_valid_input(self):"
            ]
        ))
    
    def add_template(self, template: CodeTemplate):
        """새 템플릿을 추가합니다."""
        self.templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[CodeTemplate]:
        """템플릿을 이름으로 조회합니다."""
        return self.templates.get(name)
    
    def get_templates_by_type(self, template_type: TemplateType) -> List[CodeTemplate]:
        """유형별로 템플릿을 조회합니다."""
        return [template for template in self.templates.values() if template.type == template_type]
    
    def get_templates_by_language(self, language: str) -> List[CodeTemplate]:
        """언어별로 템플릿을 조회합니다."""
        return [template for template in self.templates.values() if template.language.lower() == language.lower()]
    
    def search_templates(self, query: str) -> List[CodeTemplate]:
        """키워드로 템플릿을 검색합니다."""
        query_lower = query.lower()
        results = []
        
        for template in self.templates.values():
            # 이름, 설명, 태그에서 검색
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                (template.tags and any(query_lower in tag.lower() for tag in template.tags))):
                results.append(template)
        
        return results
    
    def render_template(self, template_name: str, variables: Dict[str, str]) -> Optional[str]:
        """템플릿을 변수로 렌더링합니다."""
        template = self.get_template(template_name)
        if not template:
            return None
        
        try:
            return template.template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}")
    
    def get_template_variables(self, template_name: str) -> Optional[List[str]]:
        """템플릿의 필수 변수 목록을 반환합니다."""
        template = self.get_template(template_name)
        return template.variables if template else None
    
    def export_templates(self, file_path: str):
        """템플릿을 JSON 파일로 내보냅니다."""
        data = {}
        for name, template in self.templates.items():
            data[name] = {
                "name": template.name,
                "type": template.type.value,
                "language": template.language,
                "description": template.description,
                "template": template.template,
                "variables": template.variables,
                "tags": template.tags or [],
                "examples": template.examples or []
            }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def import_templates(self, file_path: str):
        """JSON 파일에서 템플릿을 가져옵니다."""
        if not os.path.exists(file_path):
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for name, template_data in data.items():
            template = CodeTemplate(
                name=template_data["name"],
                type=TemplateType(template_data["type"]),
                language=template_data["language"],
                description=template_data["description"],
                template=template_data["template"],
                variables=template_data["variables"],
                tags=template_data.get("tags"),
                examples=template_data.get("examples")
            )
            self.add_template(template)

# 전역 템플릿 매니저 인스턴스
template_manager = TemplateManager()