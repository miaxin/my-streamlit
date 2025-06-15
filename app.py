import streamlit as st
import pandas as pd

st.set_page_config(page_title="🚗 銷售資料分析儀表板", layout="wide")

# 頁面標題
st.markdown(
    "<h1 style='text-align: center; color: white; background-color: #4B6EA9; padding: 20px; border-radius: 10px;'>🚘 銷售資料分析儀表板</h1>",
    unsafe_allow_html=True
)

# 上傳 CSV 檔案
uploaded_file = st.file_uploader("📁 請上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    # 讀取 CSV
    df = pd.read_csv(uploaded_file, encoding='utf-8', parse_dates=['Date'])

    # 資料預覽區
    with st.container():
        st.markdown("### 🗂️ 資料總覽")
        col1, col2 = st.columns(2)
        col1.metric("📊 資料筆數", len(df))
        col2.metric("🧾 欄位數", len(df.columns))
        st.dataframe(df, use_container_width=True)


    st.markdown("---")

    # 分頁分析區
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 銷售趨勢", "🏪 經銷商排行", "🏷️ 品牌排行",
        "🚗 車款排行", "🙋 性別分析", "🌍 區域分析", "💰 價格分布"
    ])

    with tab1:
        st.subheader("📈 每日銷售趨勢")
        trend = df.groupby('Date')['Price ($)'].sum().sort_index()
        st.line_chart(trend)

    with tab2:
        st.subheader("🏪 經銷商總銷售額")
        dealer = df.groupby('Dealer_Name')['Price ($)'].sum()
        st.bar_chart(dealer)

    with tab3:
        st.subheader("🏷️ 品牌總銷售額")
        brand = df.groupby('Company')['Price ($)'].sum()
        st.bar_chart(brand)

    with tab4:
        st.subheader("🚗 車款總銷售額")
        model = df.groupby('Model')['Price ($)'].sum()
        st.bar_chart(model)

    with tab5:
        st.subheader("🙋 不同性別銷售額")
        gender = df.groupby('Gender')['Price ($)'].sum()
        st.bar_chart(gender)

    with tab6:
        st.subheader("🌍 各區域總銷售額")
        region = df.groupby('Dealer_Region')['Price ($)'].sum()
        st.bar_chart(region)

    with tab7:
        st.subheader("💰 價格分布")
        st.bar_chart(df['Price ($)'].value_counts(bins=20).sort_index())

else:
    st.info("請先上傳資料以開始分析 🚀")
