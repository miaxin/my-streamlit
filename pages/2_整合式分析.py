# pages/2_整合式分析.py
import streamlit as st
import openai

st.set_page_config(page_title="AI 專業經理人團隊整合分析", layout="wide")
st.title("📈 AI 專業經理人團隊整合分析")
st.markdown("模擬 CFO、COO、CEO 三位專家一次生成完整報告")

# --- 檢查 API Key ---
if "GOOGLE_API_KEY" not in st.session_state or not st.session_state["GOOGLE_API_KEY"]:
    st.info("請先在首頁輸入 API Key")
    st.stop()
else:
    api_key = st.session_state["GOOGLE_API_KEY"]
    openai.api_key = api_key

# --- 使用者輸入 ---
business_question = st.text_area(
    "請輸入您的商業問題或分析需求",
    placeholder="例如：請分析新產品的投資回報與營運風險..."
)

# --- 單次請求生成整合報告 ---
def single_call_analysis(question: str):
    prompt = f"""
模擬一個由 CFO、COO、CEO 組成的專家團隊，針對以下商業問題生成完整整合報告：
商業問題: {question}

報告要求：
1. 📊 CFO 分析: 財務指標、成本效益、投資回報。
2. 🏭 COO 分析: 營運可行性、流程與風險。
3. 👑 CEO 最終決策: 綜合以上觀點，提供戰略總結與後續行動建議。
"""
    response = openai.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "你是高階企業分析專家。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=2000
    )
    return response.choices[0].message.content

# --- 按鈕觸發 ---
if st.button("生成整合報告") and business_question.strip():
    with st.spinner("AI 專業經理人團隊正在進行全面分析..."):
        try:
            report = single_call_analysis(business_question)
            st.success("📈 AI 專業經理人團隊整合報告完成！")
            st.markdown(report)
        except openai.error.AuthenticationError:
            st.error("❌ API Key 驗證失敗，請確認 Key 是否正確或仍有效。")
        except Exception as e:
            st.error(f"❌ 發生錯誤：{e}")
