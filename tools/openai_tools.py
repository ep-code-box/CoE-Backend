"""
OpenAI 호환 도구들을 정의합니다.
파일 시스템 및 터미널 상호작용을 지원하는 도구들을 포함합니다.
"""
import os
import json
import subprocess
import glob # Added for file_glob_search
import requests # Added for fetch_url_content
from typing import Dict, Any, List, Optional

# --- Constants ---
# 현재 작업 디렉토리를 프로젝트 루트로 가정합니다.
PROJECT_ROOT = os.getcwd()

# --- Helper Functions ---

def _get_absolute_path(filepath: str) -> str:
    """
    상대 경로를 절대 경로로 변환하고, 프로젝트 루트 내에 있는지 확인합니다.
    보안을 위해 프로젝트 디렉토리 외부 접근을 방지합니다.
    """
    if not os.path.isabs(filepath):
        absolute_path = os.path.join(PROJECT_ROOT, filepath)
    else:
        absolute_path = filepath
    
    absolute_path = os.path.normpath(absolute_path)
    
    if not absolute_path.startswith(PROJECT_ROOT):
        raise ValueError(f"Access denied: Path '{filepath}' is outside the project directory.")
    
    return absolute_path

# --- Tool Implementations ---

def read_file(filepath: str) -> str:
    """
    지정된 경로의 파일 내용을 읽어 반환합니다.
    파일이 존재하지 않거나 접근 권한이 없는 경우 오류 메시지를 반환합니다.
    """
    try:
        abs_path = _get_absolute_path(filepath)
        if not os.path.exists(abs_path):
            return f"Error: File not found at '{filepath}' (resolved to '{abs_path}')"
        
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except ValueError as ve:
        return f"Error: {ve}"
    except Exception as e:
        return f"Error reading file '{filepath}': {str(e)}"

def read_currently_open_file() -> str:
    """
    IDE에서 현재 열려 있는 파일의 내용을 읽습니다.
    이 기능은 백엔드에서 직접 구현할 수 없으므로 오류를 반환합니다.
    """
    return "Error: This tool requires direct IDE integration and cannot be executed by the backend."

def create_new_file(filepath: str, contents: str) -> str:
    """
    새 파일을 생성하고 내용을 작성합니다. 파일이 이미 존재하면 덮어씁니다.
    필요한 경우 상위 디렉토리를 자동으로 생성합니다.
    """
    try:
        abs_path = _get_absolute_path(filepath)
        
        os.makedirs(os.path.dirname(abs_path), exist_ok=True) # 디렉토리가 존재하지 않으면 생성

        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(contents)
        
        return f"Success: File '{filepath}' created/overwritten."
    except ValueError as ve:
        return f"Error: {ve}"
    except Exception as e:
        return f"Error creating file '{filepath}': {str(e)}"

def edit_existing_file(filepath: str, changes: str) -> str:
    """
    기존 파일에 변경사항을 적용합니다.
    현재는 파일 내용을 'changes'로 완전히 덮어쓰는 방식으로 구현됩니다.
    """
    try:
        abs_path = _get_absolute_path(filepath)
        if not os.path.exists(abs_path):
            return f"Error: File not found at '{filepath}' (resolved to '{abs_path}')"
        
        with open(abs_path, 'w', encoding='utf-8') as f: # Overwrite with new content
            f.write(changes)
        
        return f"Success: File '{filepath}' updated."
    except ValueError as ve:
        return f"Error: {ve}"
    except Exception as e:
        return f"Error editing file '{filepath}': {str(e)}"

def search_and_replace_in_file(filepath: str, search_string: str, replace_string: str) -> str:
    """
    파일의 특정 구간을 검색하여 치환합니다.
    현재는 파일 내의 모든 'search_string'을 'replace_string'으로 치환합니다.
    """
    try:
        abs_path = _get_absolute_path(filepath)
        if not os.path.exists(abs_path):
            return f"Error: File not found at '{filepath}' (resolved to '{abs_path}')"
        
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = content.replace(search_string, replace_string)
        
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return f"Success: Replaced all occurrences of '{search_string}' with '{replace_string}' in '{filepath}'."
    except ValueError as ve:
        return f"Error: {ve}"
    except Exception as e:
        return f"Error performing search and replace in '{filepath}': {str(e)}"

def grep_search(query: str) -> str:
    """
    ripgrep 정규식으로 저장소 내 텍스트 검색을 수행합니다.
    이 기능은 백엔드에서 직접 ripgrep을 실행해야 하므로 현재는 구현되지 않았습니다.
    """
    return "Error: `grep_search` requires `ripgrep` to be installed and configured on the host system. This tool is not fully implemented in the backend."

