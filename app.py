import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os

# --- Gemini API Configuration ---
# 移除了對 Gemini API key 的檢查，因為 AI 助理已被移除。
# 如果未來需要重新加入 AI 功能，請恢復此區塊。
# if "GOOGLE_API_KEY" not in st.secrets:
#     st.error("Gemini API key not found in .streamlit/secrets.toml. 請添加您的 API key。")
#     st.stop()
# genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])


st.set_page_config(page_title="財務分析儀表板", layout="wide")
st.title("📊 企業財務洞察平台") # 更新標題，移除AI相關文字
st.markdown("---")
st.markdown(""" **請上傳您的 CSV 或 Excel 檔案**。 """) # 更新提示文字，明確指出支援Excel

st.markdown("---")

# Streamlit 檔案上傳器，現在支援 CSV 和 Excel
uploaded_file = st.file_uploader("📤 上傳您的合併財務 CSV/Excel 檔案", type=["csv", "xlsx", "xls"])

# 函數：將 DataFrame 欄位穩健地轉換為數值型
@st.cache_data # 快取此函數，避免每次互動都重新運行
def convert_df_to_numeric(df_input):
    df_output = df_input.copy() # 在副本上操作
    for col in df_output.columns:
        try:
            # 嘗試將欄位轉換為數值類型，無法轉換的設為 NaN
            temp_series = pd.to_numeric(df_output[col], errors='coerce')
            original_non_null_count = df_output[col].count()
            converted_non_null_count = temp_series.count()
            
            # 啟發式判斷：如果大部分（例如 > 70%）數據能轉換為數值，則假定它是數值欄位
            # 並確保它原本不是純粹的物件/布林欄位，除非它確實包含數字
            if original_non_null_count > 0 and converted_non_null_count / original_non_null_count > 0.7:
                if not pd.api.types.is_bool_dtype(df_output[col]) and (pd.api.types.is_numeric_dtype(df_output[col]) or pd.api.types.is_object_dtype(df_output[col])):
                    df_output[col] = temp_series
                    # 將無限值替換為 NaN，以避免繪圖或計算錯誤
                    df_output[col].replace([np.inf, -np.inf], np.nan, inplace=True)
        except Exception:
            # 如果轉換失敗，則跳過此欄位，保持其原始類型
            pass
    return df_output

