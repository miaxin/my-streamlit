import streamlit as st
import pandas as pd

st.set_page_config(page_title="汽車銷售資料分析", layout="wide")
st.title("🚗 銷售資料分析儀表板")

uploaded_file = st.file_uploader("請上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, encoding='utf-8', parse_dates=['Date'])
    
    # 資料清理與準備
    df = df.dropna(subset=['Date', 'Price ($)'])
    df['Year'] = df['Date'].dt.year

    st.markdown("## 📊 資料總攬")
    st.write(f"總筆數：{len(df)}")
    st.write(f"欄位名稱：{list(df.columns)}")
    st.dataframe(df, use_container_width=True)

    st.divider()
    st.markdown("## 🔍 分析類型")

    selected_year = st.selectbox("選擇年份篩選", sorted(df['Year'].unique(), reverse=True))
    filtered_df = df[df['Year'] == selected_year]

    col1, col2, col3 = st.columns(3)
    col1.metric("平均單價", f"${filtered_df['Price ($)'].mean():,.0f}")
    col2.metric("最高單價", f"${filtered_df['Price ($)'].max():,.0f}")
    top_brand = filtered_df.groupby("Company")["Price ($)"].sum().idxmax()
    col3.metric("銷售最佳品牌", top_brand)

    st.markdown("### 📈 銷售趨勢圖（每日總銷售額）")
    trend = filtered_df.groupby("Date")["Price ($)"].sum()
    st.line_chart(trend)

    st.markdown("### 🏆 Top 10 品牌銷售額")
    top_brands = filtered_df.groupby("Company")["Price ($)"].sum().sort_values(ascending=False).head(10)
    st.bar_chart(top_brands)

    st.markdown("### 🏪 Top 10 經銷商銷售額")
    top_dealers = filtered_df.groupby("Dealer_Name")["Price ($)"].sum().sort_values(ascending=False).head(10)
    st.bar_chart(top_dealers)

    st.markdown("### 👥 車型偏好分析（依性別）")
    if 'Gender' in df.columns and 'Model' in df.columns:
        pivot = filtered_df.pivot_table(index='Model', columns='Gender', values='Price ($)', aggfunc='sum').fillna(0)
        st.bar_chart(pivot)

    st.markdown("### 💰 價格分布觀察")
    st.bar_chart(filtered_df['Price ($)'].value_counts(bins=20).sort_index())

else:
    st.info("請先上傳包含汽車銷售欄位的 CSV 檔案，例如包含：Date, Price ($), Dealer_Name, Company, Model, Gender 等欄位。")