def file_glob_search(pattern: str) -> str:
    """
    글롭 패턴으로 프로젝트 내 파일 경로를 검색합니다. `**` 재귀 패턴을 지원합니다.
    """
    try:
        matching_files = []
        # glob.glob은 현재 작업 디렉토리를 기준으로 작동하므로,
        # PROJECT_ROOT 내에서만 작동하도록 패턴을 조정합니다.
        # 예: pattern = "**/*.py" -> os.path.join(PROJECT_ROOT, "**/*.py")
        full_pattern = os.path.join(PROJECT_ROOT, pattern)
        
        # glob.glob은 절대 경로를 반환하므로, PROJECT_ROOT에 대한 상대 경로로 변환
        for f in glob.glob(full_pattern, recursive=True):
            if f.startswith(PROJECT_ROOT):
                matching_files.append(os.path.relpath(f, PROJECT_ROOT))
        
        if not matching_files:
            return f"No files found matching pattern '{pattern}'."
        
        return "\n".join(sorted(matching_files))
    except Exception as e:
        return f"Error performing glob search with pattern '{pattern}': {str(e)}"

def search_web(query: str) -> str:
    """
    외부 웹을 검색해 상위 결과를 반환합니다.
    이 기능은 외부 웹 검색 API가 필요하므로 현재는 구현되지 않았습니다.
    """
    return "Error: Web search functionality is not implemented in the backend. Please provide search results manually if needed."

def view_diff() -> str:
    """
    현재 워킹 디렉토리의 git diff를 확인합니다.
    이 기능은 Git이 설치되어 있어야 하며, 프로젝트가 Git 저장소여야 합니다.
    """
    return "Error: `view_diff` requires Git to be installed and the project to be a Git repository. This tool is not fully implemented in the backend."

def ls(dirPath: Optional[str] = ".", recursive: bool = False) -> str:
    """
    지정 디렉토리의 파일 및 폴더 목록을 확인합니다.
    'recursive'가 True인 경우 하위 디렉토리까지 재귀적으로 탐색합니다.
    """
    try:
        abs_path = _get_absolute_path(dirPath)
        
        if not os.path.isdir(abs_path):
            return f"Error: Directory not found at '{dirPath}' (resolved to '{abs_path}')"
        
        items = []
        if recursive:
            for root, dirs, files in os.walk(abs_path):
                for name in files:
                    items.append(os.path.relpath(os.path.join(root, name), PROJECT_ROOT))
                for name in dirs:
                    items.append(os.path.relpath(os.path.join(root, name), PROJECT_ROOT) + "/") # 디렉토리임을 표시
        else:
            for item in os.listdir(abs_path):
                full_path = os.path.join(abs_path, item)
                if os.path.isdir(full_path):
                    items.append(item + "/")
                else:
                    items.append(item)
        
        return "\n".join(sorted(items))
    except ValueError as ve:
        return f"Error: {ve}"
    except Exception as e:
        return f"Error listing directory '{dirPath}': {str(e)}"

