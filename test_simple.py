#!/usr/bin/env python3
"""
간단한 테스트 실행 스크립트
"""

def test_basic_import():
    """기본 import 테스트"""
    try:
        from core.schemas import Message
        print("✅ core.schemas import successful")
        return True
    except Exception as e:
        print(f"❌ core.schemas import failed: {e}")
        return False

def test_pydantic_model():
    """Pydantic 모델 테스트"""
    try:
        from core.schemas import Message
        msg = Message(role="user", content="test")
        print(f"✅ Message model created: {msg}")
        return True
    except Exception as e:
        print(f"❌ Message model test failed: {e}")
        return False

def test_basic_tools():
    """기본 도구 테스트"""
    try:
        from tools.basic_tools import tool1_node, basic_tool_descriptions
        print("✅ basic_tools import successful")
        print(f"✅ Found {len(basic_tool_descriptions)} tool descriptions")
        return True
    except Exception as e:
        print(f"❌ basic_tools import failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running simple tests...")
    
    tests = [
        test_basic_import,
        test_pydantic_model,
        test_basic_tools
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        exit(0)
    else:
        print("💥 Some tests failed!")
        exit(1)