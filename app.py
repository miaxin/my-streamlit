import streamlit as st
import pandas as pd

st.set_page_config(page_title="🚗 銷售資料分析儀表板", layout="wide")

# 🧢 頁面主標題
st.markdown("<h1 style='text-align: center; color: #4B6EA9;'>🚘 銷售資料分析儀表板</h1>", unsafe_allow_html=True)
st.markdown("### 讓我們一起探索汽車銷售資料 📊")

# 上傳檔案區塊
uploaded_file = st.file_uploader("📁 請上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    # 讀取資料
    df = pd.read_csv(uploaded_file, encoding='utf-8', parse_dates=['Date'])

    # 📊 資料預覽區
    st.markdown("---")
    st.markdown("## 🗂️ 資料預覽")
    with st.expander("🔍 點擊展開資料總覽", expanded=True):
        col1, col2 = st.columns(2)
        col1.metric("總資料筆數", len(df))
        col2.metric("欄位數量", len(df.columns))
        st.dataframe(df.head(10), use_container_width=True)

    st.markdown("---")

    # 分析選單區（改用 radio 更活潑）
    st.markdown("## 🧭 分析類型")
    analysis = st.radio(
        "請選擇一項分析內容：",
        [
            "📈 銷售趨勢分析",
            "🏪 經銷商銷售排行",
            "🏷️ 品牌銷售排行",
            "🚗 車款銷售排行",
            "🙋 性別分析",
            "🌍 經銷商區域分析",
            "💰 價格分布"
        ],
        horizontal=True,
    )

    st.markdown("---")

    # 各類分析圖表
    if analysis == "📈 銷售趨勢分析":
        st.subheader("📈 每日銷售趨勢")
        trend = df.groupby('Date')['Price ($)'].sum().sort_index()
        st.line_chart(trend)

    elif analysis == "🏪 經銷商銷售排行":
        st.subheader("🏪 經銷商總銷售額")
        dealer = df.groupby('Dealer_Name')['Price ($)'].sum()
        st.bar_chart(dealer)

    elif analysis == "🏷️ 品牌銷售排行":
        st.subheader("🏷️ 品牌總銷售額")
        brand = df.groupby('Company')['Price ($)'].sum()
        st.bar_chart(brand)

    elif analysis == "🚗 車款銷售排行":
        st.subheader("🚗 車款總銷售額")
        model = df.groupby('Model')['Price ($)'].sum()
        st.bar_chart(model)

    elif analysis == "🙋 性別分析":
        st.subheader("🙋 不同性別銷售額")
        gender = df.groupby('Gender')['Price ($)'].sum()
        st.bar_chart(gender)

    elif analysis == "🌍 經銷商區域分析":
        st.subheader("🌍 各區域總銷售額")
        region = df.groupby('Dealer_Region')['Price ($)'].sum()
        st.bar_chart(region)

    elif analysis == "💰 價格分布":
        st.subheader("💰 價格分布")
        st.bar_chart(df['Price ($)'].value_counts(bins=20).sort_index())

else:
    st.info("請先上傳資料以開始分析 🚀")
