"""
코드 파싱 및 분석을 위한 공통 유틸리티
"""

import ast
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class CodeLanguage(Enum):
    """지원하는 프로그래밍 언어"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    KOTLIN = "kotlin"
    SWIFT = "swift"

@dataclass
class CodeBlock:
    """코드 블록 정보"""
    content: str
    language: CodeLanguage
    start_line: int = 0
    end_line: int = 0
    metadata: Dict[str, Any] = None

@dataclass
class FunctionInfo:
    """함수 정보"""
    name: str
    parameters: List[str]
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    complexity: int = 1
    line_count: int = 0

@dataclass
class ClassInfo:
    """클래스 정보"""
    name: str
    methods: List[FunctionInfo]
    attributes: List[str]
    inheritance: List[str] = None
    docstring: Optional[str] = None

class CodeParser:
    """코드 파싱 및 분석 유틸리티"""
    
    @staticmethod
    def detect_language(code: str) -> CodeLanguage:
        """코드 내용을 분석하여 프로그래밍 언어를 감지합니다."""
        
        language_patterns = {
            CodeLanguage.PYTHON: [
                r'\bdef\s+\w+\s*\(',
                r'\bimport\s+\w+',
                r'\bfrom\s+\w+\s+import',
                r'\bclass\s+\w+\s*\(',
                r'\bif\s+__name__\s*==\s*["\']__main__["\']'
            ],
            CodeLanguage.JAVASCRIPT: [
                r'\bfunction\s+\w+\s*\(',
                r'\bconst\s+\w+\s*=',
                r'\blet\s+\w+\s*=',
                r'\bvar\s+\w+\s*=',
                r'=>',
                r'\bconsole\.log\s*\('
            ],
            CodeLanguage.TYPESCRIPT: [
                r'\binterface\s+\w+',
                r'\btype\s+\w+\s*=',
                r':\s*(string|number|boolean)',
                r'\bexport\s+(interface|type|class)',
                r'\bimport\s+.*\bfrom\s+["\']'
            ],
            CodeLanguage.JAVA: [
                r'\bpublic\s+class\s+\w+',
                r'\bprivate\s+\w+',
                r'\bpublic\s+static\s+void\s+main',
                r'\bimport\s+java\.',
                r'\bSystem\.out\.print'
            ],
            CodeLanguage.CPP: [
                r'#include\s*<\w+>',
                r'\busing\s+namespace\s+std',
                r'\bint\s+main\s*\(',
                r'\bstd::\w+',
                r'\bcout\s*<<'
            ],
            CodeLanguage.CSHARP: [
                r'\busing\s+System',
                r'\bpublic\s+class\s+\w+',
                r'\bnamespace\s+\w+',
                r'\bConsole\.WriteLine',
                r'\bpublic\s+static\s+void\s+Main'
            ],
            CodeLanguage.GO: [
                r'\bpackage\s+\w+',
                r'\bfunc\s+\w+\s*\(',
                r'\bimport\s*\(',
                r'\bfmt\.Print',
                r'\bvar\s+\w+\s+\w+'
            ],
            CodeLanguage.RUST: [
                r'\bfn\s+\w+\s*\(',
                r'\blet\s+mut\s+\w+',
                r'\buse\s+std::',
                r'\bimpl\s+\w+',
                r'\bprintln!\s*\('
            ],
            CodeLanguage.KOTLIN: [
                r'\bfun\s+\w+\s*\(',
                r'\bval\s+\w+\s*=',
                r'\bvar\s+\w+\s*=',
                r'\bclass\s+\w+',
                r'\bpackage\s+\w+'
            ],
            CodeLanguage.SWIFT: [
                r'\bfunc\s+\w+\s*\(',
                r'\bvar\s+\w+\s*=',
                r'\blet\s+\w+\s*=',
                r'\bclass\s+\w+',
                r'\bimport\s+Foundation'
            ]
        }
        
        scores = {}
        for language, patterns in language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, code, re.MULTILINE | re.IGNORECASE)
                score += len(matches)
            scores[language] = score
        
        # 가장 높은 점수를 받은 언어 반환
        if scores:
            best_language = max(scores, key=scores.get)
            if scores[best_language] > 0:
                return best_language
        
        return CodeLanguage.PYTHON  # 기본값

    @staticmethod
    def extract_code_blocks(text: str) -> List[CodeBlock]:
        """텍스트에서 코드 블록들을 추출합니다."""
        
        code_blocks = []
        
        # 마크다운 코드 블록 패턴
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in matches:
            lang_str = match.group(1)
            content = match.group(2).strip()
            
            # 언어 감지
            if lang_str:
                try:
                    language = CodeLanguage(lang_str.lower())
                except ValueError:
                    language = CodeParser.detect_language(content)
            else:
                language = CodeParser.detect_language(content)
            
            # 라인 번호 계산
            start_pos = match.start()
            start_line = text[:start_pos].count('\n') + 1
            end_line = start_line + content.count('\n')
            
            code_blocks.append(CodeBlock(
                content=content,
                language=language,
                start_line=start_line,
                end_line=end_line
            ))
        
        return code_blocks

    @staticmethod
    def parse_python_functions(code: str) -> List[FunctionInfo]:
        """Python 코드에서 함수 정보를 추출합니다."""
        
        functions = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 매개변수 추출
                    params = [arg.arg for arg in node.args.args]
                    
                    # 반환 타입 추출 (타입 힌트가 있는 경우)
                    return_type = None
                    if node.returns:
                        return_type = ast.unparse(node.returns)
                    
                    # 독스트링 추출
                    docstring = None
                    if (node.body and 
                        isinstance(node.body[0], ast.Expr) and 
                        isinstance(node.body[0].value, ast.Constant) and 
                        isinstance(node.body[0].value.value, str)):
                        docstring = node.body[0].value.value
                    
                    # 복잡도 계산 (간단한 구현)
                    complexity = CodeParser._calculate_complexity(node)
                    
                    # 라인 수 계산
                    line_count = node.end_lineno - node.lineno + 1 if node.end_lineno else 1
                    
                    functions.append(FunctionInfo(
                        name=node.name,
                        parameters=params,
                        return_type=return_type,
                        docstring=docstring,
                        complexity=complexity,
                        line_count=line_count
                    ))
        
        except SyntaxError:
            # 구문 오류가 있는 경우 빈 리스트 반환
            pass
        
        return functions

    @staticmethod
    def parse_python_classes(code: str) -> List[ClassInfo]:
        """Python 코드에서 클래스 정보를 추출합니다."""
        
        classes = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # 메서드 추출
                    methods = []
                    attributes = []
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # 메서드 정보 추출
                            params = [arg.arg for arg in item.args.args]
                            
                            return_type = None
                            if item.returns:
                                return_type = ast.unparse(item.returns)
                            
                            docstring = None
                            if (item.body and 
                                isinstance(item.body[0], ast.Expr) and 
                                isinstance(item.body[0].value, ast.Constant) and 
                                isinstance(item.body[0].value.value, str)):
                                docstring = item.body[0].value.value
                            
                            complexity = CodeParser._calculate_complexity(item)
                            line_count = item.end_lineno - item.lineno + 1 if item.end_lineno else 1
                            
                            methods.append(FunctionInfo(
                                name=item.name,
                                parameters=params,
                                return_type=return_type,
                                docstring=docstring,
                                complexity=complexity,
                                line_count=line_count
                            ))
                        
                        elif isinstance(item, ast.Assign):
                            # 클래스 속성 추출
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    attributes.append(target.id)
                    
                    # 상속 정보 추출
                    inheritance = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            inheritance.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            inheritance.append(ast.unparse(base))
                    
                    # 클래스 독스트링 추출
                    docstring = None
                    if (node.body and 
                        isinstance(node.body[0], ast.Expr) and 
                        isinstance(node.body[0].value, ast.Constant) and 
                        isinstance(node.body[0].value.value, str)):
                        docstring = node.body[0].value.value
                    
                    classes.append(ClassInfo(
                        name=node.name,
                        methods=methods,
                        attributes=attributes,
                        inheritance=inheritance if inheritance else None,
                        docstring=docstring
                    ))
        
        except SyntaxError:
            pass
        
        return classes

    @staticmethod
    def _calculate_complexity(node: ast.AST) -> int:
        """AST 노드의 순환 복잡도를 계산합니다."""
        
        complexity = 1  # 기본 복잡도
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity

    @staticmethod
    def extract_imports(code: str, language: CodeLanguage) -> List[str]:
        """코드에서 import 문을 추출합니다."""
        
        imports = []
        
        if language == CodeLanguage.PYTHON:
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            imports.append(f"{module}.{alias.name}")
            except SyntaxError:
                pass
        
        elif language in [CodeLanguage.JAVASCRIPT, CodeLanguage.TYPESCRIPT]:
            # JavaScript/TypeScript import 패턴
            patterns = [
                r'import\s+.*\s+from\s+["\']([^"\']+)["\']',
                r'import\s+["\']([^"\']+)["\']',
                r'require\s*\(\s*["\']([^"\']+)["\']\s*\)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, code)
                imports.extend(matches)
        
        elif language == CodeLanguage.JAVA:
            # Java import 패턴
            pattern = r'import\s+([^;]+);'
            matches = re.findall(pattern, code)
            imports.extend(matches)
        
        return imports

    @staticmethod
    def count_lines_of_code(code: str) -> Dict[str, int]:
        """코드의 라인 수를 계산합니다."""
        
        lines = code.split('\n')
        
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = 0
        
        # 간단한 주석 라인 계산 (언어별로 다를 수 있음)
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
                comment_lines += 1
        
        code_lines = total_lines - blank_lines - comment_lines
        
        return {
            'total': total_lines,
            'code': code_lines,
            'blank': blank_lines,
            'comment': comment_lines
        }