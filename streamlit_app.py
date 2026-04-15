import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
from scipy.interpolate import interp1d

st.set_page_config(page_title="中药离子透析实验数据处理", layout="wide")
st.title("🌿 中药离子透析实验数据处理")
st.markdown("根据标准曲线将电流值转换为离子相对浓度，评价中药有效成分的透析效果。")

# ==================== 初始化 session_state ====================
if "std_df" not in st.session_state:
    default_std = pd.DataFrame({
        "浓度 (%)": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        "电流 (mA)": [0.12, 0.24, 0.36, 0.48, 0.60, 0.72, 0.84, 0.96]
    })
    st.session_state.std_df = default_std
if "sample_data" not in st.session_state:
    default_samples = pd.DataFrame({
        "样品": ["当归", "大黄", "金银花"],
        "原液电流 (mA)": [0.50, 0.55, 0.48],
        "透析液电流 (mA)": [0.25, 0.30, 0.22]
    })
    st.session_state.sample_data = default_samples
if "std_interp" not in st.session_state:
    st.session_state.std_interp = None

# ==================== 辅助函数 ====================
def fit_standard_curve(df):
    x = df["电流 (mA)"].values
    y = df["浓度 (%)"].values
    if len(x) < 2:
        return None
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    def predict(Current):
        return slope * Current + intercept
    return predict, slope, intercept, r_value**2

def compute_concentration(df_samples, predict_func):
    df = df_samples.copy()
    df["原液相当浓度 (%)"] = df["原液电流 (mA)"].apply(predict_func)
    df["透析液相当浓度 (%)"] = df["透析液电流 (mA)"].apply(predict_func)
    df["透析率 (%)"] = (df["透析液相当浓度 (%)"] / df["原液相当浓度 (%)"]) * 100
    return df

# ==================== 侧边栏：标准曲线 ====================
st.sidebar.header("📈 标准曲线")
std_source = st.sidebar.radio("标准曲线数据来源", ["使用示例数据", "手动编辑表格", "上传 CSV"], key="std_source")
if std_source == "使用示例数据":
    std_df = st.session_state.std_df.copy()
elif std_source == "手动编辑表格":
    std_df = st.data_editor(st.session_state.std_df, num_rows="dynamic", key="std_editor")
else:
    uploaded_std = st.sidebar.file_uploader("上传 CSV (列: 浓度 (%), 电流 (mA))", type="csv")
    if uploaded_std:
        std_df = pd.read_csv(uploaded_std)
    else:
        std_df = st.session_state.std_df.copy()
st.session_state.std_df = std_df

if st.sidebar.button("拟合标准曲线"):
    if std_df.shape[0] < 2:
        st.sidebar.error("至少需要2个数据点")
    else:
        predict_func, slope, intercept, r2 = fit_standard_curve(std_df)
        st.session_state.std_interp = predict_func
        st.session_state.slope = slope
        st.session_state.intercept = intercept
        st.session_state.r2 = r2
        st.sidebar.success(f"拟合方程: 浓度 = {slope:.4f} × 电流 + {intercept:.4f}\nR² = {r2:.4f}")

# 显示标准曲线图
if st.session_state.std_interp is not None:
    st.subheader("📊 标准曲线")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=std_df["电流 (mA)"], y=std_df["浓度 (%)"], mode='markers', name='实验点', marker=dict(size=8)))
    x_range = np.linspace(std_df["电流 (mA)"].min(), std_df["电流 (mA)"].max(), 100)
    y_fit = st.session_state.slope * x_range + st.session_state.intercept
    fig.add_trace(go.Scatter(x=x_range, y=y_fit, mode='lines', name='拟合线', line=dict(color='red')))
    fig.update_layout(title="浓度-电流标准曲线", xaxis_title="电流 (mA)", yaxis_title="浓度 (%)")
    st.plotly_chart(fig, use_container_width=True)

# ==================== 样品数据录入 ====================
st.header("🧪 样品数据（中药离子透析）")
st.markdown("输入各样品原液和透析液的电流值")
sample_source = st.radio("样品数据来源", ["使用示例数据", "手动编辑表格", "上传 CSV"], key="sample_source")
if sample_source == "使用示例数据":
    sample_df = st.session_state.sample_data.copy()
