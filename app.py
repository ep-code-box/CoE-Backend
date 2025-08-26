import streamlit as st
import openai

# Streamlit 페이지 설정
st.set_page_config(page_title="CoE-Backend Chat", page_icon="🤖")
st.title("🤖 CoE-Backend Chat")

# OpenAI 클라이언트 설정
# 백엔드의 주소를 기본 URL로 사용합니다.
client = openai.OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")

# 세션 상태에서 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 이전 대화 내용 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("무엇이든 물어보세요!"):
    # 사용자 메시지를 채팅 기록에 추가하고 화면에 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 어시스턴트 응답 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            # OpenAI 호환 API 호출
            stream = client.chat.completions.create(
                model="gpt-4o",  # 테스트를 위해 모델 변경
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
                extra_body={"context": "openWebUi"} # context 값 추가
            )
            # 스트리밍 응답 처리
            for chunk in stream:
                full_response += (chunk.choices[0].delta.content or "")
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
            full_response = f"오류: {e}"

    # 어시스턴트의 전체 응답을 채팅 기록에 추가
    st.session_state.messages.append({"role": "assistant", "content": full_response})