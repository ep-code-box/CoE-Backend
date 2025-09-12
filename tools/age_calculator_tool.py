from typing import Dict, Any, List, Optional
from core.schemas import AgentState
from datetime import datetime

# 1. 'run' 함수 (필수)
from typing import Dict, Any, List, Optional
from core.schemas import AgentState
from datetime import datetime

# 1. 'run' 함수 (필수)
async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """생년월일을 기준으로 만 나이를 계산합니다.

    주의: 인자 추출은 LLM의 tool call에 의해 이루어집니다. 이 함수는 제공된 인자만 사용합니다.
    """
    if not tool_input or 'birth_date' not in tool_input:
        return {"messages": [{"role": "assistant", "content": "생년월일을 'YYYY-MM-DD' 형식으로 알려주세요."}]}

    birth_date_str = tool_input['birth_date']
    # 다양한 구분자(., /)를 하이픈(-)으로 정규화합니다.
    normalized_date_str = str(birth_date_str).replace('.', '-').replace('/', '-')
    # 8자리 숫자를 허용하여 YYYY-MM-DD로 정규화
    if isinstance(birth_date_str, str) and len(birth_date_str) == 8 and birth_date_str.isdigit():
        normalized_date_str = f"{birth_date_str[0:4]}-{birth_date_str[4:6]}-{birth_date_str[6:8]}"

    try:
        birth_date = datetime.strptime(normalized_date_str, "%Y-%m-%d")
        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        result_message = f"생년월일 {birth_date.strftime('%Y-%m-%d')} 기준, 만 나이는 {age}세입니다."
        return {"messages": [{"role": "assistant", "content": result_message}]}
    except ValueError:
        return {"messages": [{"role": "assistant", "content": f"생년월일 형식('{birth_date_str}')을 이해할 수 없습니다. 'YYYY-MM-DD' 형식으로 입력해주세요."}]}

# 2. 'available_tools' 변수 (필수)
age_calculator_tool_schema = {
    "type": "function",
    "function": {
        "name": "calculate_international_age",
        "description": "Ai모델은 오늘날짜확인이 부정확 하므로 날짜관련은 최대한 서버툴을 사용합니다. 사용자의 생년월일을 기준으로 한국식 만 나이를 계산합니다. 현재 날짜와 생년월일을 비교하여, 올해 생일이 지났는지 여부를 따져 정확한 나이를 반환합니다. 예를 들어, '1990년 5월 10일생 나이 계산해줘'와 같은 요청에 사용할 수 있습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "birth_date": {
                    "type": "string",
                    "description": "계산할 생년월일. 'YYYY-MM-DD' 또는 'YYYY.MM.DD' 형식입니다."
                }
            },
            "required": ["birth_date"]
        }
    }
}

available_tools: List[Dict[str, Any]] = [age_calculator_tool_schema]

# 3. 'tool_functions' 변수 (필수)
tool_functions: Dict[str, callable] = {
    "calculate_international_age": run
}
