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
        '日期': 'Date', '交易日': 'Date', '銷售日': 'Date',
        '公司': 'Company', '類別': 'Category',
        '市值': 'MarketCap', '市值十億美元': 'MarketCap', '市值（十億美元）': 'MarketCap',
        '收入': 'Revenue', '營收': 'Revenue', '營業收入': 'Revenue', 'Total Revenue': 'Revenue',
        '收入十億美元': 'Revenue',
        '毛利': 'GrossProfit',
        '淨利': 'NetIncome', '純益': 'NetIncome', '收益': 'NetIncome', 'Profit After Tax': 'NetIncome',
        '每股盈餘': 'EPS', '每股收益': 'EPS',
        '息稅折舊攤提前利潤': 'EBITDA',
        '股東權益': 'Equity',
        '成本': 'Cost', '銷貨成本': 'Cost', '成本金額': 'Cost', 'COGS': 'Cost',
        '數量': 'Quantity', '價格': 'Price',
        '客戶': 'Customer',
        '分店': 'Store', '門市': 'Store', '據點': 'Store', '營業點': 'Store',
        '產品': 'Product', '商品': 'Product', '品項': 'Product', '品名': 'Product',
        '年': 'Year', '年份': 'Year', '月份': 'Month'
    }
    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)

    # 年份處理邏輯加強
    if 'Year' not in df.columns:
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Year'] = df['Date'].dt.year
            df['Month'] = df['Date'].dt.month
        elif '年' in df.columns:
            df['Year'] = pd.to_numeric(df['年'], errors='coerce')

    with st.sidebar:
        st.header("⚙️ 選項")
        year_options = df['Year'].dropna().unique() if 'Year' in df.columns else []
        year = st.selectbox("選擇年份", sorted(year_options, reverse=True)) if len(year_options) > 0 else None

    filtered_df = df[df['Year'] == year] if year and 'Year' in df.columns else df.copy()

    st.markdown("## 📦 商品分析")
    if all(col in filtered_df.columns for col in ['Product', 'Revenue']):
        top_products = filtered_df.groupby('Product')['Revenue'].sum().nlargest(10).reset_index()
        chart = alt.Chart(top_products).mark_bar().encode(
            x=alt.X('Revenue:Q', title='營收'),
            y=alt.Y('Product:N', sort='-x', title='商品')
        ).properties(title=f"{year if year else ''} 年 Top 10 商品營收")
        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("缺少 Product 或 Revenue 欄位，無法進行商品分析")

    st.markdown("## 🏪 分店營運分析")
    if all(col in filtered_df.columns for col in ['Store', 'Revenue']):
        store_rev = filtered_df.groupby('Store')['Revenue'].sum().reset_index()
        st.bar_chart(store_rev.set_index('Store'))
    else:
        st.warning("缺少 Store 或 Revenue 欄位，無法進行分店分析")

    st.markdown("## 📈 財務趨勢預測")
    if 'Date' in df.columns and 'Revenue' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        monthly = df.set_index('Date').resample('M').sum(numeric_only=True)
        st.line_chart(monthly['Revenue'])
    else:
        st.warning("缺少 Date 或 Revenue 欄位，無法顯示趨勢")

    st.markdown("## 🧮 損益表")
    if all(col in df.columns for col in ['Revenue', 'Cost']):
        pnl = df.groupby('Year').agg({
            'Revenue': 'sum',
            'Cost': 'sum'
        })
        pnl['Gross Profit'] = pnl['Revenue'] - pnl['Cost']
        pnl['Net Income'] = df.groupby('Year')['NetIncome'].sum() if 'NetIncome' in df.columns else pnl['Gross Profit'] * 0.8
        st.dataframe(pnl)
    else:
        st.warning("缺少 Revenue 或 Cost 欄位，無法產生損益表")

    st.markdown("## 📊 財務比率分析")
    if all(col in df.columns for col in ['Revenue', 'GrossProfit', 'NetIncome']):
        ratio = pd.DataFrame(index=df['Year'].dropna().unique())
        ratio['毛利率'] = df.groupby('Year')['GrossProfit'].sum() / df.groupby('Year')['Revenue'].sum()
        ratio['淨利率'] = df.groupby('Year')['NetIncome'].sum() / df.groupby('Year')['Revenue'].sum()
        st.dataframe(ratio.style.format("{:.2%}"))
    else:
        st.warning("缺少 Revenue、GrossProfit 或 NetIncome 欄位，無法計算比率")

else:
    st.info("請上傳資料檔以開始分析。")
