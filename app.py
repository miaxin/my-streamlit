import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
from statsmodels.tsa.seasonal import seasonal_decompose
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="銷售資料分析", layout="wide")
st.title("銷售資料分析儀表板")

uploaded_file = st.file_uploader("請上傳 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8', parse_dates=['Date'])
    except Exception as e:
        st.error(f"讀取檔案錯誤：{e}")
    else:
        df = df.dropna(subset=['Date', 'Price ($)'])
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.to_period('M')
        df['DayOfWeek'] = df['Date'].dt.dayofweek

        st.markdown("## 📊 資料總覽")
        st.write(f"總資料筆數：**{len(df):,} 筆**")
        st.dataframe(df, use_container_width=True)

        selected_year = st.selectbox("選擇年份進行分析", sorted(df['Year'].unique(), reverse=True))
        filtered_df = df[df['Year'] == selected_year]

        tabs = st.tabs([
            "📈 市場分析",
            "📅 季節性模式與競爭分析",
            "🔮 預測與趨勢分析",
            "🚚 供應鏈與庫存優化"
        ])

        # 市場分析
        with tabs[0]:
            st.header("📈 市場分析")
            
            st.subheader("每日銷售趨勢")
            daily_sales = filtered_df.groupby("Date")["Price ($)"].sum()
            st.line_chart(daily_sales)
            
            st.subheader("區域銷售總額")
            if 'Dealer_Region' in filtered_df.columns:
                region_sales = filtered_df.groupby('Dealer_Region')['Price ($)'].sum().sort_values(ascending=False)
                st.bar_chart(region_sales)
                st.markdown(f"最高銷售區域為 **{region_sales.idxmax()}**，銷售額 **${region_sales.max():,.0f}**")
            else:
                st.warning("缺少 Dealer_Region 欄位")
            
            st.subheader("車型性別偏好")
            if 'Gender' in filtered_df.columns and 'Model' in filtered_df.columns:
                pivot = filtered_df.pivot_table(index='Model', columns='Gender', values='Price ($)', aggfunc='sum').fillna(0)
                st.bar_chart(pivot)
            else:
                st.warning("缺少 Gender 或 Model 欄位")
            
            st.subheader("人口統計 - 年收入與價格關聯")
            if 'Annual Income' in filtered_df.columns:
                income_price = filtered_df[['Annual Income', 'Price ($)']].dropna()
                chart = alt.Chart(income_price).mark_circle(size=60, opacity=0.5).encode(
                    x='Annual Income',
                    y='Price ($)',
                    tooltip=['Annual Income', 'Price ($)']
                ).interactive()
                st.altair_chart(chart, use_container_width=True)
            else:
                st.warning("缺少 Annual Income 欄位")

        # 季節性模式與競爭對手分析
        with tabs[1]:
            st.header("📅 季節性模式與競爭分析")

            st.subheader("銷售季節性拆解")
            ts = filtered_df.groupby('Date')['Price ($)'].sum().sort_index()
            if len(ts) > 30:
                decomposition = seasonal_decompose(ts, model='additive', period=30, extrapolate_trend='freq')
                seasonal_df = pd.DataFrame({
                    '趨勢': decomposition.trend,
                    '季節性': decomposition.seasonal,
                    '殘差': decomposition.resid
                })
                st.line_chart(seasonal_df)
            else:
                st.warning("資料筆數不足，無法做季節性拆解")

            st.subheader("經銷商銷售排名")
            dealer_sales = filtered_df.groupby('Dealer_Name')['Price ($)'].sum().sort_values(ascending=False)
            st.bar_chart(dealer_sales.head(10))
            st.markdown(f"銷售最強經銷商：**{dealer_sales.idxmax()}**，銷售額：**${dealer_sales.max():,.0f}**")

        # 預測與趨勢分析
        with tabs[2]:
            st.header("🔮 預測與趨勢分析")

            st.subheader("簡易線性回歸預測未來30天銷售趨勢")
            ts = filtered_df.groupby('Date')['Price ($)'].sum().sort_index().reset_index()
            if len(ts) >= 30:
                ts['Date_ordinal'] = ts['Date'].map(pd.Timestamp.toordinal)
                X = ts['Date_ordinal'].values.reshape(-1,1)
                y = ts['Price ($)'].values

                model = LinearRegression()
                model.fit(X, y)

                last_date = ts['Date'].max()
                future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=30)
                future_ordinals = future_dates.map(pd.Timestamp.toordinal).values.reshape(-1,1)
                preds = model.predict(future_ordinals)

                base = alt.Chart(ts).mark_line(color='blue').encode(
                    x='Date',
                    y='Price ($)'
                )
                forecast = alt.Chart(pd.DataFrame({'Date': future_dates, 'Price ($)': preds})).mark_line(color='red').encode(
                    x='Date',
                    y='Price ($)'
                )

                st.altair_chart(base + forecast, use_container_width=True)
                st.markdown("藍線：歷史銷售額，紅線：預測未來30天銷售趨勢")
            else:
                st.warning("資料筆數不足，無法進行預測")

        # 供應鏈與庫存優化
        with tabs[3]:
            st.header("🚚 供應鏈與庫存優化")

            daily_sales_count = filtered_df.groupby('Date')['Price ($)'].count().mean()
            total_sales_count = filtered_df['Price ($)'].count()
            inventory = total_sales_count * 1.5  # 假設庫存為1.5倍銷售量

            if daily_sales_count > 0:
                days_inventory = inventory / daily_sales_count
                st.write(f"假設庫存為總銷售量1.5倍：**{int(inventory)} 輛**")
                st.write(f"每日平均銷售量：**{daily_sales_count:.2f} 輛**")
                st.write(f"估計庫存可供銷售天數：**{days_inventory:.1f} 天**")
                st.markdown("此資訊可協助優化補貨及庫存管理。")
            else:
                st.warning("資料不足，無法計算庫存天數")

else:
    st.info("請上傳包含 Date, Price ($), Dealer_Region, Dealer_Name, Company, Model, Gender 等欄位的 CSV 檔案")
