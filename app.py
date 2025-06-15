import streamlit as st
import pandas as pd

st.title("汽車銷售資料分析")

uploaded_file = st.file_uploader("請上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, encoding='utf-8', parse_dates=['Date'])
    
    st.subheader("📊 資料總攬")
    st.write(f"資料總筆數: {len(df)}")
    st.write(f"欄位名稱: {list(df.columns)}")
    st.dataframe(df.head(10))  # 預覽前10筆資料
    
    st.write("---")
    
    analysis = st.selectbox("選擇分析類型", [
        "銷售趨勢分析",
        "經銷商銷售排行",
        "品牌銷售排行",
        "車款銷售排行",
        "性別分析",
        "經銷商區域分析",
        "價格分布"
    ])
    
    if analysis == "銷售趨勢分析":
        sales_trend = df.groupby('Date')['Price ($)'].sum().sort_index()
        st.line_chart(sales_trend)
    
    elif analysis == "經銷商銷售排行":
        dealer_sales = df.groupby('Dealer_Name')['Price ($)'].sum()
        st.bar_chart(dealer_sales)
    
    elif analysis == "品牌銷售排行":
        brand_sales = df.groupby('Company')['Price ($)'].sum()
        st.bar_chart(brand_sales)
    
    elif analysis == "車款銷售排行":
        model_sales = df.groupby('Model')['Price ($)'].sum()
        st.bar_chart(model_sales)
    
    elif analysis == "性別分析":
        gender_sales = df.groupby('Gender')['Price ($)'].sum()
        st.bar_chart(gender_sales)
    
    elif analysis == "經銷商區域分析":
        region_sales = df.groupby('Dealer_Region')['Price ($)'].sum()
        st.bar_chart(region_sales)
    
    elif analysis == "價格分布":
        st.write("價格分布直方圖")
        st.bar_chart(df['Price ($)'].value_counts(bins=20).sort_index())
else:
    st.info("請先上傳 CSV 檔案")
