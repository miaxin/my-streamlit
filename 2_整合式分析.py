import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="智慧資料分析平台", layout="wide")
st.title("📊 智慧資料分析平台")

# --- 上傳 CSV 或輸入分析問題 ---
uploaded_file = st.file_uploader("請上傳 CSV 檔案 (可選)", type=["csv"])
st.markdown("---")

# --- 整合式 AI 專業經理人團隊分析 ---
st.header("🤖 整合式 AI 專業經理人團隊分析 (Single API Call)")

# 使用者輸入商業問題或分析需求
user_prompt = st.text_area(
    "請描述您的商業問題或分析需求：",
    placeholder="例如：分析本季度營運與財務表現，提供策略建議..."
)

if st.button("開始生成整合報告") and user_prompt.strip() != "":
    with st.spinner("AI 專業經理人團隊正在進行全面分析..."):
        # 組合專家角色說明
        full_prompt = f"""
你是由三位專家組成的團隊：
1. 📊 CFO 財務長: 從財務指標、成本效益、投資回報角度分析。
2. 🏭 COO 營運長: 評估營運可行性、潛在流程與風險。
3. 👑 CEO 執行長: 綜合 CFO 與 COO 的分析，提供戰略總結與明確行動建議。

請基於以下使用者需求生成一份完整的整合報告，分為三個部分：
使用者需求: {user_prompt}
格式：
📊 CFO 分析:
(分析內容)

🏭 COO 分析:
(分析內容)

👑 CEO 最終決策:
(分析內容)
"""

        # 呼叫 Gemini LLM
        model = genai.GenerativeModel("gemini-2.5-Flash")
        response = model.generate_content(full_prompt)

    # 顯示整合報告
    st.subheader("📈 AI 專業經理人團隊整合報告")
    st.text_area("報告內容", value=response.result, height=500)
