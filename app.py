import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="📊 全方位財務與商業分析儀表板", layout="wide")
st.title("📈 商店與商品財務分析系統")

uploaded_file = st.file_uploader("請上傳交易/財務資料 (CSV/XLSX)", type=["csv", "xlsx"])

def load_data(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    df.columns = df.columns.str.replace(r"（.*?）|\(.*?\)", "", regex=True).str.strip()
    return df

if uploaded_file:
    df = load_data(uploaded_file)
    st.markdown("## 🔍 資料預覽")
    st.dataframe(df, use_container_width=True)

    # 偵測常見欄位
    col_map = {
        '日期': 'Date', '公司': 'Company', '類別': 'Category',
        '市值': 'MarketCap', '收入': 'Revenue', '毛利': 'GrossProfit',
        '淨利': 'NetIncome', '每股盈餘': 'EPS', '每股收益': 'EPS',
        '息稅折舊攤提前利潤': 'EBITDA', '股東權益': 'Equity',
        '成本': 'Cost', '數量': 'Quantity', '價格': 'Price', '客戶': 'Customer',
        '分店': 'Store', '產品': 'Product', '年': 'Year', '月份': 'Month'
    }
    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.month

    with st.sidebar:
        st.header("⚙️ 選項")
        year_options = df['Year'].dropna().unique() if 'Year' in df.columns else []
        year = st.selectbox("選擇年份", sorted(year_options, reverse=True)) if len(year_options) > 0 else None

    st.markdown("## 📦 商品分析")
    if all(col in df.columns for col in ['Product', 'Revenue']):
        top_products = df[df['Year'] == year].groupby('Product')['Revenue'].sum().nlargest(10).reset_index()
        chart = alt.Chart(top_products).mark_bar().encode(
            x=alt.X('Revenue:Q', title='營收'),
            y=alt.Y('Product:N', sort='-x', title='商品')
        ).properties(title=f"{year} 年 Top 10 商品營收")
        st.altair_chart(chart, use_container_width=True)

    st.markdown("## 🏪 分店營運分析")
    if all(col in df.columns for col in ['Store', 'Revenue']):
        store_rev = df[df['Year'] == year].groupby('Store')['Revenue'].sum().reset_index()
        st.bar_chart(store_rev.set_index('Store'))

    st.markdown("## 📈 財務趨勢預測")
    if 'Date' in df.columns and 'Revenue' in df.columns:
        monthly = df.set_index('Date').resample('M').sum(numeric_only=True)
        st.line_chart(monthly['Revenue'])

    st.markdown("## 🧮 損益表")
    if all(col in df.columns for col in ['Revenue', 'Cost']):
        pnl = df.groupby('Year').agg({
            'Revenue': 'sum',
            'Cost': 'sum'
        })
        pnl['Gross Profit'] = pnl['Revenue'] - pnl['Cost']
        pnl['Net Income'] = df.groupby('Year')['NetIncome'].sum() if 'NetIncome' in df.columns else pnl['Gross Profit'] * 0.8
        st.dataframe(pnl)

    st.markdown("## 📊 財務比率分析")
    if all(col in df.columns for col in ['Revenue', 'GrossProfit', 'NetIncome']):
        ratio = pd.DataFrame(index=df['Year'].dropna().unique())
        ratio['毛利率'] = df.groupby('Year')['GrossProfit'].sum() / df.groupby('Year')['Revenue'].sum()
        ratio['淨利率'] = df.groupby('Year')['NetIncome'].sum() / df.groupby('Year')['Revenue'].sum()
        st.dataframe(ratio.style.format("{:.2%}"))

else:
    st.info("請上傳資料檔以開始分析。")
