import streamlit as st
import pandas as pd
import plotly.express as px
import io

# 設定 Streamlit 頁面配置
st.set_page_config(page_title="簡易 CSV 資料分析器", layout="wide")

st.title("📊 簡易 CSV 資料分析器")
st.markdown("---")  # 分隔線

# --- API Key 輸入（存到 session_state） ---
st.write("### 🔑 請輸入您的 API Key")

if "api_key" not in st.session_state:
    st.session_state.api_key = ""  # 預設空值

# 使用秘密輸入框
user_api_key = st.text_input("輸入 API Key", type="password", value=st.session_state.api_key)

# 更新 session_state
if user_api_key:
    st.session_state.api_key = user_api_key
    st.success("API Key 已輸入 ✅")
else:
    st.warning("請輸入 API Key 才能繼續使用此工具")

# 🔘 清除 API Key 按鈕
if st.session_state.api_key:
    if st.button("🚪 登出 / 清除 API Key"):
        st.session_state.api_key = ""
        st.experimental_rerun()  # 重新整理頁面讓輸入框歸零

st.markdown("---")  # 分隔線

st.write("### 📤 上傳您的 CSV 檔案")

# 1. 上傳 CSV 檔案的按鈕
uploaded_file = st.file_uploader("點擊此處上傳 CSV 檔案", type=["csv"])

# 檢查是否有檔案被上傳 & API Key 已輸入
if uploaded_file is not None and st.session_state.api_key:
    try:
        # 讀取 CSV 檔案到 DataFrame
        df = pd.read_csv(uploaded_file)
        st.success("CSV 檔案上傳成功！")

        # 2. 顯示資料集的前幾行，改為可滑動預覽全部
        st.write("### 📖 資料集預覽:")
        st.dataframe(df)  # 顯示整個 DataFrame，Streamlit 會自動使其可滑動

        st.markdown("---")  # 分隔線
        st.write("### 📈 數據視覺化")

        # 動態獲取數值型和類別型欄位
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()

        if not numeric_columns and not categorical_columns:
            st.warning("數據集中沒有可供繪圖的數值或類別欄位。")
        else:
            # 選擇圖表類型
            chart_type = st.selectbox(
                "選擇您想繪製的圖表類型:",
                ["請選擇", "長條圖 (Bar Chart)", "折線圖 (Line Chart)", "散佈圖 (Scatter Plot)"]
            )

            if chart_type == "長條圖 (Bar Chart)":
                if categorical_columns:
                    st.write("#### 長條圖設定")
                    x_axis_col = st.selectbox("選擇 X 軸 (類別型):", sorted(categorical_columns), key="bar_x")
                    y_axis_col = st.selectbox("選擇 Y 軸 (數值型, 可選):", ["None"] + sorted(numeric_columns), key="bar_y")

                    if x_axis_col:
                        if y_axis_col == "None":
                            plot_df = df[x_axis_col].value_counts().reset_index()
                            plot_df.columns = [x_axis_col, 'Count']
                            fig = px.bar(plot_df, x=x_axis_col, y='Count',
                                         title=f"{x_axis_col} 的計數分佈")
                        else:
                            if not df[y_axis_col].dropna().empty:
                                fig = px.bar(df, x=x_axis_col, y=y_axis_col,
                                             title=f"{x_axis_col} 對 {y_axis_col} 的長條圖")
                            else:
                                st.warning(f"選擇的 Y 軸 '{y_axis_col}' 沒有足夠的非空數據來繪製長條圖。")
                                fig = None
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("沒有可供選擇的類別欄位來繪製長條圖。")
                else:
                    st.warning("您的資料集中沒有類別型欄位，無法繪製長條圖。")

            elif chart_type == "折線圖 (Line Chart)":
                if numeric_columns:
                    st.write("#### 折線圖設定")
                    x_axis_col_line = st.selectbox("選擇 X 軸 (數值型):", sorted(numeric_columns), key="line_x")
                    y_axis_col_line = st.selectbox("選擇 Y 軸 (數值型):", sorted([col for col in numeric_columns if col != x_axis_col_line]), key="line_y")

                    if x_axis_col_line and y_axis_col_line:
                        df_valid = df.dropna(subset=[x_axis_col_line, y_axis_col_line])
                        if not df_valid.empty:
                            fig = px.line(df_valid, x=x_axis_col_line, y=y_axis_col_line,
                                          title=f"{x_axis_col_line} 對 {y_axis_col_line} 的折線圖",
                                          markers=True)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"所選欄位 '{x_axis_col_line}' 和 '{y_axis_col_line}' 沒有足夠的非空數據來繪製折線圖。")
                    else:
                        st.warning("請選擇兩個不同的數值欄位來繪製折線圖。")
                else:
                    st.warning("您的資料集中沒有數值型欄位，無法繪製折線圖。")

            elif chart_type == "散佈圖 (Scatter Plot)":
                if len(numeric_columns) >= 2:
                    st.write("#### 散佈圖設定")
                    x_axis_col_scatter = st.selectbox("選擇 X 軸 (數值型):", sorted(numeric_columns), key="scatter_x")
                    y_axis_col_scatter = st.selectbox("選擇 Y 軸 (數值型):", sorted([col for col in numeric_columns if col != x_axis_col_scatter]), key="scatter_y")

                    if x_axis_col_scatter and y_axis_col_scatter:
                        df_valid = df.dropna(subset=[x_axis_col_scatter, y_axis_col_scatter])
                        if not df_valid.empty:
                            fig = px.scatter(df_valid, x=x_axis_col_scatter, y=y_axis_col_scatter,
                                             title=f"{x_axis_col_scatter} 對 {y_axis_col_scatter} 的散佈圖")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning(f"所選欄位 '{x_axis_col_scatter}' 和 '{y_axis_col_scatter}' 沒有足夠的非空數據來繪製散佈圖。")
                    else:
                        st.warning("請選擇兩個不同的數值欄位來繪製散佈圖。")
                else:
                    st.warning("您的資料集中至少需要兩個數值型欄位才能繪製散佈圖。")

    except Exception as e:
        st.error(f"讀取檔案時發生錯誤：{e}")
        st.info("請確認您的 CSV 檔案格式正確，且數據沒有異常。")
elif uploaded_file and not st.session_state.api_key:
    st.warning("請先輸入 API Key 才能分析 CSV")
else:
    st.info("請輸入 API Key 並上傳 CSV 檔案以開始分析。")
