import streamlit as st
import openai

# 페이지 설정
st.set_page_config(page_title="CoE-Backend Chat", page_icon="🤖")
st.title("🤖 CoE-Backend Chat")

# OpenAI 호환 클라이언트 (백엔드 주소)
client = openai.OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")

CONTEXT_OPTIONS = ("aider", "continue.dev", "openWebUi")

# 옵션 및 기본값
if "context" not in st.session_state:
    st.session_state.context = "openWebUi"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "model_name" not in st.session_state:
    st.session_state.model_name = "gpt-4o"
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = ""
if "chat_input_value" not in st.session_state:
    st.session_state.chat_input_value = ""

# 이전 대화 렌더링
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 메시지 처리 및 어시스턴트 응답 (prompt가 있을 경우)
if st.session_state.current_prompt:
    prompt = st.session_state.current_prompt
    # 사용자 메시지 저장/표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 어시스턴트 응답
    with st.chat_message("assistant"):
        ph = st.empty()
        full = ""
        try:
            stream = client.chat.completions.create(
                model=st.session_state.model_name,
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                stream=True,
                extra_body={"context": st.session_state.context},  # 👈 하단 콤보박스 값 사용
            )
            for chunk in stream:
                full += (chunk.choices[0].delta.content or "")
                ph.markdown(full + "▌")
            ph.markdown(full)
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
            full = f"오류: {e}"

    st.session_state.messages.append({"role": "assistant", "content": full})
    st.session_state.current_prompt = ""
    st.session_state.chat_input_value = ""

# === 하단 컨트롤 바 (입력창 및 옵션) ===
bottom_container = st.container()
with bottom_container:
    st.text_input(
        "무엇이든 물어보세요!",
        key="chat_input",
        on_change=lambda: st.session_state.update(current_prompt=st.session_state.chat_input),
        value=st.session_state.chat_input_value
    )

    cols = st.columns([1, 2, 3])  # 필요에 맞춰 비율 조정
    with cols[0]:
        st.caption("Context")
        st.session_state.context = st.selectbox(
            label="요청 컨텍스트",
            options=CONTEXT_OPTIONS,
            index=CONTEXT_OPTIONS.index(st.session_state.context),
            key="context_select",
            label_visibility="collapsed",
        )
    with cols[1]:
        st.caption("모델")
        st.session_state.model_name = st.text_input("모델", value=st.session_state.model_name, label_visibility="collapsed", key="model_name_input")
    with cols[2]:
        st.caption("정보")
        st.write(f"선택됨: `{st.session_state.context}`")