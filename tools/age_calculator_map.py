# 이 도구가 사용될 수 있는 컨텍스트를 정의합니다.
tool_contexts = [
    "aider",
    "continue.dev"
]

allowed_groups = ["coe"]

# 도구를 직접 호출할 수 있는 API 엔드포인트를 정의합니다. (선택 사항)
endpoints = {
    "calculate_international_age": "/tools/calculate-age"
}
