import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

# --- 0. グローバル設定 ---
st.set_page_config(layout="wide", page_title="J.League Physical Dashboard")

# --- 1. 定数・カラー定義 ---
LEAGUE_FILE_MAP = {
    'J1': '2025_J1_physical_data.csv',
    'J2': '2025_J2_physical_data.csv',
    'J3': '2025_J3_physical_data.csv',
}

LEAGUE_COLOR_MAP = {'J1': '#E6002D', 'J2': '#127A3A', 'J3': '#014099'}

TEAM_COLORS = {
    # J1
    'Kashima Antlers': '#B71940','Kashiwa Reysol':"#FFF000",'Urawa Red Diamonds': '#E6002D',
    'FC Tokyo': "#3E4C8D",'Tokyo Verdy':"#006931",'FC Machida Zelvia':"#0056A5",
    'Kawasaki Frontale': "#319FDA",'Yokohama F. Marinos': "#014099",'Yokohama FC':"#4BC1FE",'Shonan Bellmare':"#9EFF26",
    'Albirex Niigata':"#FE641E",'Shimizu S-Pulse':"#FF8901",'Nagoya Grampus': "#F8B500",
    'Kyoto Sanga FC':"#820064",'Gamba Osaka': "#00458D",'Cerezo Osaka': "#DB005B",'Vissel Kobe': '#A60129',
    'Fagiano Okayama':"#A72041",'Sanfrecce Hiroshima':"#603D97",'Avispa Fukuoka':"#9EB5C7",
    # J2
    'Hokkaido Consadole Sapporo':"#125D75",'Vegalta Sendai':"#FFC20E",'AFC Blaublitz Akita':"#0D5790",'Montedio Yamagata':"#F7F4A6",'Iwaki SC':"#C01630",
    'Mito Hollyhock':"#2E3192",'Omiya Ardija':"#EC6601",'JEF United Ichihara Chiba':"#FFDE00",'Ventforet Kofu':"#0F63A3",
    'Kataller Toyama':"#25458F",'Jubilo Iwata':"#7294BA",'Fujieda MYFC':"#875884",'Renofa Yamaguchi':"#F26321",'Tokushima Vortis':"#11233F",'Ehime FC':"#ED9A4C",'FC Imabari':"#908E3C",
    'Sagan Tosu':"#30B7D7",'V-Varen Nagasaki':"#013893",'Roasso Kumamoto':"#A92D27",'Oita Trinita':"#254398",
    # J3
    'Vanraure Hachinohe':"#13A63B",'Fukushima United FC':"#CF230C",'Tochigi SC':"#0170A4",'Tochigi City':"#001030",'ThespaKusatsu Gunma':"#08406F",'SC Sagamihara':"#408B52",
    'AC Parceiro Nagano':"#E36A2A",'Matsumoto Yamaga FC':"#004B1D",'Ishikawa FC Zweigen Kanazawa':"#3B1216",'FC Azul Claro Numazu':"#13A7DE",'FC Gifu':"#126246",
    'FC Osaka':"#90C9E2",'Nara Club':"#011D64",'Gainare Tottori':"#96C692",'Kamatamare Sanuki':"#669FB9",'Kochi United SC':"#B21E23",
    'Giravanz Kitakyushu':"#E8BD00",'Tegevajaro Miyazaki FC':"#F6E066",'Kagoshima United FC':"#19315F",'FC Ryūkyū':"#AA131B",
}

physical_vars = [
    'Distance','Running Distance','HSR Distance','Sprint Count','HI Distance','HI Count',
    'Distance TIP','Running Distance TIP','HSR Distance TIP','HSR Count TIP',
    'Sprint Distance TIP','Sprint Count TIP','Distance OTIP','Running Distance OTIP',
    'HSR Distance OTIP','HSR Count OTIP','Sprint Distance OTIP','Sprint Count OTIP'
]
RANKING_METHODS = ['Total', 'Average', 'Max', 'Min']

