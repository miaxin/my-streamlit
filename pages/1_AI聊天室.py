# pages/1_🤖_AI_聊天室.py
import streamlit as st
import google.generativeai as genai
import os

# --- Gemini API Configuration ---
# 確保 API key 已配置
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Gemini API key not found in .streamlit/secrets.toml. 請確保您的主應用程式檔案已配置 API key。")
    st.stop()
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 初始化 Gemini Pro 模型和聊天會話
# 使用 st.cache_resource 來快取模型，避免每次頁面重新運行時都重新初始化
@st.cache_resource(ttl="30min") 
def get_gemini_model():
    try:
        return genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        st.error(f"未能初始化 Gemini 模型: {e}")
        st.stop()

gemini_model = get_gemini_model()

# 初始化聊天會話，並將歷史記錄儲存在 session_state 中
if "chat" not in st.session_state:
    st.session_state.chat = gemini_model.start_chat(history=[])

st.title("💬 AI 財務聊天機器人")
st.markdown("---")
st.write("您好！我是您的 AI 財務分析助理。您可以問我任何關於財務分析、市場趨勢或您上傳數據中公司的問題。")
st.write("請輸入您的問題，我會盡力為您提供幫助。")

# 顯示聊天歷史記錄
for message in st.session_state.chat.history:
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# 聊天輸入框
user_query = st.chat_input("請輸入您的問題...")

if user_query:
    # 將用戶消息添加到聊天歷史並顯示
    with st.chat_message("user"):
        st.markdown(user_query)
    
    # 獲取 AI 回覆
    with st.chat_message("assistant"):
        with st.spinner("AI 思考中..."):
            try:
                # 嘗試將處理後的 DataFrame 傳遞給 AI，以提供上下文
                # 注意：這是一個簡單的示例，實際應用中可能需要更複雜的數據傳遞機制
                processed_df_str = ""
                if 'processed_df' in st.session_state:
                    # 考慮數據量，只傳遞部分數據或摘要
                    df_summary = st.session_state['processed_df'].head().to_markdown(index=False)
                    processed_df_str = f"\n\n以下是您上傳的數據摘要 (如果相關)：\n{df_summary}\n\n"
                    # 也可以只傳遞當前選定公司的數據
                    # if 'selected_company' in st.session_state and st.session_state.selected_company:
                    #     company_data = st.session_state['processed_df'][st.session_state['processed_df']['Name'] == st.session_state.selected_company].iloc[0].to_dict()
                    #     processed_df_str += f"\n當前選定的公司 {st.session_state.selected_company} 的數據：{company_data}\n"

                full_prompt = f"{user_query}{processed_df_str}\n請用中文回答。"
                response = st.session_state.chat.send_message(full_prompt)
                
                if response and response.text:
                    st.markdown(response.text)
                else:
                    st.warning("AI 無法生成回覆，請稍後再試。")
            except Exception as e:
                st.error(f"聊天機器人錯誤: {e}")