def fetch_url_content(url: str) -> str:
    """
    URL의 웹 문서를 가져옵니다.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL content from '{url}': {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred while fetching URL '{url}': {str(e)}"

def create_rule_block(name: str, rule: str, description: Optional[str] = None, globs: Optional[str] = None, regex: Optional[str] = None, alwaysApply: Optional[bool] = None) -> str:
    """
    향후 대화/생성에 적용할 규칙(rule)을 생성·저장합니다.
    이 기능은 백엔드에서 규칙 관리 시스템이 필요하므로 현재는 구현되지 않았습니다.
    """
    return "Error: Rule management functionality is not implemented in the backend."

def request_rule(name: str) -> str:
    """
    사용 가능한 rule 목록에서 이름으로 특정 rule의 내용을 요청합니다.
    이 기능은 백엔드에서 규칙 관리 시스템이 필요하므로 현재는 구현되지 않았습니다.
    """
    return "Error: Rule management functionality is not implemented in the backend."

def run_terminal_command(command: str, waitForCompletion: bool = True) -> str:
    """
    현재 디렉토리에서 터미널 명령어를 실행합니다.
    'waitForCompletion'이 True인 경우 명령이 완료될 때까지 기다리고,
    False인 경우 백그라운드에서 실행합니다.
    """
    try:
        if waitForCompletion:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        else:
            subprocess.Popen(command, shell=True)
            return f"Command '{command}' started in background."
    except subprocess.CalledProcessError as e:
        return f"Error executing command '{command}':\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
    except Exception as e:
        return f"Error running terminal command '{command}': {str(e)}"

# --- OpenAI Compatible Tool Schemas ---

# read_file 스키마
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

# read_currently_open_file 스키마
read_currently_open_file_schema = {
    "type": "function",
    "function": {
        "name": "read_currently_open_file",
        "description": "IDE에서 현재 열려 있는 파일의 내용을 읽습니다.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

# create_new_file 스키마
create_new_file_schema = {
    "type": "function",
    "function": {
        "name": "create_new_file",
        "description": "새 파일을 생성하고 내용을 작성합니다. 파일이 이미 존재하면 덮어씁니다.",
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

# edit_existing_file 스키마
edit_existing_file_schema = {
    "type": "function",
    "function": {
        "name": "edit_existing_file",
        "description": "기존 파일에 변경사항을 적용합니다. 큰 파일의 경우 변경이 없는 영역은 언어 적합한 축약 표기(예: // ... existing code ...)를 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "수정할 파일 경로 (상대 경로)",
                },
                "changes": {
                    "type": "string",
                    "description": "적용할 변경 텍스트(검색/치환이 아닌 최종 편집 결과)",
                },
            },
            "required": ["filepath", "changes"],
        },
    },
}

# search_and_replace_in_file 스키마
search_and_replace_in_file_schema = {
    "type": "function",
    "function": {
        "name": "search_and_replace_in_file",
        "description": "파일의 특정 구간을 SEARCH/REPLACE 블록들로 정의해 정확히 치환합니다. 병렬 호출 금지.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "파일 경로 (상대 경로)",
                },
                "search_string": { "type": "string", "description": "찾을 문자열" },
                "replace_string": { "type": "string", "description": "바꿀 문자열" },
            },
            "required": ["filepath", "search_string", "replace_string"],
        },
    },
}

# grep_search 스키마
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

# file_glob_search 스키마
file_glob_search_schema = {
    "type": "function",
    "function": {
        "name": "file_glob_search",
        "description": "글롭 패턴으로 프로젝트 내 파일 경로를 검색합니다. ** 재귀 패턴 지원.",
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

# search_web 스키마
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

# view_diff 스키마
view_diff_schema = {
    "type": "function",
    "function": {
        "name": "view_diff",
        "description": "현재 워킹 디렉토리의 git diff를 확인합니다.",
        "parameters": {
            "type": "object",
            "properties": {}, 
            "required": [],
        },
    },
}

# ls 스키마
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
                    "description": "루트 기준 디렉토리 경로. 기본값은 현재 디렉토리.",
                    "default": "."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "재귀 목록 여부 (남용 금지)",
                    "default": False
                }
            },
            "required": [],
        },
    },
}

# fetch_url_content 스키마
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

# create_rule_block 스키마
create_rule_block_schema = {
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
                "alwaysApply": {"type": "boolean"},
            },
            "required": ["name", "rule"],
        },
    },
}

# request_rule 스키마
request_rule_schema = {
    "type": "function",
    "function": {
        "name": "request_rule",
        "description": "사용 가능한 rule 목록에서 이름으로 특정 rule의 내용을 요청합니다(일부 설정에서만 노출).",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
}

# run_terminal_command 스키마
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
                    "description": "실행할 터미널 명령어",
                },
                "waitForCompletion": {
                    "type": "boolean",
                    "description": "default true; false면 백그라운드 실행",
                    "default": True
                }
            },
            "required": ["command"],
        },
    },
}

# --- Registry Variables ---

# 서버에서 사용 가능한 Tool 목록
available_tools: List[Dict[str, Any]] = [
    read_file_schema,
    read_currently_open_file_schema,
    create_new_file_schema,
    edit_existing_file_schema,
    search_and_replace_in_file_schema,
    grep_search_schema,
    file_glob_search_schema,
    search_web_schema,
    view_diff_schema,
    ls_schema,
    fetch_url_content_schema,
    create_rule_block_schema,
    request_rule_schema,
    run_terminal_command_schema,
]

# Tool 이름과 실제 함수 구현을 매핑
tool_functions: Dict[str, callable] = {
    "read_file": read_file,
    "read_currently_open_file": read_currently_open_file,
    "create_new_file": create_new_file,
    "edit_existing_file": edit_existing_file,
    "search_and_replace_in_file": search_and_replace_in_file,
    "grep_search": grep_search,
    "file_glob_search": file_glob_search,
    "search_web": search_web,
    "view_diff": view_diff,
    "ls": ls,
    "fetch_url_content": fetch_url_content,
    "create_rule_block": create_rule_block,
    "request_rule": request_rule,
    "run_terminal_command": run_terminal_command,
}