elif sample_source == "手动编辑表格":
    sample_df = st.data_editor(
        st.session_state.sample_data,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "样品": st.column_config.TextColumn("样品"),
            "原液电流 (mA)": st.column_config.NumberColumn("原液电流 (mA)", format="%.3f"),
            "透析液电流 (mA)": st.column_config.NumberColumn("透析液电流 (mA)", format="%.3f")
        }
    )
else:
    uploaded_sample = st.file_uploader("上传 CSV (列: 样品, 原液电流 (mA), 透析液电流 (mA))", type="csv")
    if uploaded_sample:
        sample_df = pd.read_csv(uploaded_sample)
    else:
        sample_df = st.session_state.sample_data.copy()
st.session_state.sample_data = sample_df

# ==================== 计算浓度及透析率 ====================
if st.button("🔍 计算相当浓度及透析率"):
    if st.session_state.std_interp is None:
        st.error("请先在侧边栏拟合标准曲线")
    else:
        result_df = compute_concentration(sample_df, st.session_state.std_interp)
        st.session_state.result_df = result_df
        st.subheader("📋 计算结果")
        st.dataframe(result_df, use_container_width=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=result_df["样品"], y=result_df["透析率 (%)"], name="透析率", marker_color='green'))
        fig.update_layout(title="中药离子透析率", yaxis_title="透析率 (%)")
        st.plotly_chart(fig, use_container_width=True)
        st.session_state.calculated = True

# ==================== 报告生成 ====================
st.markdown("---")
st.subheader("🖨️ 生成实验报告（PDF）")
if st.button("📄 生成并打印报告"):
    if not hasattr(st.session_state, 'result_df') or st.session_state.result_df is None:
        st.warning("请先点击上方按钮进行计算")
    else:
        result_df = st.session_state.result_df
        std_df = st.session_state.std_df
        result_html = result_df.to_html(index=False)
        std_html = std_df.to_html(index=False)
        if hasattr(st.session_state, 'slope'):
            std_eq = f"浓度 = {st.session_state.slope:.4f} × 电流 + {st.session_state.intercept:.4f}, R² = {st.session_state.r2:.4f}"
        else:
            std_eq = "未拟合"
        full_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>中药离子透析实验报告</title>
            <style>
                body {{ font-family: 'SimHei', 'Microsoft YaHei', Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; border-bottom: 1px solid #ddd; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #f2f2f2; }}
                .info {{ margin: 20px 0; padding: 10px; background-color: #f9f9f9; border-left: 4px solid #2c3e50; }}
            </style>
        </head>
        <body>
            <h1>中药离子透析实验报告</h1>
            <p>生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <h2>1. 标准曲线数据</h2>
            {std_html}
            <div class="info"><strong>标准曲线方程：</strong> {std_eq}</div>
            <h2>2. 样品测定结果</h2>
            {result_html}
            <h2>3. 实验结论</h2>
            <p>根据标准曲线计算各中药原液和透析液的相当浓度，透析率越高表示有效离子透过半透膜的能力越强。</p>
            <script>window.onload = function() {{ window.print(); }};</script>
        </body>
        </html>
        """
        st.components.v1.html(full_html, height=0, scrolling=False)
        st.success("报告已生成，请在弹出的打印对话框中选择「另存为 PDF」")

# ==================== 数据导出 ====================
if hasattr(st.session_state, 'result_df') and st.session_state.result_df is not None:
    st.subheader("💾 导出计算结果")
    csv = st.session_state.result_df.to_csv(index=False).encode('utf-8')
    st.download_button("下载 CSV", csv, "ion_dialysis_results.csv", "text/csv")

with st.expander("ℹ️ 实验原理及方法"):
    st.markdown("""
    **1. 实验原理**  
    中药离子透析法利用电场作用，使药液中的离子透过半透膜进入接收液。通过测量透析前后接收液的电流变化，结合标准曲线（浓度-电流）计算离子相对浓度，评价中药有效成分的透析性能。

    **2. 标准曲线**  
    用已知浓度的氯化钾溶液测定电流，建立浓度与电流的线性关系，采用最小二乘法拟合。

    **3. 透析率计算**  
    \[
    \text{透析率} = \frac{\text{透析液相当浓度}}{\text{原液相当浓度}} \times 100\%
    \]
    """)
