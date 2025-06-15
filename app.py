import streamlit as st
import pandas as pd

st.set_page_config(page_title="銷售資料分析", layout="wide")

# 頁面標題區
st.markdown("<h1 style='text-align: center; color: #3366cc;'>🚗 汽車銷售資料分析 Dashboard</h1>", unsafe_allow_html=True)
st.markdown("### 📥 請上傳您的銷售資料（CSV）")

uploaded_file = st.file_uploader("", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, encoding='utf-8', parse_dates=['Date'])

    # 資料總攬區塊
    st.markdown("### 🧾 資料總覽")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("資料筆數", len(df))
        st.write("欄位名稱：", df.columns.tolist())
    with col2:
        st.dataframe(df.head(10), use_container_width=True)

    st.markdown("---")

    # 分析選單區塊
    st.markdown("### 📊 選擇您要查看的分析圖表")
    analysis = st.selectbox(
        "點選下方選單選擇分析類型",
        [
            "📈 銷售趨勢分析",
            "🏬 經銷商銷售排行",
            "🏷️ 品牌銷售排行",
            "🚙 車款銷售排行",
            "👥 客戶性別分析",
            "🌍 經銷商區域分布",
            "💰 價格分布分析"
        ]
    )

    # 各類型分析圖表
    st.markdown("#### 📉 分析結果")
    
    if analysis == "📈 銷售趨勢分析":
        sales_trend = df.groupby('Date')['Price ($)'].sum().sort_index()
        st.line_chart(sales_trend)

    elif analysis == "🏬 經銷商銷售排行":
        dealer_sales = df.groupby('Dealer_Name')['Price ($)'].sum()
        st.bar_chart(dealer_sales)

    elif analysis == "🏷️ 品牌銷售排行":
        brand_sales = df.groupby('Company')['Price ($)'].sum()
        st.bar_chart(brand_sales)

    elif analysis == "🚙 車款銷售排行":
        model_sales = df.groupby('Model')['Price ($)'].sum()
        st.bar_chart(model_sales)

    elif analysis == "👥 客戶性別分析":
        gender_sales = df.groupby('Gender')['Price ($)'].sum()
        st.bar_chart(gender_sales)

    elif analysis == "🌍 經銷商區域分布":
        region_sales = df.groupby('Dealer_Region')['Price ($)'].sum()
        st.bar_chart(region_sales)

    elif analysis == "💰 價格分布分析":
        st.write("價格分布（每區間數量）")
        st.bar_chart(df['Price ($)'].value_counts(bins=20).sort_index())
else:
    st.info("請上傳包含日期欄位的汽車銷售 CSV 檔案")
