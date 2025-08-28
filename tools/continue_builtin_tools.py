from typing import List, Dict, Any

# --- Continue Built-in Tool Schemas (from continue-tools-integration.md) ---
READ_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "워크스페이스 루트 기준 상대 경로의 파일 내용을 읽습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "읽을 파일 경로 (상대 경로)"}
            },
            "required": ["filepath"]
        }
    }
}

READ_CURRENTLY_OPEN_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_currently_open_file",
        "description": "IDE에서 현재 열려 있는 파일의 내용을 읽습니다.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}

CREATE_NEW_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_new_file",
        "description": "새 파일을 생성하고 내용을 작성합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "생성할 파일 경로 (상대 경로)"},
                "contents": {"type": "string", "description": "파일 내용"}
            },
            "required": ["filepath", "contents"]
        }
    }
}

EDIT_EXISTING_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "edit_existing_file",
        "description": "기존 파일에 변경사항을 적용합니다. 큰 파일의 경우 변경이 없는 영역은 언어 적합한 축약 표기(예: // ... existing code ...)를 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "수정할 파일 경로 (상대 경로)"},
                "changes": {"type": "string", "description": "적용할 변경 텍스트(검색/치환이 아닌 최종 편집 결과)"}
            },
            "required": ["filepath", "changes"]
        }
    }
}

SEARCH_AND_REPLACE_IN_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_and_replace_in_file",
        "description": "파일의 특정 구간을 SEARCH/REPLACE 블록들로 정의해 정확히 치환합니다. 병렬 호출 금지.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "diffs": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["filepath", "diffs"]
        }
    }
}

GREP_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "grep_search",
        "description": "ripgrep 정규식으로 저장소 내 텍스트 검색을 수행합니다(출력은 길이 제한 가능).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "ripgrep 정규식 쿼리"}
            },
            "required": ["query"]
        }
    }
}

FILE_GLOB_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "file_glob_search",
        "description": "글롭 패턴으로 프로젝트 내 파일 경로를 검색합니다. ** 재귀 패턴 지원.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "글롭 패턴"}
            },
            "required": ["pattern"]
        }
    }
}

SEARCH_WEB_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "외부 웹을 검색해 상위 결과를 반환합니다(필요 시에만 사용 권장).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "자연어 검색어"}
            },
            "required": ["query"]
        }
    }
}

VIEW_DIFF_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "view_diff",
        "description": "현재 워킹 디렉토리의 git diff를 확인합니다.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}

LS_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "ls",
        "description": "지정 디렉토리의 파일/폴더 목록을 확인합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "dirPath": {"type": "string", "description": "루트 기준 디렉토리 경로. 기본값 권장 경로 사용 가능"},
                "recursive": {"type": "boolean", "description": "재귀 목록 여부(남용 금지)"}
            },
            "required": []
        }
    }
}

FETCH_URL_CONTENT_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "fetch_url_content",
        "description": "URL의 웹 문서를 가져옵니다(파일 취득용 아님).",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL"}
            },
            "required": ["url"]
        }
    }
}

CREATE_RULE_BLOCK_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_rule_block",
        "description": "향후 대화/생성에 적용할 규칙(rule)을 생성·저장합니다. 기존 규칙 수정은 편집 도구 사용.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "rule": {"type": "string"},
                "description": {"type": "string"},
                "globs": {"type": "string"},
                "regex": {"type": "string"},
                "alwaysApply": {"type": "boolean"}
            },
            "required": ["name", "rule"]
        }
    }
}

REQUEST_RULE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "request_rule",
        "description": "사용 가능한 rule 목록에서 이름으로 특정 rule의 내용을 요청합니다(일부 설정에서만 노출).",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
    }
}

RUN_TERMINAL_COMMAND_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_terminal_command",
        "description": "현재 디렉토리에서 터미널 명령어를 실행합니다. 셸 상태는 매 호출마다 초기화되며, 관리자 권한 작업은 금지됩니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "waitForCompletion": {"type": "boolean", "description": "default true; false면 백그라운드 실행"}
            },
            "required": ["command"]
        }
    }
}

CODEBASE_TOOL_SCHEMA = { # This one is mentioned in the list but no schema provided, assuming simple
    "type": "function",
    "function": {
        "name": "codebase",
        "description": "코드베이스 관련 작업을 수행합니다. (자세한 설명 필요)",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}

ALL_CONTINUE_BUILT_IN_TOOL_SCHEMAS = [
    READ_FILE_TOOL_SCHEMA,
    READ_CURRENTLY_OPEN_FILE_TOOL_SCHEMA,
    CREATE_NEW_FILE_TOOL_SCHEMA,
    EDIT_EXISTING_FILE_TOOL_SCHEMA,
    SEARCH_AND_REPLACE_IN_FILE_TOOL_SCHEMA,
    GREP_SEARCH_TOOL_SCHEMA,
    FILE_GLOB_SEARCH_TOOL_SCHEMA,
    SEARCH_WEB_TOOL_SCHEMA,
    VIEW_DIFF_TOOL_SCHEMA,
    LS_TOOL_SCHEMA,
    FETCH_URL_CONTENT_TOOL_SCHEMA,
    CREATE_RULE_BLOCK_TOOL_SCHEMA,
    REQUEST_RULE_TOOL_SCHEMA,
    RUN_TERMINAL_COMMAND_TOOL_SCHEMA,
    CODEBASE_TOOL_SCHEMA,
]
