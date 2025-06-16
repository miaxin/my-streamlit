import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

def find_column(df, keywords):
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower():
                return col
    return None

def safe_div(a, b):
    return a / b.replace({0: np.nan})

st.set_page_config(page_title="批次財務報表分析", layout="wide")
st.title("📂 批次財務報表分析儀表板")

uploaded_files = st.file_uploader("請上傳一或多個 CSV 財務報表", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    results = []
    for idx, file in enumerate(uploaded_files):
        st.markdown(f"### 檔案 {idx+1}: {file.name}")
        try:
            df = pd.read_csv(file)
        except Exception as e:
            st.error(f"讀取檔案錯誤: {e}")
            continue

        # 欄位偵測
        date_col = find_column(df, ['date', 'period', 'month', 'year'])
        revenue_col = find_column(df, ['revenue', 'sales', 'income'])
        cost_col = find_column(df, ['cost', 'expense', 'cogs'])
        net_income_col = find_column(df, ['net profit', 'net income', 'profit after tax'])
        asset_col = find_column(df, ['asset'])
        liability_col = find_column(df, ['liability', 'debt'])
        equity_col = find_column(df, ['equity', 'capital'])

        st.write("偵測到欄位：")
        st.write({
            "日期": date_col,
            "收入": revenue_col,
            "成本": cost_col,
            "淨利": net_income_col,
            "資產": asset_col,
            "負債": liability_col,
            "權益": equity_col
        })

        # 欄位缺失提醒
        must_have = [date_col, revenue_col, cost_col, net_income_col, asset_col, liability_col, equity_col]
        if any(x is None for x in must_have):
            st.warning("此檔案缺少必要欄位，無法分析")
            continue

        # 日期轉換
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])

        # 計算指標
        df['毛利'] = df[revenue_col] - df[cost_col]
        df['毛利率'] = safe_div(df['毛利'], df[revenue_col])
        df['淨利率'] = safe_div(df[net_income_col], df[revenue_col])
        df['負債比率'] = safe_div(df[liability_col], df[asset_col])
        df['權益比率'] = safe_div(df[equity_col], df[asset_col])
        df['負債對權益比率'] = safe_div(df[liability_col], df[equity_col])

        df['Year'] = df[date_col].dt.year
        summary = df.groupby('Year').agg({
            revenue_col: 'sum',
            '毛利': 'sum',
            net_income_col: 'sum',
            asset_col: 'mean',
            liability_col: 'mean',
            equity_col: 'mean',
            '毛利率': 'mean',
            '淨利率': 'mean',
            '負債比率': 'mean',
            '權益比率': 'mean',
            '負債對權益比率': 'mean',
        }).rename(columns={
            revenue_col: '營收',
            net_income_col: '淨利',
            asset_col: '平均資產',
            liability_col: '平均負債',
            equity_col: '平均權益'
        })

        st.dataframe(summary.style.format({
            '營收': '{:,.0f}',
            '毛利': '{:,.0f}',
            '淨利': '{:,.0f}',
            '平均資產': '{:,.0f}',
            '平均負債': '{:,.0f}',
            '平均權益': '{:,.0f}',
            '毛利率': '{:.2%}',
            '淨利率': '{:.2%}',
            '負債比率': '{:.2%}',
            '權益比率': '{:.2%}',
            '負債對權益比率': '{:.2f}',
        }))

        # 繪圖
        summary_reset = summary.reset_index().melt('Year', var_name='指標', value_name='值')
        chart = alt.Chart(summary_reset).mark_line(point=True).encode(
            x='Year:O',
            y=alt.Y('值:Q'),
            color='指標:N',
            tooltip=['Year', '指標', '值']
        ).properties(width=900, height=400).interactive()

        st.altair_chart(chart, use_container_width=True)

else:
    st.info("請上傳一或多個 CSV 檔案。")
