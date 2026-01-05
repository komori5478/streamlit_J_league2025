import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import altair as alt
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

# --- 0. グローバル設定 ---
st.set_page_config(layout="wide", page_title="J.League Physical Dashboard")
st.subheader('All data by SkillCorner')

# --- Excel出力用の関数 ---
def to_excel(df: pd.DataFrame):
    """データフレームをExcelバイトストリームに変換する"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ranking Data')
    processed_data = output.getvalue()
    return processed_data

# --- 1. データと変数定義 ---
LEAGUE_FILE_MAP = {
    'J1': '2025_J1_physical_data.csv',
    'J2': '2025_J2_physical_data.csv',
    'J3': '2025_J3_physical_data.csv',
}

LEAGUE_COLOR_MAP = {
    'J1': '#E6002D', # 赤
    'J2': '#127A3A', # 緑
    'J3': '#014099', # 青
}

TEAM_COLORS = {
    # J1 Teams
    'Kashima Antlers': '#B71940','Kashiwa Reysol':"#FFF000",'Urawa Red Diamonds': '#E6002D',
    'FC Tokyo': "#3E4C8D",'Tokyo Verdy':"#006931",'FC Machida Zelvia':"#0056A5",
    'Kawasaki Frontale': "#319FDA",'Yokohama F. Marinos': "#014099",'Yokohama FC':"#4BC1FE",'Shonan Bellmare':"#9EFF26",
    'Albirex Niigata':"#FE641E",'Shimizu S-Pulse':"#FF8901",'Nagoya Grampus': "#F8B500",
    'Kyoto Sanga FC':"#820064",'Gamba Osaka': "#00458D",'Cerezo Osaka': "#DB005B",'Vissel Kobe': '#A60129',
    'Fagiano Okayama':"#A72041",'Sanfrecce Hiroshima':"#603D97",'Avispa Fukuoka':"#9EB5C7",
    # J2 Teams
    'Hokkaido Consadole Sapporo':"#125D75",'Vegalta Sendai':"#FFC20E",'AFC Blaublitz Akita':"#0D5790",'Montedio Yamagata':"#F7F4A6",'Iwaki SC':"#C01630",
    'Mito Hollyhock':"#2E3192",'Omiya Ardija':"#EC6601",'JEF United Ichihara Chiba':"#FFDE00",'Ventforet Kofu':"#0F63A3",
    'Kataller Toyama':"#25458F",'Jubilo Iwata':"#7294BA",'Fujieda MYFC':"#875884",'Renofa Yamaguchi':"#F26321",'Tokushima Vortis':"#11233F",'Ehime FC':"#ED9A4C",'FC Imabari':"#908E3C",
    'Sagan Tosu':"#30B7D7",'V-Varen Nagasaki':"#013893",'Roasso Kumamoto':"#A92D27",'Oita Trinita':"#254398",
    # J3 Teams
    'Vanraure Hachinohe':"#13A63B",'Fukushima United FC':"#CF230C",
    'Tochigi SC':"#0170A4",'Tochigi City':"#001030",'ThespaKusatsu Gunma':"#08406F",'SC Sagamihara':"#408B52",
    'AC Parceiro Nagano':"#E36A2A",'Matsumoto Yamaga FC':"#004B1D",'Ishikawa FC Zweigen Kanazawa':"#3B1216",'FC Azul Claro Numazu':"#13A7DE",'FC Gifu':"#126246",
    'FC Osaka':"#90C9E2",'Nara Club':"#011D64",'Gainare Tottori':"#96C692",'Kamatamare Sanuki':"#669FB9",'Kochi United SC':"#B21E23",
    'Giravanz Kitakyushu':"#E8BD00",'Tegevajaro Miyazaki FC':"#F6E066",'Kagoshima United FC':"#19315F",'FC Ryūkyū':"#AA131B",
}

available_vars = ['Distance','Running Distance','HSR Distance','Sprint Count','HI Distance','HI Count',
                  'Distance TIP','Running Distance TIP','HSR Distance TIP','HSR Count TIP',
                  'Sprint Distance TIP','Sprint Count TIP','Distance OTIP','Running Distance OTIP','HSR Distance OTIP','HSR Count OTIP',
                  'Sprint Distance OTIP','Sprint Count OTIP']
RANKING_METHODS = ['Total', 'Average', 'Max', 'Min']

# --- 2. データロード関数 ---
@st.cache_data(ttl=60*15)
def get_data(league_key):
    file_name = LEAGUE_FILE_MAP.get(league_key)
    file_path = f"data/{file_name}"
    try:
        with st.spinner(f'{league_key}データをロード中...'):
            df = pd.read_csv(file_path)
            df['League'] = league_key

            if 'Match Date' in df.columns and 'Match ID' in df.columns:
                df['Match Date'] = pd.to_datetime(df['Match Date'], errors='coerce')
                unique_matches = df[['Team', 'Match ID', 'Match Date']].drop_duplicates()
                unique_matches = unique_matches.sort_values(by=['Team', 'Match Date']).reset_index(drop=True)
                unique_matches['Matchday'] = unique_matches.groupby('Team').cumcount() + 1
                df = pd.merge(df, unique_matches[['Team', 'Match ID', 'Matchday']], on=['Team', 'Match ID'], how='left')
                df = df.dropna(subset=['Matchday'])
                df['Matchday'] = df['Matchday'].astype(int)
            elif 'Matchday' not in df.columns:
                 df['Matchday'] = df.groupby('Team').cumcount() + 1
            return df
    except Exception as e:
        st.error(f"{league_key} データ ({file_name}) のロードに失敗しました。")
        return pd.DataFrame()

@st.cache_data(ttl=60*15)
def get_all_league_data():
    all_dfs = [get_data(lk) for lk in LEAGUE_FILE_MAP.keys()]
    combined_df = pd.concat([d for d in all_dfs if not d.empty], ignore_index=True)
    return combined_df

# --- 3. 描画コンポーネント関数 ---

def render_custom_ranking(df, league_name, team_colors, available_vars):
    st.markdown("### 🏆 カスタムランキング作成")
    team = st.selectbox('注目チームを選択', df['Team'].unique(), key=f"focal_{league_name}")
    focal_color = team_colors.get(team, '#000000')

    col1, col2 = st.columns(2)
    with col1:
        rank_method = st.selectbox('集計方法', RANKING_METHODS, key=f"meth_{league_name}")
    with col2:
        rank_var = st.selectbox('評価指標', available_vars, key=f"var_{league_name}")

    # 集計
    if rank_method == 'Total':
        rank_df = df.groupby('Team')[available_vars].sum().reset_index()
    else:
        # Match ID単位で一度集約してから集計（Min/Max/Avgを正確にするため）
        match_level = df.groupby(['Team', 'Match ID'])[available_vars].mean().reset_index()
        if rank_method == 'Average': rank_df = match_level.groupby('Team')[available_vars].mean().reset_index()
        elif rank_method == 'Max': rank_df = match_level.groupby('Team')[available_vars].max().reset_index()
        elif rank_method == 'Min': rank_df = match_level.groupby('Team')[available_vars].min().reset_index()

    sort_asc = True if rank_method == 'Min' else False
    indexdf_short = rank_df.sort_values(by=[rank_var], ascending=sort_asc)[['Team', rank_var]].reset_index(drop=True)
    indexdf_short = indexdf_short[::-1]

    # Matplotlib描画
    sns.set(rc={'axes.facecolor':'#fbf9f4', 'figure.facecolor':'#fbf9f4'})
    fig, ax = plt.subplots(figsize=(7, 8), dpi=200)
    nrows = indexdf_short.shape[0]
    ax.set_xlim(0, 3.5); ax.set_ylim(0, nrows + 1.5)
    
    for i in range(nrows):
        team_name = indexdf_short['Team'].iloc[i]
        is_focal = team_name == team
        t_color = focal_color if is_focal else '#4A2E19'
        rank = nrows - i
        val = indexdf_short[rank_var].iloc[i]
        display_val = f"{round(val/1000, 2)} km" if rank_var == 'Distance' and rank_method == 'Total' else f"{round(val,2)}"
        
        ax.annotate(f"{rank}  {team_name}", xy=(0.1, i + .5), va='center', color=t_color, weight='bold' if is_focal else 'regular')
        ax.annotate(display_val, xy=(2.5, i + .5), va='center', color=t_color, weight='bold' if is_focal else 'regular')

    ax.set_axis_off()
    st.pyplot(fig)

def render_league_dashboard(df, league_name, team_colors, available_vars):
    st.header(f"🏆 {league_name} リーグ分析ダッシュボード")
    current_teams = df['Team'].unique().tolist()
    filtered_colors = {t: team_colors[t] for t in current_teams if t in team_colors}
    
    tabs = st.tabs(['集計ランキング', 'カスタムランキング', 'シーズン動向分析'])
    
    with tabs[0]: # 集計ランキング
        col_agg, col_var = st.columns(2)
        method = col_agg.selectbox('集計方法', RANKING_METHODS, key=f'agg_m_{league_name}')
        opts = [v.replace('Distance', 'Distance (km)') if v == 'Distance' and method == 'Total' else v for v in available_vars]
        selected_var = col_var.selectbox('指標', opts, key=f'agg_v_{league_name}')
        actual_v = selected_var.replace(' (km)', '')

        # 正確な集計ロジック
        if method == 'Total':
            stats = df.groupby('Team')[available_vars].sum().reset_index()
        else:
            match_stats = df.groupby(['Team', 'Match ID'])[available_vars].mean().reset_index()
            if method == 'Average': stats = match_stats.groupby('Team')[available_vars].mean().reset_index()
            elif method == 'Max': stats = match_stats.groupby('Team')[available_vars].max().reset_index()
            elif method == 'Min': stats = match_stats.groupby('Team')[available_vars].min().reset_index()

        if selected_var == 'Distance (km)':
            stats['val'] = stats[actual_v] / 1000
        else:
            stats['val'] = stats[actual_v]

        sort_asc = (method == 'Min')
        chart = alt.Chart(stats).mark_bar().encode(
            y=alt.Y('Team:N', sort='x' if sort_asc else '-x', title='チーム'),
            x=alt.X('val:Q', title=f'{method} {selected_var}'),
            color=alt.Color('Team:N', scale=alt.Scale(domain=list(filtered_colors.keys()), range=list(filtered_colors.values()))),
            tooltip=['Team', alt.Tooltip('val', format='.2f')]
        ).properties(height=600)
        st.altair_chart(chart, use_container_width=True)

    with tabs[1]: render_custom_ranking(df, league_name, team_colors, available_vars)
    with tabs[2]: render_trend_analysis(df, league_name, team_colors, available_vars)

def render_scatter_plot(df, vars, colors, l_colors):
    st.markdown("### 📊 J.League 全体分析：散布図")
    team_avg = df.groupby(['Team', 'League'])[vars].mean().reset_index()
    c1, c2 = st.columns(2)
    x_v = c1.selectbox('X軸', vars, index=1, key='sx')
    y_v = c2.selectbox('Y軸', vars, index=2, key='sy')
    fig = px.scatter(team_avg, x=x_v, y=y_v, color='League', color_discrete_map=l_colors, hover_data=['Team'], height=600)
    st.plotly_chart(fig, use_container_width=True)

def render_trend_analysis(df, league_name, team_colors, available_vars):
    st.markdown(f"### 📈 シーズン動向分析 ({league_name})")
    all_teams = sorted(df['Team'].unique().tolist())
    c1, c2 = st.columns(2)
    sel_team = c1.selectbox('チーム', all_teams, key=f'tr_t_{league_name}')
    sel_var = c2.selectbox('項目', available_vars, key=f'tr_v_{league_name}')
    show_opp = st.checkbox('対戦相手も表示', key=f'tr_o_{league_name}')

    team_data = df[df['Team'] == sel_team].groupby(['Matchday', 'Match ID'])[sel_var].mean().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=team_data['Matchday'], y=team_data[sel_var], mode='lines+markers', name='自チーム', line=dict(color=team_colors.get(sel_team, '#000'))))
    
    if show_opp:
        opp_data = df[df['Match ID'].isin(team_data['Match ID']) & (df['Team'] != sel_team)].groupby('Matchday')[sel_var].mean().reset_index()
        fig.add_trace(go.Scatter(x=opp_data['Matchday'], y=opp_data[sel_var], mode='lines+markers', name='相手平均', line=dict(dash='dot', color='#ccc')))
    
    fig.update_layout(xaxis_title='節', yaxis_title='値', hovermode="x unified", height=500)
    st.plotly_chart(fig, use_container_width=True)

# --- 4. メインロジック ---
with st.sidebar:
    selected = st.selectbox('menu', ['HOME', 'J1', 'J2', 'J3'])

df = get_all_league_data() if selected == 'HOME' else get_data(selected)

if selected == 'HOME':
    st.title('🇯🇵 J.League Data Dashboard')
    if not df.empty:
        t1, t2 = st.tabs(['全体散布図', 'プレビュー'])
        with t1: render_scatter_plot(df, available_vars, TEAM_COLORS, LEAGUE_COLOR_MAP)
        with t2: st.dataframe(df.head())
elif selected in ['J1', 'J2', 'J3']:
    render_league_dashboard(df, selected, TEAM_COLORS, available_vars)
