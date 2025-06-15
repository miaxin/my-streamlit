import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="汽車銷售資料分析", layout="wide")
st.title("🚗 銷售資料分析儀表板")

uploaded_file = st.file_uploader("請上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8', parse_dates=['Date'])
    except Exception as e:
        st.error(f"讀取檔案錯誤：{e}")
    else:
        # 基本清理
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

        # KPI 指標
        col1, col2, col3 = st.columns(3)
        col1.metric("平均單價", f"${filtered_df['Price ($)'].mean():,.0f}")
        col2.metric("最高單價", f"${filtered_df['Price ($)'].max():,.0f}")
        top_brand = filtered_df.groupby("Company")["Price ($)"].sum().idxmax()
        col3.metric("銷售最佳品牌", top_brand)

        # 銷售趨勢
        st.markdown("### 📈 銷售趨勢圖（每日總銷售額）")
        trend = filtered_df.groupby("Date")["Price ($)"].sum()
        st.line_chart(trend)

        # 品牌
        st.markdown("### 🏆 Top 10 品牌銷售額")
        top_brands = filtered_df.groupby("Company")["Price ($)"].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top_brands)

        # 經銷商
        st.markdown("### 🏪 Top 10 經銷商銷售額")
        top_dealers = filtered_df.groupby("Dealer_Name")["Price ($)"].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top_dealers)

        # 性別 vs 車型
        st.markdown("### 👥 車型偏好分析（依性別）")
        if 'Gender' in df.columns and 'Model' in df.columns:
            pivot = filtered_df.pivot_table(index='Model', columns='Gender', values='Price ($)', aggfunc='sum').fillna(0)
            st.bar_chart(pivot)

        # 價格分布圖（Altair）
        st.markdown("### 💰 價格分布觀察")
        hist_df = pd.DataFrame({'Price': filtered_df['Price ($)']})
        chart = alt.Chart(hist_df).mark_bar().encode(
            alt.X("Price:Q", bin=alt.Bin(maxbins=20), title="價格區間"),
            alt.Y('count():Q', title='數量')
        ).properties(width=800, height=400)

        st.altair_chart(chart, use_container_width=True)

else:
    st.info("請上傳包含 `Date`, `Price ($)`, `Company`, `Dealer_Name`, `Model`, `Gender` 等欄位的 CSV 檔案。")
