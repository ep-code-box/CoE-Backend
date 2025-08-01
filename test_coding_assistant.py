#!/usr/bin/env python3
"""
코딩어시스턴트 기능 테스트 스크립트
"""

import sys
import os
sys.path.append('.')

def test_imports():
    """모든 모듈이 정상적으로 import되는지 테스트"""
    try:
        from api.coding_assistant.code_api import router
        print("✅ 코딩어시스턴트 API 라우터 로드 성공")
        
        from utils.coding_assistant.code_parser import CodeParser, CodeLanguage
        print("✅ 코드 파서 유틸리티 로드 성공")
        
        from utils.coding_assistant.template_manager import template_manager
        print("✅ 템플릿 매니저 로드 성공")
        
        from tools.coding_assistant.code_generation_tool import code_generation_node
        print("✅ 코드 생성 도구 로드 성공")
        
        from tools.coding_assistant.code_review_tool import code_review_node
        print("✅ 코드 리뷰 도구 로드 성공")
        
        from tools.coding_assistant.code_refactoring_tool import code_refactoring_node
        print("✅ 코드 리팩토링 도구 로드 성공")
        
        from tools.coding_assistant.test_generation_tool import test_generation_node
        print("✅ 테스트 생성 도구 로드 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ Import 오류: {e}")
        return False

def test_code_parser():
    """코드 파서 기능 테스트"""
    try:
        from utils.coding_assistant.code_parser import CodeParser, CodeLanguage
        
        # Python 코드 테스트
        python_code = '''
def hello_world(name):
    """Say hello to someone"""
    return f"Hello, {name}!"

class Greeter:
    def __init__(self, greeting="Hello"):
        self.greeting = greeting
    
    def greet(self, name):
        return f"{self.greeting}, {name}!"
'''
        
        # 언어 감지 테스트
        detected_lang = CodeParser.detect_language(python_code)
        print(f"✅ 언어 감지: {detected_lang}")
        
        # 함수 파싱 테스트
        functions = CodeParser.parse_python_functions(python_code)
        print(f"✅ 함수 파싱: {len(functions)}개 함수 발견")
        for func in functions:
            print(f"   - {func.name}({', '.join(func.parameters)})")
        
        # 클래스 파싱 테스트
        classes = CodeParser.parse_python_classes(python_code)
        print(f"✅ 클래스 파싱: {len(classes)}개 클래스 발견")
        for cls in classes:
            print(f"   - {cls.name} (메서드 {len(cls.methods)}개)")
        
        # 라인 통계 테스트
        line_stats = CodeParser.count_lines_of_code(python_code)
        print(f"✅ 라인 통계: 총 {line_stats['total']}줄, 코드 {line_stats['code']}줄")
        
        return True
        
    except Exception as e:
        print(f"❌ 코드 파서 테스트 오류: {e}")
        return False

def test_template_manager():
    """템플릿 매니저 기능 테스트"""
    try:
        from utils.coding_assistant.template_manager import template_manager, TemplateType
        
        # 템플릿 목록 조회
        all_templates = list(template_manager.templates.keys())
        print(f"✅ 로드된 템플릿: {len(all_templates)}개")
        
        # Python 함수 템플릿 테스트
        python_templates = template_manager.get_templates_by_language("python")
        print(f"✅ Python 템플릿: {len(python_templates)}개")
        
        # 템플릿 렌더링 테스트
        variables = {
            "function_name": "calculate_sum",
            "parameters": "numbers: List[int]",
            "return_type": "int",
            "description": "Calculate the sum of a list of numbers",
            "args_doc": "numbers: List of integers to sum",
            "return_doc": "The sum of all numbers",
            "body": "    return sum(numbers)"
        }
        
        rendered = template_manager.render_template("python_function", variables)
        if rendered:
            print("✅ 템플릿 렌더링 성공")
            print("   렌더링된 코드 미리보기:")
            print("   " + rendered.split('\n')[0])
        
        return True
        
    except Exception as e:
        print(f"❌ 템플릿 매니저 테스트 오류: {e}")
        return False

def test_api_endpoints():
    """API 엔드포인트 구조 테스트"""
    try:
        from api.coding_assistant.code_api import router
        
        # 라우터의 경로들 확인
        routes = [route.path for route in router.routes]
        print(f"✅ API 엔드포인트: {len(routes)}개")
        for route in routes:
            print(f"   - {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ API 엔드포인트 테스트 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🧪 코딩어시스턴트 기능 테스트 시작\n")
    
    tests = [
        ("모듈 Import", test_imports),
        ("코드 파서", test_code_parser),
        ("템플릿 매니저", test_template_manager),
        ("API 엔드포인트", test_api_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name} 테스트:")
        if test_func():
            passed += 1
            print(f"✅ {test_name} 테스트 통과")
        else:
            print(f"❌ {test_name} 테스트 실패")
    
    print(f"\n🎯 테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        return True
    else:
        print("⚠️  일부 테스트가 실패했습니다.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)