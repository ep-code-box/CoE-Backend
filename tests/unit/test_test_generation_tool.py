import pytest
from tools.coding_assistant.test_generation_tool import extract_test_info

class TestExtractTestInfo:
    """extract_test_info 함수 단위 테스트"""

    def test_extract_code_with_language_tag(self):
        """언어 태그가 있는 코드 블록 추출 테스트"""
        user_input = """
        다음 파이썬 코드에 대한 단위 테스트를 생성해줘:
        ```python
        def add(a, b):
            return a + b
        ```
        """
        result = extract_test_info(user_input)
        assert result["source_code"] == "def add(a, b):\n    return a + b"
        assert result["language"] == "python"
        assert result["test_type"] == "unit"
        assert result["test_framework"] == "pytest"

    def test_extract_code_without_language_tag(self):
        """언어 태그가 없는 코드 블록 추출 테스트"""
        user_input = """
        ```
        function subtract(a, b) {
            return a - b;
        }
        ```
        이 자바스크립트 코드에 대한 통합 테스트를 만들어줘.
        """
        result = extract_test_info(user_input)
        assert result["source_code"] == "function subtract(a, b) {\n    return a - b;\n}"
        assert result["language"] == "javascript"  # 언어 자동 감지
        assert result["test_type"] == "integration"
        assert result["test_framework"] == "jest"

    def test_extract_code_no_code_block(self):
        """코드 블록 없이 코드 추출 테스트"""
        user_input = """
        다음 코드를 테스트해줘:
        public class MyClass {
            public int multiply(int a, int b) {
                return a * b;
            }
        }
        """
        result = extract_test_info(user_input)
        assert "public class MyClass" in result["source_code"]
        assert result["language"] == "java"
        assert result["test_type"] == "unit" # 기본값
        assert result["test_framework"] == "junit"

    def test_extract_test_type(self):
        """테스트 유형 추출 테스트"""
        user_input = "단위 테스트를 작성해줘."
        result = extract_test_info(user_input)
        assert result["test_type"] == "unit"

        user_input = "통합 테스트를 만들어줘."
        result = extract_test_info(user_input)
        assert result["test_type"] == "integration"

        user_input = "성능 테스트가 필요해."
        result = extract_test_info(user_input)
        assert result["test_type"] == "performance"

    def test_extract_test_framework(self):
        """테스트 프레임워크 추출 테스트"""
        user_input = "pytest를 사용해서 테스트해줘."
        result = extract_test_info(user_input)
        assert result["test_framework"] == "pytest"

        user_input = "jest로 테스트를 작성해줘."
        result = extract_test_info(user_input)
        assert result["test_framework"] == "jest"

    def test_empty_input(self):
        """빈 입력 테스트"""
        user_input = ""
        result = extract_test_info(user_input)
        assert result["source_code"] == ""
        assert result["language"] == "python" # 기본값
        assert result["test_type"] == "unit" # 기본값

    def test_only_text_input(self):
        """텍스트만 있는 입력 테스트"""
        user_input = "이것은 테스트 코드 생성을 위한 일반 텍스트입니다."
        result = extract_test_info(user_input)
        assert result["source_code"] == user_input
        assert result["language"] == "python" # 기본값
        assert result["test_type"] == "unit" # 기본값
