# 이 도구가 사용될 수 있는 컨텍스트를 정의합니다.
# 사용자의 요청에 따라, 현재 정의된 모든 컨텍스트에 추가합니다.
tool_contexts = [
    "aider",
    "continue.dev",
    "openWebUi"
]

# 도구의 직접 호출을 위한 API 엔드포인트를 정의합니다.
endpoints = {
    "visualize_conversation_as_langflow": "/tools/visualize-conversation-as-langflow",
    "generate_langflow_workflow": "/tools/generate-langflow-workflow"
}