import os
import requests
from typing import Dict, Any, List
from urllib.parse import quote

# Assume project_root is known
PROJECT_ROOT = "/Users/a08418/Documents/CoE/CoE-Backend/"

def _resolve_path(relative_path: str) -> str:
    """Resolves a relative path to an absolute path within the project root."""
    return os.path.join(PROJECT_ROOT, relative_path)

# --- Tool Implementations ---

def search_web(query: str) -> str:
    """
    DuckDuckGo Instant Answer API를 사용해 웹 검색을 수행합니다.
    """
    try:
        encoded_query = quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        results = []

        if data.get('Abstract'):
            results.append(f"Summary: {data['Abstract']}")

        if data.get('RelatedTopics'):
            results.append("Related Topics:")
            for topic in data['RelatedTopics'][:3]:
                if 'Text' in topic and 'FirstURL' in topic:
                    results.append(f"- {topic['Text'][:100]}... [{topic['FirstURL']}]")

        if data.get('Answer'):
            results.append(f"Answer: {data['Answer']}")

        if results:
            return "\n".join(results)
        else:
            return f"No web search results found for query '{query}'"

    except Exception as e:
        return f"Error performing web search for '{query}': {str(e)}"

def fetch_url_content(url: str) -> str:
    """
    URL의 웹 문서를 가져옵니다(파일 취득용 아님).
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL content from {url}: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred while fetching URL content: {str(e)}"

# New tool implementations using default_api
def read_file(filepath: str) -> str:
    """
    워크스페이스 루트 기준 상대 경로의 파일 내용을 읽습니다.
    """
    absolute_path = _resolve_path(filepath)
    try:
        # Using default_api.read_file
        result = default_api.read_file(absolute_path=absolute_path)
        if 'content' in result:
            return result['content']
        else:
            return f"Error reading file {filepath}: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error reading file {filepath}: {str(e)}"

def create_new_file(filepath: str, contents: str) -> str:
    """
    새 파일을 생성하고 내용을 작성합니다.
    """
    absolute_path = _resolve_path(filepath)
    try:
        # Using default_api.write_file
        result = default_api.write_file(file_path=absolute_path, content=contents)
        if 'success' in result and result['success']:
            return f"Successfully created file: {filepath}"
        else:
            return f"Error creating file {filepath}: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error creating file {filepath}: {str(e)}"

def grep_search(query: str) -> str:
    """
    ripgrep 정규식으로 저장소 내 텍스트 검색을 수행합니다(출력은 길이 제한 가능).
    """
    try:
        # Using default_api.search_file_content
        result = default_api.search_file_content(pattern=query, path=PROJECT_ROOT)
        if 'matches' in result:
            if not result['matches']:
                return f"No matches found for query '{query}'."
            formatted_matches = []
            for match in result['matches']:
                formatted_matches.append(f"{match['file_path']}:{match['line_number']}: {match['line_content']}")
            return "\n".join(formatted_matches)
        else:
            return f"Error performing grep search for '{query}': {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error performing grep search for '{query}': {str(e)}"

def file_glob_search(pattern: str) -> str:
    """
    글롭 패턴으로 프로젝트 내 파일 경로를 검색합니다. `**` 재귀 패턴 지원.
    """
    try:
        # Using default_api.glob
        result = default_api.glob(pattern=pattern, path=PROJECT_ROOT)
        if 'files' in result:
            if not result['files']:
                return f"No files found matching pattern '{pattern}'."
            return "\n".join(result['files'])
        else:
            return f"Error performing file glob search for '{pattern}': {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error performing file glob search for '{pattern}': {str(e)}"

def view_diff() -> str:
    """
    현재 워킹 디렉토리의 git diff를 확인합니다.
    """
    try:
        # Using default_api.run_shell_command
        result = default_api.run_shell_command(command="git diff", directory=PROJECT_ROOT)
        if 'stdout' in result:
            return result['stdout']
        else:
            return f"Error viewing diff: {result.get('stderr', 'Unknown error')}"
    except Exception as e:
        return f"Error viewing diff: {str(e)}"

def ls(dirPath: str = ".", recursive: bool = False) -> str:
    """
    지정 디렉토리의 파일/폴더 목록을 확인합니다.
    Note: 'recursive' parameter is not fully supported by the underlying tool,
    only direct children will be listed.
    """
    absolute_path = _resolve_path(dirPath)
    try:
        # Using default_api.list_directory
        result = default_api.list_directory(path=absolute_path)
        if 'entries' in result:
            if not result['entries']:
                return f"Directory '{dirPath}' is empty."
            return "\n".join(result['entries'])
        else:
            return f"Error listing directory '{dirPath}': {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error listing directory '{dirPath}': {str(e)}"

def run_terminal_command(command: str, waitForCompletion: bool = True) -> str:
    """
    현재 디렉토리에서 터미널 명령어를 실행합니다. 셸 상태는 매 호출마다 초기화되며, 관리자 권한 작업은 금지됩니다.
    """
    full_command = command
    if not waitForCompletion:
        full_command += " &" # Run in background

    try:
        # Using default_api.run_shell_command
        result = default_api.run_shell_command(command=full_command, directory=PROJECT_ROOT)
        if 'stdout' in result:
            output = result['stdout']
            if result.get('stderr'):
                output += f"\nStderr: {result['stderr']}"
            if result.get('error'):
                output += f"\nError: {result['error']}"
            return output
        else:
            return f"Error running command '{command}': {result.get('stderr', 'Unknown error')}"
    except Exception as e:
        return f"Error running command '{command}': {str(e)}"

# Placeholder for tools not directly supported
def read_currently_open_file() -> str:
    """
    IDE에서 현재 열려 있는 파일의 내용을 읽습니다. (현재 지원되지 않음)
    """
    return "This tool is specific to IDE integration and is not supported by the current backend."

def edit_existing_file(filepath: str, changes: str) -> str:
    """
    기존 파일에 변경사항을 적용합니다. (현재 지원되지 않음: 복잡한 패치 적용 필요)
    """
    return "This tool requires complex patching logic not directly supported by available tools."

def search_and_replace_in_file(filepath: str, diffs: List[str]) -> str:
    """
    파일의 특정 구간을 SEARCH/REPLACE 블록들로 정의해 정확히 치환합니다. (현재 지원되지 않음: diffs 형식 불분명)
    """
    return "This tool requires a specific 'diffs' format which is not defined or supported."


# --- OpenAI Compatible Tool Schemas ---

search_web_schema = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "외부 웹을 검색해 상위 결과를 반환합니다(필요 시에만 사용 권장).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "자연어 검색어",
                }
            },
            "required": ["query"],
        },
    },
}

fetch_url_content_schema = {
    "type": "function",
    "function": {
        "name": "fetch_url_content",
        "description": "URL의 웹 문서를 가져옵니다(파일 취득용 아님).",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "가져올 URL",
                }
            },
            "required": ["url"],
        },
    },
}

read_file_schema = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "워크스페이스 루트 기준 상대 경로의 파일 내용을 읽습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "읽을 파일 경로 (상대 경로)",
                }
            },
            "required": ["filepath"],
        },
    },
}

create_new_file_schema = {
    "type": "function",
    "function": {
        "name": "create_new_file",
        "description": "새 파일을 생성하고 내용을 작성합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "생성할 파일 경로 (상대 경로)",
                },
                "contents": {
                    "type": "string",
                    "description": "파일 내용",
                },
            },
            "required": ["filepath", "contents"],
        },
    },
}

grep_search_schema = {
    "type": "function",
    "function": {
        "name": "grep_search",
        "description": "ripgrep 정규식으로 저장소 내 텍스트 검색을 수행합니다(출력은 길이 제한 가능).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "ripgrep 정규식 쿼리",
                }
            },
            "required": ["query"],
        },
    },
}

file_glob_search_schema = {
    "type": "function",
    "function": {
        "name": "file_glob_search",
        "description": "글롭 패턴으로 프로젝트 내 파일 경로를 검색합니다. `**` 재귀 패턴 지원.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "글롭 패턴",
                }
            },
            "required": ["pattern"],
        },
    },
}

view_diff_schema = {
    "type": "function",
    "function": {
        "name": "view_diff",
        "description": "현재 워킹 디렉토리의 git diff를 확인합니다.",
        "parameters": {
            "type": "object",
            "properties": {}, # No parameters
            "required": [],
        },
    },
}

ls_schema = {
    "type": "function",
    "function": {
        "name": "ls",
        "description": "지정 디렉토리의 파일/폴더 목록을 확인합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "dirPath": {
                    "type": "string",
                    "description": "루트 기준 디렉토리 경로. 기본값 권장 경로 사용 가능",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "재귀 목록 여부(남용 금지)",
                },
            },
            "required": [], # dirPath and recursive are optional
        },
    },
}

run_terminal_command_schema = {
    "type": "function",
    "function": {
        "name": "run_terminal_command",
        "description": "현재 디렉토리에서 터미널 명령어를 실행합니다. 셸 상태는 매 호출마다 초기화되며, 관리자 권한 작업은 금지됩니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "실행할 명령어",
                },
                "waitForCompletion": {
                    "type": "boolean",
                    "description": "default true; false면 백그라운드 실행",
                },
            },
            "required": ["command"],
        },
    },
}

# Schemas for placeholder tools
read_currently_open_file_schema = {
    "type": "function",
    "function": {
        "name": "read_currently_open_file",
        "description": "IDE에서 현재 열려 있는 파일의 내용을 읽습니다. (현재 지원되지 않음)",
        "parameters": {
            "type": "object",
            "properties": {}, 
            "required": [],
        },
    },
}

edit_existing_file_schema = {
    "type": "function",
    "function": {
        "name": "edit_existing_file",
        "description": "기존 파일에 변경사항을 적용합니다. (현재 지원되지 않음: 복잡한 패치 적용 필요)",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": { "type": "string" },
                "changes": { "type": "string" },
            },
            "required": ["filepath", "changes"],
        },
    },
}

search_and_replace_in_file_schema = {
    "type": "function",
    "function": {
        "name": "search_and_replace_in_file",
        "description": "파일의 특정 구간을 SEARCH/REPLACE 블록들로 정의해 정확히 치환합니다. (현재 지원되지 않음: diffs 형식 불분명)",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": { "type": "string" },
                "diffs": { "type": "array", "items": { "type": "string" } },
            },
            "required": ["filepath", "diffs"],
        },
    },
}

# --- Registry Variables ---

available_tools: List[Dict[str, Any]] = [
    search_web_schema,
    fetch_url_content_schema,
    read_file_schema,
    create_new_file_schema,
    grep_search_schema,
    file_glob_search_schema,
    view_diff_schema,
    ls_schema,
    run_terminal_command_schema,
    read_currently_open_file_schema,
    edit_existing_file_schema,
    search_and_replace_in_file_schema,
]

tool_functions: Dict[str, callable] = {
    "search_web": search_web,
    "fetch_url_content": fetch_url_content,
    "read_file": read_file,
    "create_new_file": create_new_file,
    "grep_search": grep_search,
    "file_glob_search": file_glob_search,
    "view_diff": view_diff,
    "ls": ls,
    "run_terminal_command": run_terminal_command,
    "read_currently_open_file": read_currently_open_file,
    "edit_existing_file": edit_existing_file,
    "search_and_replace_in_file": search_and_replace_in_file,
}