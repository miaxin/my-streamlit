import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.arima.model import ARIMA

uploaded_file = st.file_uploader("上傳財務資料 CSV", type=['csv'])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    # 後續分析繼續
else:
    st.warning("請先上傳 CSV 檔")
    st.stop()

# 財務比率計算
def calc_ratios(df):
    df['NetProfitMargin'] = df['NetIncome'] / df['Revenue']
    df['ROE'] = df['NetIncome'] / df['Equity']
    df['ROA'] = df['NetIncome'] / (df['Equity'] + df['Debt'])
    df['ROI'] = df['NetIncome'] / (df['Equity'] + df['Debt'])
    df['DebtEquityRatio'] = df['Debt'] / df['Equity']
    df['CurrentRatio'] = df['CurrentAssets'] / df['CurrentLiabilities']
    df['GrossMargin'] = df['GrossProfit'] / df['Revenue']
    df['OperatingMargin'] = (df['GrossProfit'] - (df['Revenue'] - df['GrossProfit'] - df['NetIncome'])) / df['Revenue']
    return df

df = calc_ratios(df)

companies = df['Company'].unique()
selected_companies = st.sidebar.multiselect("選擇公司", companies, default=companies[:3])

years = df['Year'].unique()
year_min, year_max = int(df['Year'].min()), int(df['Year'].max())
selected_years = st.sidebar.slider("選擇年份範圍", year_min, year_max, (year_min, year_max))

filtered = df[(df['Company'].isin(selected_companies)) &
              (df['Year'] >= selected_years[0]) & (df['Year'] <= selected_years[1])]

# 1. 財務趨勢折線圖
st.header("財務趨勢分析")
metric = st.selectbox("選擇指標", ['MarketCap', 'Revenue', 'GrossProfit', 'NetIncome', 'EPS'])

line_chart = alt.Chart(filtered).mark_line(point=True).encode(
    x='Year:O',
    y=alt.Y(metric, title=metric),
    color='Company',
    tooltip=['Company', 'Year', metric]
).interactive()

st.altair_chart(line_chart, use_container_width=True)

# 2. 財務比率柱狀圖
st.header("財務比率分析")
ratio = st.selectbox("選擇財務比率", ['NetProfitMargin', 'ROE', 'ROA', 'ROI', 'DebtEquityRatio', 'CurrentRatio'])

bar_chart = alt.Chart(filtered).mark_bar().encode(
    x='Year:O',
    y=alt.Y(ratio, title=ratio),
    color='Company',
    column='Company',
    tooltip=['Company', 'Year', ratio]
).properties(width=100).interactive()

st.altair_chart(bar_chart, use_container_width=True)

# 3. 行業內多指標比較 — 用平行座標圖取代雷達圖
st.header("行業內公司獲利與效率比較 (平行座標圖)")
industry = st.selectbox("選擇行業", df['Industry'].unique())
industry_df = df[(df['Industry'] == industry) & (df['Year'] == selected_years[1])]

metrics = ['ROE', 'ROA', 'GrossMargin', 'OperatingMargin']

# 標準化
scaler = MinMaxScaler()
scaled_vals = scaler.fit_transform(industry_df[metrics].fillna(0))
scaled_df = pd.DataFrame(scaled_vals, columns=metrics)
scaled_df['Company'] = industry_df['Company'].values

# 將資料轉成長格式方便繪圖
melted = scaled_df.melt(id_vars=['Company'], var_name='Metric', value_name='Value')

parallel = alt.Chart(melted).mark_line().encode(
    x=alt.X('Metric:N', sort=metrics),
    y=alt.Y('Value:Q', scale=alt.Scale(domain=[0,1])),
    color='Company',
    detail='Company',
    tooltip=['Company', 'Metric', alt.Tooltip('Value', format='.2f')]
).interactive()

st.altair_chart(parallel, use_container_width=True)

# 4. 損益表模擬展示
st.header("損益表與資產負債表模擬")
company_sim = st.selectbox("選擇公司(模擬)", companies, key="sim_company")
year_sim = st.slider("選擇年份(模擬)", year_min, year_max, year_min, key="sim_year")

sim_row = df[(df['Company'] == company_sim) & (df['Year'] == year_sim)]
if not sim_row.empty:
    sim_data = sim_row.iloc[0]
    st.markdown("**損益表（簡化）**")
    st.write({
        "營收 (Revenue)": sim_data['Revenue'],
        "成本 (Cost, 簡化)": sim_data['Revenue'] - sim_data['GrossProfit'],
        "淨利 (Net Income)": sim_data['NetIncome']
    })

    st.markdown("**資產負債表（簡化）**")
    st.write({
        "股東權益 (Equity)": sim_data['Equity'],
        "負債 (Debt)": sim_data['Debt'],
        "負債比 (Debt/Equity Ratio)": sim_data['DebtEquityRatio']
    })
else:
    st.write("無該公司該年份資料")

# 5. 簡單時間序列預測示範 — ARIMA
st.header("簡單時間序列預測示範 (ARIMA)")

predict_company = st.selectbox("選擇預測公司", companies, key="pred_company")
predict_metric = st.selectbox("選擇預測指標", ['MarketCap', 'Revenue', 'NetIncome'], key="pred_metric")

pred_df = df[df['Company'] == predict_company][['Year', predict_metric]].dropna().sort_values('Year')

if len(pred_df) >= 5:
    # ARIMA 只用指標值，年份作索引
    pred_df = pred_df.set_index('Year')
    try:
        model = ARIMA(pred_df[predict_metric], order=(1,1,1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=3)
        
        forecast_years = np.arange(pred_df.index.max()+1, pred_df.index.max()+4)
        forecast_df = pd.DataFrame({predict_metric: forecast}, index=forecast_years).reset_index().rename(columns={'index':'Year'})

        combined = pd.concat([pred_df.reset_index(), forecast_df])

        line_pred = alt.Chart(combined).mark_line(point=True).encode(
            x='Year:O',
            y=predict_metric,
            tooltip=['Year', predict_metric]
        )

        st.altair_chart(line_pred, use_container_width=True)
        st.write("預測結果（未來3年）")
        st.dataframe(forecast_df)

    except Exception as e:
        st.error(f"模型擬合失敗：{e}")
else:
    st.write("該公司資料不足，至少需要5年資料才能進行預測。")