# --- 2. ユーティリティ関数 ---
def to_excel(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ranking Data')
    return output.getvalue()

@st.cache_data(ttl=60*15)
def get_data(league_key):
    file_path = f"data/{LEAGUE_FILE_MAP.get(league_key)}"
    try:
        df = pd.read_csv(file_path)
        df['League'] = league_key
        if 'Match ID' in df.columns:
            # 節(Matchday)の算出
            sort_cols = ['Team', 'Match Date'] if 'Match Date' in df.columns else ['Team', 'Match ID']
            unique_matches = df[['Team', 'Match ID', 'Match Date']].drop_duplicates() if 'Match Date' in df.columns else df[['Team', 'Match ID']].drop_duplicates()
            if 'Match Date' in unique_matches.columns:
                unique_matches['Match Date'] = pd.to_datetime(unique_matches['Match Date'], errors='coerce')
            unique_matches = unique_matches.sort_values(by=sort_cols)
            unique_matches['Matchday'] = unique_matches.groupby('Team').cumcount() + 1
            df = pd.merge(df, unique_matches[['Team', 'Match ID', 'Matchday']], on=['Team', 'Match ID'], how='left')
        return df
    except:
        return pd.DataFrame()

# ★ 核心ロジック：1試合合計リストから集計し単位を統一
def apply_ranking_logic(df, method, target_var):
    # 1. 1試合ごとのチーム合計値を算出
    match_totals = df.groupby(['Team', 'Match ID'])[physical_vars].sum().reset_index()
    
    # 指標が0のデータを除外
    working_df = match_totals[match_totals[target_var] > 0].copy()
    
    if working_df.empty:
        return pd.DataFrame(), ""

    # 2. 指定された方法で集計
    if method == 'Total':
        res = working_df.groupby('Team')[target_var].sum().reset_index()
    elif method == 'Average':
        res = working_df.groupby('Team')[target_var].mean().reset_index()
    elif method == 'Max':
        res = working_df.groupby('Team')[target_var].max().reset_index()
    elif method == 'Min':
        res = working_df.groupby('Team')[target_var].min().reset_index()
    
    # 3. 単位の統一
    if 'Distance' in target_var:
        res[target_var] = res[target_var] / 1000
        unit = "km"
    else:
        unit = "回"
    return res, unit

# --- 3. 描画コンポーネント ---

def render_custom_ranking(df, league_name, team_colors):
    st.markdown("### 🏆 カスタムランキング作成")
    team = st.selectbox('注目チームを選択', sorted(df['Team'].unique()), key=f"focal_{league_name}")
    col1, col2 = st.columns(2)
    method = col1.selectbox('集計方法', RANKING_METHODS, key=f"meth_{league_name}")
    var = col2.selectbox('評価指標', physical_vars, key=f"var_{league_name}")
    
    res, unit = apply_ranking_logic(df, method, var)
    if res.empty: return

    is_asc = (method == 'Min')
    plot_df = res.sort_values(by=var, ascending=is_asc).reset_index(drop=True)
    plot_df = plot_df[::-1] # グラフ表示用に反転

    sns.set(rc={'axes.facecolor':'#fbf9f4', 'figure.facecolor':'#fbf9f4'})
    fig, ax = plt.subplots(figsize=(7, 8), dpi=200)
    nrows = plot_df.shape[0]
    ax.set_xlim(0, 3.5); ax.set_ylim(0, nrows + 1.5)

    for i in range(nrows):
        t_name = plot_df['Team'].iloc[i]
        val = plot_df[var].iloc[i]
        is_f = (t_name == team)
        c = team_colors.get(t_name, '#4A2E19') if is_f else '#4A2E19'
        ax.annotate(f"{nrows-i}  {t_name}", xy=(0.1, i + .5), va='center', color=c, weight='bold' if is_f else 'regular')
        ax.annotate(f"{round(val, 2)} {unit}", xy=(2.5, i + .5), va='center', color=c, weight='bold' if is_f else 'regular')
    
    ax.set_axis_off()
    st.pyplot(fig)

def render_league_dashboard(df, league_name, team_colors):
    st.header(f"🏆 {league_name} 分析ダッシュボード")
    tabs = st.tabs(['集計ランキング', 'カスタムランキング', 'シーズン動向分析'])
    
    with tabs[0]:
        c1, c2 = st.columns(2)
        m = c1.selectbox('集計方法', RANKING_METHODS, key=f'agg_m_{league_name}')
        v = c2.selectbox('指標', physical_vars, key=f'agg_v_{league_name}')
        
        res, unit = apply_ranking_logic(df, m, v)
        if not res.empty:
            is_asc = (m == 'Min')
            chart = alt.Chart(res).mark_bar().encode(
                y=alt.Y('Team:N', sort='x' if is_asc else '-x', title='チーム'),
                x=alt.X(v, title=f"{m} {v} ({unit})"),
                color=alt.Color('Team:N', scale=alt.Scale(domain=list(team_colors.keys()), range=list(team_colors.values())), legend=None),
                tooltip=['Team', alt.Tooltip(v, format='.2f', title=f"{v} ({unit})")]
            ).properties(height=600)
            st.altair_chart(chart, use_container_width=True)
            st.download_button(label=f"Excelダウンロード ({unit})", data=to_excel(res), file_name=f"{league_name}_{m}_{v}.xlsx")

    with tabs[1]:
        render_custom_ranking(df, league_name, team_colors)
    with tabs[2]:
        render_trend_analysis(df, league_name, team_colors)

def render_trend_analysis(df, league_name, team_colors):
    st.markdown(f"### 📈 シーズン動向分析 ({league_name})")
    all_teams = sorted(df['Team'].unique())
    c1, c2 = st.columns(2)
    sel_team = c1.selectbox('チーム', all_teams, key=f'tr_t_{league_name}')
    sel_var = c2.selectbox('項目', physical_vars, key=f'tr_v_{league_name}')
    
    # トレンド用データ：1試合合計値の推移
    match_data = df[df['Team'] == sel_team].groupby(['Matchday', 'Match ID'])[sel_var].sum().reset_index()
    
    if 'Distance' in sel_var:
        match_data[sel_var] = match_data[sel_var] / 1000
        unit = "km"
    else:
        unit = "回"

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=match_data['Matchday'], y=match_data[sel_var], mode='lines+markers', 
                             name=sel_team, line=dict(color=team_colors.get(sel_team, '#000'))))
    fig.update_layout(xaxis_title='節', yaxis_title=f"{sel_var} ({unit})", hovermode="x unified", xaxis=dict(dtick=1))
    st.plotly_chart(fig, use_container_width=True)