if uploaded_file is not None:
    try:
        # 根據檔案類型讀取數據
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("不支援的檔案格式。請上傳 CSV 或 Excel 檔案。")
            st.stop()

        df.columns = df.columns.str.strip() # 清理欄位名稱的空白字符

        st.success("檔案上傳成功！正在處理數據...")

        # 使用自動數值轉換函數
        df = convert_df_to_numeric(df)

        # 確保必要的名稱欄位存在，且是字符串類型
        # 嘗試尋找 'Name' 或 'name' 欄位作為公司名稱
        if 'Name' not in df.columns and 'name' in df.columns:
            df.rename(columns={'name': 'Name'}, inplace=True)
        
        # 如果依然沒有 'Name' 欄位，嘗試尋找其他可能的公司名稱欄位，或設定一個預設
        if 'Name' not in df.columns:
            # 尋找包含 '公司', '企業', '名稱' 等關鍵字的欄位
            potential_name_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['公司', '企業', '名稱', 'entity', 'company'])]
            if potential_name_cols:
                df.rename(columns={potential_name_cols[0]: 'Name'}, inplace=True)
                st.info(f"已將 '{potential_name_cols[0]}' 欄位識別為公司名稱 'Name'。")
            else:
                # 如果沒有找到，就創建一個索引作為名稱
                df['Name'] = [f"公司_{i+1}" for i in range(len(df))]
                st.warning("檔案中缺少 'Name' (或 'name') 欄位，已自動創建 '公司_X' 作為公司名稱。")
        
        # 確保 'Name' 欄位是字符串類型
        df['Name'] = df['Name'].astype(str).str.strip()
        
        # 將處理後的 DataFrame 儲存到 session_state
        st.session_state['processed_df'] = df

        # 預先計算可能用到的欄位 (確保原始欄位存在才計算)
        if "Balance sheet total" in df.columns and "Debt" in df.columns and df["Balance sheet total"].sum() != 0:
            df["負債比率 (%)"] = (df["Debt"] / df["Balance sheet total"]) * 100
            df["負債比率 (%)"].replace([np.inf, -np.inf], np.nan, inplace=True)
        else:
            df["負債比率 (%)"] = np.nan # 如果欄位不存在或總和為零，則為 NaN
        
        if all(col in df.columns for col in ["Equity capital", "Reserves", "Preference capital"]):
            df["總股東權益"] = df["Equity capital"] + df["Reserves"] + df["Preference capital"]
        elif "Balance sheet total" in df.columns and "Debt" in df.columns:
            # 如果沒有詳細股權資訊，則用資產總計減負債估算
            df["總股東權益"] = df["Balance sheet total"] - df["Debt"]
        else:
            df["總股東權益"] = np.nan

        if "Current assets" in df.columns and "Current liabilities" in df.columns and df["Current liabilities"].sum() != 0:
            df["流動比率"] = df["Current assets"] / df["Current liabilities"]
            df["流動比率"].replace([np.inf, -np.inf], np.nan, inplace=True)
        else:
            df["流動比率"] = np.nan

        # ----------------------------------------------------
        # 定義圖表需求 (基於欄位存在性，以字典儲存，方便動態檢查)
        # 移除了原先硬性定義的檔案名，現在完全基於當前上傳的df來判斷
        # 新增了更通用的圖表類型，增加彈性
        # ----------------------------------------------------
        chart_requirements = {
            "資料概覽表格": {
                "required": set(), # 無需特定欄位，顯示前幾行
                "description": "顯示所有數據，並可滑動查看，同時包含數據類型和描述性統計。", # 更新描述
                "type": "table_overview"
            },
            "數值欄位分佈直方圖": {
                "required": set(), # 需要至少一個數值欄位，但不指定名稱
                "description": "選擇一個數值型欄位，顯示其數據分佈的直方圖。",
                "type": "dynamic_numeric_hist"
            },
            "類別欄位計數長條圖": {
                "required": set(), # 需要至少一個類別欄位，但不指定名稱
                "description": "選擇一個類別型欄位，顯示各類別項目數量最多的前20名長條圖。",
                "type": "dynamic_categorical_bar"
            },
            "任意兩數值欄位散佈圖": { # 新增的通用散佈圖
                "required": set(), # 需要至少兩個數值欄位
                "description": "選擇任意兩個數值型欄位，分析它們之間的關係。",
                "type": "dynamic_scatter"
            },
            "產業市值長條圖（前 8 名）": {
                "required": {"Industry", "Market Capitalization"},
                "description": "展示各產業的總市值分佈。",
                "type": "bar"
            },
            "資產結構圓餅圖（單一公司）": {
                "required": {"Name", "Net block", "Current assets", "Investments"},
                "description": "顯示單一公司的淨固定資產、流動資產和投資在總資產中的佔比。",
                "type": "pie"
            },
            "負債 vs 營運資金（散佈圖）": {
                "required": {"Debt", "Working capital", "Name"},
                "description": "分析負債與營運資金之間的關係，並識別特定公司。",
                "type": "scatter"
            },
            "財務比率表格": {
                "required": {"Name", "負債比率 (%)", "流動比率", "總股東權益", "Balance sheet total"},
                "description": "顯示計算後的關鍵財務比率和基本資產負債數據。",
                "type": "table"
            },
            "各年度營收趨勢圖（單一公司）": {
                "required": {"Name", "Sales", "Sales last year", "Sales preceding year"},
                "description": "追蹤單一公司在過去三個會計年度的營收變化。",
                "type": "line"
            },
            "各年度淨利潤趨勢圖（單一公司）": {
                "required": {"Name", "Profit after tax", "Profit after tax last year", "Profit after tax preceding year"},
                "description": "追蹤單一公司在過去三個會計年度的淨利潤變化。",
                "type": "line"
            },
            "各年度EPS趨勢圖（單一公司）": {
                "required": {"Name", "EPS", "EPS last year", "EPS preceding year"},
                "description": "追蹤單一公司在過去三個會計年度的每股盈餘 (EPS) 變化。",
                "type": "line"
            },
            "ROE與ROCE比較圖（單一公司，最新年度）": {
                "required": {"Name", "Return on equity", "Return on capital employed"},
                "description": "比較單一公司最新年度的股東權益報酬率 (ROE) 和資本運用報酬率 (ROCE)。",
                "type": "bar"
            },
            "本益比與股東權益報酬率散佈圖": {
                "required": {"Price to Earning", "Return on equity", "Name"},
                "description": "分析所有公司在本益比和股東權益報酬率之間的關係，有助於投資者評估。",
                "type": "scatter"
            },
            "銷售額成長率排名（前20）": {
                "required": {"Name", "Sales growth 3Years"},
                "description": "列出過去三年銷售額成長最快的前 20 家公司。",
                "type": "bar"
            },
            "利潤成長率排名（前20）": {
                "required": {"Name", "Profit growth 3Years"},
                "description": "列出過去三年利潤成長最快的前 20 家公司。",
                "type": "bar"
            },
            "現金流量概覽圓餅圖（單一公司，最近一年）": {
                "required": {"Name", "Cash from operations last year", "Cash from investing last year", "Cash from financing last year"},
                "description": "展示單一公司最近一個會計年度的營運、投資和融資現金流分佈。",
                "type": "pie"
            },
            "自由現金流趨勢圖（單一公司）": {
                "required": {"Name", "Free cash flow last year", "Free cash flow preceding year", "Free cash flow 3years", "Free cash flow 5years", "Free cash flow 7years", "Free cash flow 10years"},
                "description": "追蹤單一公司過去多年的自由現金流趨勢。",
                "type": "line"
            },
            "股價相對表現趨勢圖（單一公司）": {
                "required": {"Name", "Current Price", "t_1_price", "Return over 1year", "Return over 3years", "Return over 5years"},
                "description": "展示單一公司在不同時間段的股價回報率。",
                "type": "bar" 
            },
            "市值分佈直方圖": {
                "required": {"Market Capitalization"},
                "description": "顯示市場資本化的分佈情況。",
                "type": "histogram"
            },
            "銷售額與淨利潤關係散佈圖": {
                "required": {"Sales", "Net profit", "Name"},
                "description": "分析公司銷售額與淨利潤之間的關係。",
                "type": "scatter"
            },
            "平均股東權益報酬率排名（前20）": {
                "required": {"Name", "Average return on equity 5Years"},
                "description": "列出過去五年平均股東權益報酬率最高的前 20 家公司。",
                "type": "bar"
            },
            "發起人持股比例分佈（圓餅圖）": {
                "required": {"Promoter holding", "FII holding", "DII holding", "Public holding"},
                "description": "顯示所有公司平均或單一公司發起人、外資、本土機構和公眾持股比例。",
                "type": "pie"
            }
        }

        # 動態判斷可用的圖表
        available_charts = []
        numeric_cols_df = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols_df = df.select_dtypes(include=['object', 'category']).columns.tolist()

        for chart_name, details in chart_requirements.items():
            required_cols = details["required"]
            
            # 對於動態分佈圖，只需要有數值或類別欄位即可
            if details["type"] == "table_overview":
                available_charts.append(chart_name) # 資料概覽始終可用
            elif details["type"] == "dynamic_numeric_hist" and numeric_cols_df:
                available_charts.append(chart_name)
            elif details["type"] == "dynamic_categorical_bar" and categorical_cols_df:
                available_charts.append(chart_name)
            elif details["type"] == "dynamic_scatter" and len(numeric_cols_df) >= 2:
                available_charts.append(chart_name)
            elif required_cols.issubset(df.columns): # 對於其他特定欄位圖表
                # 額外檢查關鍵欄位是否至少有非NaN值，避免繪製空圖
                if all(df[col].dropna().empty for col in required_cols if col in df.columns):
                    continue # 如果所有關鍵欄位都為空，則跳過此圖表
                available_charts.append(chart_name)

        # --- Streamlit Sidebar for Chart Selection ---
        st.sidebar.header("📊 圖表選擇")
        if available_charts:
            # 將通用圖表選項排在最前面
            generic_charts = ["資料概覽表格", "數值欄位分佈直方圖", "類別欄位計數長條圖", "任意兩數值欄位散佈圖"]
            sorted_available_charts = [c for c in generic_charts if c in available_charts] + \
                                      sorted([c for c in available_charts if c not in generic_charts])
            
            chart_option = st.sidebar.selectbox("🔽 根據資料欄位選擇分析圖表：", sorted(available_charts)) # Changed to sorted(available_charts) to maintain alphabetical order within groups
            st.sidebar.markdown(f"**圖表說明:** {chart_requirements[chart_option]['description']}")
        else:
            chart_option = None
            st.sidebar.warning("當前上傳的檔案沒有足夠的數據來生成任何建議的圖表。")
            
        # --- 主內容區塊的圖表顯示邏輯 ---
        if chart_option:
            # 顯示資料概覽
            if chart_option == "資料概覽表格":
                st.subheader("📚 資料集概覽")
                st.write("這是您的資料集：")
                st.dataframe(df) # 顯示整個 DataFrame，並可滑動

                # 重新加入 df.info()
                st.write("---") # 分隔線
                st.write("資料集資訊：")
                import io
                buffer = io.StringIO()
                df.info(buf=buffer, verbose=True, show_counts=True)
                st.text(buffer.getvalue())
                
                # 重新加入描述性統計
                st.write("---") # 分隔線
                st.write("數值欄位的描述性統計：")
                st.dataframe(df.describe().T)
                
                st.write("---") # 分隔線
                st.write("類別欄位的描述性統計：")
                st.dataframe(df.describe(include='object').T)

            # 動態生成數值欄位直方圖
            elif chart_option == "數值欄位分佈直方圖":
                st.subheader("📈 數值欄位分佈直方圖")
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                if numeric_cols:
                    selected_num_col = st.selectbox("請選擇一個數值欄位來繪製直方圖：", sorted(numeric_cols), key="dynamic_hist_col")
                    if selected_num_col:
                        df_valid = df.dropna(subset=[selected_num_col])
                        if not df_valid.empty:
                            fig = px.histogram(df_valid, x=selected_num_col,
                                               title=f"{selected_num_col} 的分佈",
                                               labels={selected_num_col: selected_num_col},
                                               nbins=30)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"欄位 '{selected_num_col}' 沒有足夠的非空數據來繪製直方圖。")
                else:
                    st.warning("資料集中沒有數值型欄位可供繪製直方圖。")

            # 動態生成類別欄位計數長條圖
            elif chart_option == "類別欄位計數長條圖":
                st.subheader("📊 類別欄位計數長條圖")
                categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                if categorical_cols:
                    selected_cat_col = st.selectbox("請選擇一個類別欄位來繪製長條圖：", sorted(categorical_cols), key="dynamic_bar_col")
                    if selected_cat_col:
                        df_valid = df.dropna(subset=[selected_cat_col])
                        if not df_valid.empty:
                            # 取前20個最常見的類別，避免圖形過於擁擠
                            top_categories = df_valid[selected_cat_col].value_counts().nlargest(20).index.tolist()
                            plot_df = df_valid[df_valid[selected_cat_col].isin(top_categories)]

                            fig = px.bar(plot_df, y=selected_cat_col, orientation='h',
                                         title=f"{selected_cat_col} 的計數分佈 (前20)",
                                         labels={selected_cat_col: selected_cat_col, "count": "計數"})
                            fig.update_layout(yaxis={'categoryorder':'total ascending'}) # 讓數量多的在上方
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"欄位 '{selected_cat_col}' 沒有足夠的非空數據來繪製長條圖。")
                else:
                    st.warning("資料集中沒有類別型欄位可供繪製長條圖。")

            # 新增的「任意兩數值欄位散佈圖」邏輯
            elif chart_option == "任意兩數值欄位散佈圖":
                st.subheader("📈 任意兩數值欄位散佈圖")
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                
                if len(numeric_cols) >= 2:
                    col1 = st.selectbox("選擇 X 軸欄位：", sorted(numeric_cols), key="scatter_x_col")
                    col2 = st.selectbox("選擇 Y 軸欄位：", sorted([c for c in numeric_cols if c != col1]), key="scatter_y_col")

                    if col1 and col2:
                        df_valid = df.dropna(subset=[col1, col2])
                        if not df_valid.empty:
                            fig = px.scatter(df_valid, x=col1, y=col2,
                                             title=f"{col1} vs {col2} 散佈圖",
                                             labels={col1: col1, col2: col2},
                                             hover_name="Name" if "Name" in df_valid.columns else None, # 如果有公司名稱欄位，顯示在懸停提示中
                                             color="Industry" if "Industry" in df_valid.columns else None, # 如果有產業欄位，按產業區分顏色
                                             trendline="ols" if len(df_valid) > 2 else None) # 如果數據點夠多，顯示趨勢線
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"所選欄位 '{col1}' 和 '{col2}' 沒有足夠的非空數據來繪製散佈圖。")
                    else:
                        st.warning("請選擇兩個不同的數值欄位來繪製散佈圖。")
                else:
                    st.warning("資料集中數值型欄位不足兩個，無法繪製散佈圖。")

            elif chart_option == "產業市值長條圖（前 8 名）":
                st.subheader("🏭 各產業市值分佈 (前 8 名)")
                df_valid = df.dropna(subset=["Industry", "Market Capitalization"])
                if not df_valid.empty:
                    industry_market = df_valid.groupby("Industry", as_index=False)["Market Capitalization"].sum()
                    industry_market = industry_market.sort_values("Market Capitalization", ascending=False)

                    top_n = 8
                    top_industries = industry_market.head(top_n) # 只取前 N 名，不包含「其他」
                    
                    fig = px.bar(top_industries,
                                 x="Industry", y="Market Capitalization",
                                 title="前 8 名產業市值",
                                 text_auto=True,
                                 labels={"Market Capitalization": "市值"})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Industry』和『Market Capitalization』數據來繪製此圖。")

            elif chart_option == "資產結構圓餅圖（單一公司）":
                st.subheader("🏢 公司資產結構")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="asset_pie_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    pie_cols = {"Net block": "淨固定資產", "Current assets": "流動資產", "Investments": "投資"}
                    plot_data = pd.DataFrame([
                        {'資產類型': display_name, '金額': company_data[col]}
                        for col, display_name in pie_cols.items()
                        if col in company_data and pd.notna(company_data[col]) and company_data[col] > 0
                    ])

                    if not plot_data.empty:
                        fig = px.pie(plot_data,
                                     values='金額',
                                     names='資產類型',
                                     title=f"{selected_company} 的資產結構",
                                     hole=0.3)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的『淨固定資產』、『流動資產』或『投資』數據（或數據為零/負數）來繪製資產結構圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製資產結構圖。")

            elif chart_option == "負債 vs 營運資金（散佈圖）":
                st.subheader("📉 負債 vs 營運資金")
                df_valid = df.dropna(subset=["Debt", "Working capital", "Name"])
                if not df_valid.empty:
                    fig = px.scatter(df_valid,
                                     x="Debt", y="Working capital",
                                     hover_name="Name",
                                     title="負債與營運資金的關係",
                                     labels={"Debt": "負債", "Working capital": "營運資金"},
                                     color="Industry" if "Industry" in df_valid.columns else None,
                                     trendline="ols" if len(df_valid) > 2 else None)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Debt』或『Working capital』數據來繪製此圖。")

            elif chart_option == "財務比率表格":
                st.subheader("📋 財務比率表格")
                show_cols = ["Name", "負債比率 (%)", "流動比率", "總股東權益", "Balance sheet total"]
                available_cols = [col for col in show_cols if col in df.columns]
                if available_cols:
                    st.dataframe(df[available_cols].round(2))
                else:
                    st.warning("無法顯示財務比率表格，因為缺少所需的計算欄位或原始欄位。")

            elif chart_option == "各年度營收趨勢圖（單一公司）":
                st.subheader("📈 各年度營收趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="sales_trend_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    sales_series = {}
                    if "Sales" in company_data and pd.notna(company_data["Sales"]): sales_series["最新年度"] = company_data["Sales"]
                    if "Sales last year" in company_data and pd.notna(company_data["Sales last year"]): sales_series["去年"] = company_data["Sales last year"]
                    if "Sales preceding year" in company_data and pd.notna(company_data["Sales preceding year"]): sales_series["前年"] = company_data["Sales preceding year"]

                    sales_df = pd.DataFrame(sales_series.items(), columns=['年度', '營收']).dropna()
                    
                    if not sales_df.empty:
                        year_order = {"前年": 0, "去年": 1, "最新年度": 2}
                        sales_df["_sort_key"] = sales_df["年度"].map(year_order)
                        sales_df = sales_df.sort_values("_sort_key").drop(columns="_sort_key")

                        fig = px.line(sales_df, x='年度', y='營收',
                                      title=f"{selected_company} 年度營收趨勢",
                                      markers=True,
                                      labels={"營收": "營收"})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的年度營收數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製營收趨勢圖。")

            elif chart_option == "各年度淨利潤趨勢圖（單一公司）":
                st.subheader("📈 各年度淨利潤趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="profit_trend_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    profit_series = {}
                    if "Profit after tax" in company_data and pd.notna(company_data["Profit after tax"]): profit_series["最新年度"] = company_data["Profit after tax"]
                    if "Profit after tax last year" in company_data and pd.notna(company_data["Profit after tax last year"]): profit_series["去年"] = company_data["Profit after tax last year"]
                    if "Profit after tax preceding year" in company_data and pd.notna(company_data["Profit after tax preceding year"]): profit_series["前年"] = company_data["Profit after tax preceding year"]

                    profit_df = pd.DataFrame(profit_series.items(), columns=['年度', '淨利潤']).dropna()

                    if not profit_df.empty:
                        year_order = {"前年": 0, "去年": 1, "最新年度": 2}
                        profit_df["_sort_key"] = profit_df["年度"].map(year_order)
                        profit_df = profit_df.sort_values("_sort_key").drop(columns="_sort_key")

                        fig = px.line(profit_df, x='年度', y='淨利潤',
                                      title=f"{selected_company} 年度淨利潤趨勢",
                                      markers=True,
                                      labels={"淨利潤": "淨利潤"})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的年度淨利潤數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製淨利潤趨勢圖。")

            elif chart_option == "各年度EPS趨勢圖（單一公司）":
                st.subheader("📈 各年度EPS趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="eps_trend_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    eps_series = {}
                    if "EPS" in company_data and pd.notna(company_data["EPS"]): eps_series["最新年度"] = company_data["EPS"]
                    if "EPS last year" in company_data and pd.notna(company_data["EPS last year"]): eps_series["去年"] = company_data["EPS last year"]
                    if "EPS preceding year" in company_data and pd.notna(company_data["EPS preceding year"]): eps_series["前年"] = company_data["EPS preceding year"]

                    eps_df = pd.DataFrame(eps_series.items(), columns=['年度', 'EPS']).dropna()

                    if not eps_df.empty:
                        year_order = {"前年": 0, "去年": 1, "最新年度": 2}
                        eps_df["_sort_key"] = eps_df["年度"].map(year_order)
                        eps_df = eps_df.sort_values("_sort_key").drop(columns="_sort_key")

                        fig = px.line(eps_df, x='年度', y='EPS',
                                      title=f"{selected_company} 年度EPS趨勢",
                                      markers=True)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的年度EPS數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製EPS趨勢圖。")

            elif chart_option == "ROE與ROCE比較圖（單一公司，最新年度）":
                st.subheader("📈 ROE 與 ROCE 比較")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="roce_roe_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    metrics_data = {}
                    if "Return on equity" in company_data and pd.notna(company_data["Return on equity"]):
                        metrics_data["股東權益報酬率 (ROE)"] = company_data["Return on equity"]
                    if "Return on capital employed" in company_data and pd.notna(company_data["Return on capital employed"]):
                        metrics_data["資本運用報酬率 (ROCE)"] = company_data["Return on capital employed"]
                    
                    metrics_df = pd.DataFrame(metrics_data.items(), columns=['指標', '數值']).dropna()

                    if not metrics_df.empty:
                        fig = px.bar(metrics_df, x='指標', y='數值',
                                     title=f"{selected_company} 股東權益報酬率與資本運用報酬率 (最新年度)",
                                     text_auto=True,
                                     labels={"數值": "百分比 (%)"})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的 ROE 或 ROCE 數據來繪製。")
                else:
                    st.warning("沒有可供選擇的公司來繪製 ROE/ROCE 圖。")

            elif chart_option == "本益比與股東權益報酬率散佈圖":
                st.subheader("💹 本益比與股東權益報酬率")
                df_valid = df.dropna(subset=["Price to Earning", "Return on equity", "Name"])
                if not df_valid.empty:
                    fig = px.scatter(df_valid,
                                     x="Price to Earning", y="Return on equity",
                                     hover_name="Name",
                                     title="本益比 (P/E) 與股東權益報酬率 (ROE) 的關係",
                                     labels={"Price to Earning": "本益比", "Return on equity": "股東權益報酬率 (%)"},
                                     color="Industry" if "Industry" in df.columns else None, # 如果有產業欄位，可以按產業區分顏色
                                     size="Market Capitalization" if "Market Capitalization" in df.columns else None, # 以市值大小區分點大小
                                     hover_data=["Industry", "Market Capitalization"] if "Industry" in df.columns and "Market Capitalization" in df.columns else None
                                     )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Price to Earning』或『Return on equity』數據來繪製此圖。")

            elif chart_option == "銷售額成長率排名（前20）":
                st.subheader("🏆 銷售額成長率排名 (前 20 名)")
                df_valid = df.dropna(subset=["Name", "Sales growth 3Years"])
                if not df_valid.empty:
                    top_sales_growth = df_valid.sort_values("Sales growth 3Years", ascending=False).head(20)
                    fig = px.bar(top_sales_growth,
                                 x="Name", y="Sales growth 3Years",
                                 title="銷售額成長率 (3 年) 前 20 名公司",
                                 text_auto=True,
                                 labels={"Sales growth 3Years": "銷售額成長率 (%)"})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Sales growth 3Years』數據來進行排名。")

            elif chart_option == "利潤成長率排名（前20）":
                st.subheader("💰 利潤成長率排名 (前 20 名)")
                df_valid = df.dropna(subset=["Name", "Profit growth 3Years"])
                if not df_valid.empty:
                    top_profit_growth = df_valid.sort_values("Profit growth 3Years", ascending=False).head(20)
                    fig = px.bar(top_profit_growth,
                                 x="Name", y="Profit growth 3Years",
                                 title="利潤成長率 (3 年) 前 20 名公司",
                                 text_auto=True,
                                 labels={"Profit growth 3Years": "利潤成長率 (%)"})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Profit growth 3Years』數據來進行排名。")
            
            elif chart_option == "現金流量概覽圓餅圖（單一公司，最近一年）":
                st.subheader("💸 現金流量概覽")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="cash_flow_pie_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    cash_flow_sources = {
                        "來自營運的現金": company_data.get("Cash from operations last year"),
                        "來自投資的現金": company_data.get("Cash from investing last year"),
                        "來自融資的現金": company_data.get("Cash from financing last year")
                    }
                    
                    cash_flow_df = pd.DataFrame(list(cash_flow_sources.items()), columns=['來源', '金額'])
                    cash_flow_df['金額'] = pd.to_numeric(cash_flow_df['金額'], errors='coerce') 
                    cash_flow_df = cash_flow_df.dropna()
                    cash_flow_df = cash_flow_df[cash_flow_df['金額'] != 0] 

                    if not cash_flow_df.empty:
                        fig = px.pie(cash_flow_df, values='金額', names='來源',
                                     title=f"{selected_company} 最近一年現金流量概覽",
                                     hole=0.3)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的現金流量數據來繪製概覽圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製現金流量概覽圖。")

            elif chart_option == "自由現金流趨勢圖（單一公司）":
                st.subheader("💰 自由現金流趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="fcf_trend_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    fcf_data = {}
                    fcf_years_map = {
                        "10年前": "Free cash flow 10years", "7年前": "Free cash flow 7years",
                        "5年前": "Free cash flow 5years", "3年前": "Free cash flow 3years",
                        "前年": "Free cash flow preceding year", "去年": "Free cash flow last year",
                        "最新年度": "Free cash flow"
                    }
                    
                    for year_label, col_name in fcf_years_map.items():
                        if col_name in company_data and pd.notna(company_data[col_name]):
                            fcf_data[year_label] = company_data[col_name]

                    fcf_df = pd.DataFrame(fcf_data.items(), columns=['年度', '自由現金流']).dropna()
                    
                    if not fcf_df.empty:
                        year_order_keys = list(fcf_years_map.keys())
                        fcf_df['年度_排序'] = fcf_df['年度'].apply(lambda x: year_order_keys.index(x))
                        fcf_df = fcf_df.sort_values('年度_排序').drop(columns='年度_排序')

                        fig = px.line(fcf_df, x='年度', y='自由現金流',
                                      title=f"{selected_company} 自由現金流趨勢",
                                      markers=True,
                                      labels={"自由現金流": "自由現金流"})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的自由現金流數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製自由現金流趨勢圖。")
            
            elif chart_option == "股價相對表現趨勢圖（單一公司）":
                st.subheader("📈 股價相對表現趨勢")
                company_list = df["Name"].dropna().unique().tolist()
                if company_list:
                    selected_company = st.selectbox("請選擇公司", sorted(company_list), key="price_trend_company")
                    company_data = df[df["Name"] == selected_company].iloc[0]

                    returns_data = {}
                    if "Current Price" in company_data and pd.notna(company_data["Current Price"]):
                        returns_data["最新股價"] = company_data["Current Price"]
                    if "t_1_price" in company_data and pd.notna(company_data["t_1_price"]):
                        returns_data["前一個交易日價格"] = company_data["t_1_price"]
                    if "Return over 1year" in company_data and pd.notna(company_data["Return over 1year"]):
                        returns_data["1年回報率 (%)"] = company_data["Return over 1year"]
                    if "Return over 3years" in company_data and pd.notna(company_data["Return over 3years"]):
                        returns_data["3年回報率 (%)"] = company_data["Return over 3years"]
                    if "Return over 5years" in company_data and pd.notna(company_data["Return over 5years"]):
                        returns_data["5年回報率 (%)"] = company_data["Return over 5years"]
                    
                    if returns_data:
                        # 將股價和回報率分開處理，回報率適合條形圖
                        price_metrics = {k: v for k, v in returns_data.items() if "股價" in k or "價格" in k}
                        returns_metrics = {k: v for k, v in returns_data.items() if "回報率" in k}

                        if price_metrics:
                            st.markdown("##### 關鍵股價指標")
                            for label, value in price_metrics.items():
                                st.metric(label=f"{selected_company} {label}", value=f"{value:.2f}")

                        if returns_metrics:
                            returns_df = pd.DataFrame(returns_metrics.items(), columns=['期間', '數值']).dropna()
                            if not returns_df.empty:
                                fig = px.bar(returns_df, x='期間', y='數值',
                                             title=f"{selected_company} 股價回報率 (%)",
                                             text_auto=True,
                                             labels={"數值": "回報率 (%)"})
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning(f"公司 {selected_company} 沒有足夠的股價回報率數據來繪製圖表。")
                        elif not price_metrics: # 如果連價格數據都沒有
                            st.warning(f"公司 {selected_company} 沒有足夠的股價或回報率數據來繪製趨勢圖。")
                    else:
                        st.warning(f"公司 {selected_company} 沒有足夠的股價或回報率數據來繪製趨勢圖。")
                else:
                    st.warning("沒有可供選擇的公司來繪製股價相對表現趨勢圖。")

            elif chart_option == "市值分佈直方圖":
                st.subheader("📈 市值分佈")
                df_valid = df.dropna(subset=["Market Capitalization"])
                if not df_valid.empty:
                    fig = px.histogram(df_valid, x="Market Capitalization",
                                       title="公司市值分佈",
                                       labels={"Market Capitalization": "市值"},
                                       nbins=20)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Market Capitalization』數據來繪製市值分佈直方圖。")

            elif chart_option == "銷售額與淨利潤關係散佈圖":
                st.subheader("💹 銷售額與淨利潤關係")
                df_valid = df.dropna(subset=["Sales", "Net profit", "Name"])
                if not df_valid.empty:
                    fig = px.scatter(df_valid,
                                     x="Sales", y="Net profit",
                                     hover_name="Name",
                                     title="公司銷售額與淨利潤的關係",
                                     labels={"Sales": "銷售額", "Net profit": "淨利潤"},
                                     color="Industry" if "Industry" in df.columns else None, # 如果有產業欄位，可以按產業區分顏色
                                     size="Market Capitalization" if "Market Capitalization" in df.columns else None, # 以市值大小區分點大小
                                     hover_data=["Industry", "Market Capitalization"] if "Industry" in df.columns and "Market Capitalization" in df.columns else None
                                     )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Sales』或『Net profit』數據來繪製此圖。")

            elif chart_option == "平均股東權益報酬率排名（前20）":
                st.subheader("📊 平均股東權益報酬率排名 (前 20 名)")
                df_valid = df.dropna(subset=["Name", "Average return on equity 5Years"])
                if not df_valid.empty:
                    top_roe = df_valid.sort_values("Average return on equity 5Years", ascending=False).head(20)
                    fig = px.bar(top_roe,
                                 x="Name", y="Average return on equity 5Years",
                                 title="平均股東權益報酬率 (5 年) 前 20 名公司",
                                 text_auto=True,
                                 labels={"Average return on equity 5Years": "平均股東權益報酬率 (%)"})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("沒有足夠的『Average return on equity 5Years』數據來進行排名。")

            elif chart_option == "發起人持股比例分佈（圓餅圖）":
                st.subheader("🤝 發起人持股比例分佈")
                
                # 檢查是否有足夠的公司來選擇
                company_list = df["Name"].dropna().unique().tolist()
                
                required_holding_cols = ["Promoter holding", "FII holding", "DII holding", "Public holding"]

                # 過濾掉那些沒有完整持股數據的公司
                df_with_holdings = df.dropna(subset=required_holding_cols, how='any')

                if not df_with_holdings.empty:
                    # 選項：平均或單一公司
                    holding_view_option = st.radio(
                        "選擇視圖方式：",
                        ("所有公司平均", "單一公司"),
                        key="holding_view_option"
                    )

                    plot_data = pd.DataFrame()
                    chart_title = ""

                    # 持股類型名稱映射
                    type_map = {
                        "Promoter holding": "發起人持股",
                        "FII holding": "外資持股",
                        "DII holding": "本土機構持股",
                        "Public holding": "公眾持股"
                    }

                    if holding_view_option == "所有公司平均":
                        # 計算平均持股比例
                        avg_holdings = df_with_holdings[required_holding_cols].mean()
                        plot_data = pd.DataFrame(avg_holdings).reset_index()
                        plot_data.columns = ['持股類型', '比例']
                        plot_data['持股類型'] = plot_data['持股類型'].map(type_map)
                        chart_title = "所有公司平均持股比例分佈"
                    else: # 單一公司
                        # 確保選擇的公司有持股數據
                        available_companies_for_holdings = df_with_holdings["Name"].dropna().unique().tolist()
                        if available_companies_for_holdings:
                            selected_company = st.selectbox(
                                "請選擇公司", 
                                sorted(available_companies_for_holdings), # 確保只顯示有持股數據的公司
                                key="holding_company_select"
                            )
                            if selected_company:
                                company_data = df_with_holdings[df_with_holdings["Name"] == selected_company].iloc[0]
                                holdings = {col: company_data[col] for col in required_holding_cols}
                                plot_data = pd.DataFrame(holdings.items(), columns=['持股類型', '比例'])
                                plot_data['持股類型'] = plot_data['持股類型'].map(type_map)
                                chart_title = f"{selected_company} 持股比例分佈"
                            else:
                                st.warning("請選擇一家公司以查看其持股比例分佈。")
                        else:
                            st.warning("沒有可供選擇的公司來繪製持股比例分佈圖 (數據不足)。")


                    if not plot_data.empty:
                        # 確保比例之和為 100，避免圓餅圖出錯
                        total_percentage = plot_data['比例'].sum()
                        # 僅在總和不為零時進行歸一化
                        if total_percentage > 0:
                            plot_data['比例'] = (plot_data['比例'] / total_percentage) * 100
                        else:
                            st.warning(f"選擇的公司/所有公司沒有有效的持股比例數據（總和為零或負數）。")
                            plot_data = pd.DataFrame() # 清空資料，避免繪圖
                        
                        if not plot_data.empty: # 再次檢查是否為空
                            fig = px.pie(plot_data, 
                                         values='比例', 
                                         names='持股類型',
                                         title=chart_title,
                                         hole=0.3)
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("沒有足夠的發起人持股比例數據來繪製此圖。")
                else:
                    st.warning("數據中沒有足夠的『Promoter holding』、『FII holding』、『DII holding』或『Public holding』數據來繪製此圖。")

    except Exception as e:
        st.error(f"處理檔案時發生錯誤：{e}")
        st.info("請檢查您的 CSV/Excel 檔案格式是否正確，並包含所需的欄位。")
