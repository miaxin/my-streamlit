import streamlit as st
import pandas as pd
import numpy as np

# 偵測欄位函式（給定關鍵字列表，找第一個符合的欄位）
def find_column(df, keywords):
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower():
                return col
    return None

st.set_page_config(page_title="財務報表分析儀表板", layout="wide")
st.title("🏦 商店財務報表分析儀表板")

uploaded_file = st.file_uploader("請上傳財務報表 CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"讀取檔案失敗：{e}")
        st.stop()

    # 自動找欄位
    date_col = find_column(df, ['date', 'period', 'month', 'year'])
    revenue_col = find_column(df, ['revenue', 'sales', 'income'])
    cost_col = find_column(df, ['cost', 'expense', 'cogs'])
    operating_profit_col = find_column(df, ['operating profit', 'operating_income', 'ebit'])
    net_income_col = find_column(df, ['net profit', 'net income', 'profit after tax'])
    asset_col = find_column(df, ['asset'])
    current_asset_col = find_column(df, ['current asset', 'current_asset'])
    liability_col = find_column(df, ['liability', 'debt'])
    current_liability_col = find_column(df, ['current liability', 'current_liability'])
    equity_col = find_column(df, ['equity', 'capital'])
    capex_col = find_column(df, ['capital expenditure', 'capex'])
    operating_cashflow_col = find_column(df, ['operating cash flow', 'cash from operations'])

    # 檢查必要欄位
    missing = []
    if not date_col: missing.append("日期")
    if not revenue_col: missing.append("收入")
    if not cost_col: missing.append("成本")
    if not net_income_col: missing.append("淨利")
    if not asset_col: missing.append("資產")
    if not liability_col: missing.append("負債")
    if not equity_col: missing.append("權益")

    if missing:
        st.warning(f"⚠️ 以下必要欄位找不到或無法辨識：{', '.join(missing)}，請確認 CSV 欄位名稱。")

    # 日期轉換
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])

    st.subheader("資料預覽")
    st.dataframe(df.head())

    # 計算指標函式
    def safe_div(a, b):
        return a / b.replace({0:np.nan})

    if date_col and revenue_col and cost_col and net_income_col and asset_col and liability_col and equity_col:
        # 毛利與毛利率
        df['毛利'] = df[revenue_col] - df[cost_col]
        df['毛利率'] = safe_div(df['毛利'], df[revenue_col])

        # 營業利益率（若有營業利益欄）
        if operating_profit_col:
            df['營業利益率'] = safe_div(df[operating_profit_col], df[revenue_col])
        else:
            df['營業利益率'] = np.nan

        # 淨利率
        df['淨利率'] = safe_div(df[net_income_col], df[revenue_col])

        # 負債比率
        df['負債比率'] = safe_div(df[liability_col], df[asset_col])

        # 權益比率
        df['權益比率'] = safe_div(df[equity_col], df[asset_col])

        # 負債對權益比率
        df['負債對權益比率'] = safe_div(df[liability_col], df[equity_col])

        # 流動比率（若有流動資產與流動負債欄）
        if current_asset_col and current_liability_col:
            df['流動比率'] = safe_div(df[current_asset_col], df[current_liability_col])
        else:
            df['流動比率'] = np.nan

        # 自由現金流量（若有）
        if operating_cashflow_col and capex_col:
            df['自由現金流量'] = df[operating_cashflow_col] - df[capex_col]
        else:
            df['自由現金流量'] = np.nan

        # 按年匯總指標
        df['Year'] = df[date_col].dt.year
        summary = df.groupby('Year').agg({
            revenue_col: 'sum',
            '毛利': 'sum',
            net_income_col: 'sum',
            asset_col: 'mean',
            liability_col: 'mean',
            equity_col: 'mean',
            '毛利率': 'mean',
            '營業利益率': 'mean',
            '淨利率': 'mean',
            '負債比率': 'mean',
            '權益比率': 'mean',
            '負債對權益比率': 'mean',
            '流動比率': 'mean',
            '自由現金流量': 'sum'
        }).rename(columns={
            revenue_col: '營收',
            net_income_col: '淨利',
            asset_col: '平均資產',
            liability_col: '平均負債',
            equity_col: '平均權益'
        })

        st.subheader("年度財務指標彙總")
        st.dataframe(summary.style.format({
            '營收': '{:,.0f}',
            '毛利': '{:,.0f}',
            '淨利': '{:,.0f}',
            '平均資產': '{:,.0f}',
            '平均負債': '{:,.0f}',
            '平均權益': '{:,.0f}',
            '毛利率': '{:.2%}',
            '營業利益率': '{:.2%}',
            '淨利率': '{:.2%}',
            '負債比率': '{:.2%}',
            '權益比率': '{:.2%}',
            '負債對權益比率': '{:.2f}',
            '流動比率': '{:.2f}',
            '自由現金流量': '{:,.0f}'
        }))

        # 繪圖區
        import altair as alt

        st.subheader("指標趨勢圖")
        summary_reset = summary.reset_index().melt('Year', var_name='指標', value_name='值')

        chart = alt.Chart(summary_reset).mark_line(point=True).encode(
            x='Year:O',
            y=alt.Y('值:Q', title='值'),
            color='指標:N',
            tooltip=['Year', '指標', '值']
        ).properties(width=900, height=400).interactive()

        st.altair_chart(chart, use_container_width=True)

    else:
        st.info("請確保您的資料包含至少以下欄位：日期、收入、成本、淨利、資產、負債、權益。")

else:
    st.info("請上傳財務報表 CSV 檔案。")
