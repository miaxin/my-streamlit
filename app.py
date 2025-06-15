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
        df = df.dropna(subset=['Date', 'Price ($)'])
        df['Year'] = df['Date'].dt.year

        st.markdown("## 📊 資料總攬")
        st.write(f"總資料筆數：**{len(df):,} 筆**")
        st.write("以下為前 5 筆資料預覽：")
        st.dataframe(df.head(), use_container_width=True)

        st.divider()
        st.markdown("## 🔍 分析區塊")

        selected_year = st.selectbox("選擇年份進行分析", sorted(df['Year'].unique(), reverse=True))
        filtered_df = df[df['Year'] == selected_year]

        avg_price = filtered_df['Price ($)'].mean()
        max_price = filtered_df['Price ($)'].max()
        top_brand = filtered_df.groupby("Company")["Price ($)"].sum().idxmax()
        top_brand_amount = filtered_df.groupby("Company")["Price ($)"].sum().max()

        col1, col2, col3 = st.columns(3)
        col1.metric("平均售價", f"${avg_price:,.0f}")
        col2.metric("最高售價", f"${max_price:,.0f}")
        col3.metric("最暢銷品牌", f"{top_brand}")

        st.markdown(f"""
        📌 **{selected_year} 年重點觀察：**
        - 平均單價為 **${avg_price:,.0f}**
        - 最昂貴車款售價達 **${max_price:,.0f}**
        - 銷售額最高品牌為 **{top_brand}**，總銷售金額為 **${top_brand_amount:,.0f}**
        """)

        st.markdown("### 📈 每日總銷售趨勢")
        trend = filtered_df.groupby("Date")["Price ($)"].sum()
        st.line_chart(trend)

        st.markdown("### 🏆 Top 10 品牌銷售額")
        top_brands = filtered_df.groupby("Company")["Price ($)"].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top_brands)
        st.markdown(f"🔎 其中 **{top_brands.idxmax()}** 銷售額最高，達 **${top_brands.max():,.0f}**")

        st.markdown("### 🏪 Top 10 經銷商銷售額")
        top_dealers = filtered_df.groupby("Dealer_Name")["Price ($)"].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top_dealers)
        st.markdown(f"🏬 銷售最好的經銷商為 **{top_dealers.idxmax()}**，總銷售金額為 **${top_dealers.max():,.0f}**")

        if 'Gender' in df.columns and 'Model' in df.columns:
            st.markdown("### 👥 車型偏好分析（依性別）")
            pivot = filtered_df.pivot_table(index='Model', columns='Gender', values='Price ($)', aggfunc='sum').fillna(0)
            st.bar_chart(pivot)
            st.markdown("👫 顯示不同性別偏好的車型與消費結構。")

        st.markdown("### 💰 價格分布觀察")
        hist_df = pd.DataFrame({'Price': filtered_df['Price ($)']})
        chart = alt.Chart(hist_df).mark_bar().encode(
            alt.X("Price:Q", bin=alt.Bin(maxbins=20), title="價格區間"),
            alt.Y('count():Q', title='數量')
        ).properties(width=800, height=400)
        st.altair_chart(chart, use_container_width=True)
        st.markdown("📉 用來觀察各種價格區間的熱門程度。")

else:
    st.empty()  # 沒檔案時不顯示任何提示文字