# --- 4. メインロジック ---
st.sidebar.subheader("menu")
selected = st.sidebar.selectbox(' ', ['HOME', 'J1', 'J2', 'J3'])

if selected == 'HOME':
    st.title('🇯🇵 J.League Physical Dashboard')
    all_data = pd.concat([get_data(lk) for lk in LEAGUE_FILE_MAP.keys()], ignore_index=True)
    if not all_data.empty:
        # HOMEの散布図：1試合平均のチーム合計値で比較
        team_summary = all_data.groupby(['Team', 'League', 'Match ID'])[physical_vars].sum().reset_index()
        team_avg = team_summary.groupby(['Team', 'League'])[physical_vars].mean().reset_index()
        
        # 単位変換(km)
        for col in physical_vars:
            if 'Distance' in col: team_avg[col] = team_avg[col] / 1000

        c1, c2 = st.columns(2)
        x_v = c1.selectbox('X軸', physical_vars, index=0)
        y_v = c2.selectbox('Y軸', physical_vars, index=3)
        
        fig = px.scatter(team_avg, x=x_v, y=y_v, color='League', color_discrete_map=LEAGUE_COLOR_MAP, 
                         hover_data=['Team'], title="チーム別1試合平均スタッツ比較", height=600)
        st.plotly_chart(fig, use_container_width=True)
else:
    df_league = get_data(selected)
    if not df_league.empty:
        render_league_dashboard(df_league, selected, TEAM_COLORS)
