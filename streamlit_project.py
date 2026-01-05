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
st.subheader('All data by SkillCorner')

# --- Excel出力用の関数 ---
def to_excel(df: pd.DataFrame):
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

LEAGUE_COLOR_MAP = {'J1': '#E6002D', 'J2': '#127A3A', 'J3': '#014099'}

TEAM_COLORS = {
    'Kashima Antlers': '#B71940','Kashiwa Reysol':"#FFF000",'Urawa Red Diamonds': '#E6002D',
    'FC Tokyo': "#3E4C8D",'Tokyo Verdy':"#006931",'FC Machida Zelvia':"#0056A5",
    'Kawasaki Frontale': "#319FDA",'Yokohama F. Marinos': "#014099",'Yokohama FC':"#4BC1FE",'Shonan Bellmare':"#9EFF26",
    'Albirex Niigata':"#FE641E",'Shimizu S-Pulse':"#FF8901",'Nagoya Grampus': "#F8B500",
    'Kyoto Sanga FC':"#820064",'Gamba Osaka': "#00458D",'Cerezo Osaka': "#DB005B",'Vissel Kobe': '#A60129',
    'Fagiano Okayama':"#A72041",'Sanfrecce Hiroshima':"#603D97",'Avispa Fukuoka':"#9EB5C7",
    'Hokkaido Consadole Sapporo':"#125D75",'Vegalta Sendai':"#FFC20E",'AFC Blaublitz Akita':"#0D5790",'Montedio Yamagata':"#F7F4A6",'Iwaki SC':"#C01630",
    'Mito Hollyhock':"#2E3192",'Omiya Ardija':"#EC6601",'JEF United Ichihara Chiba':"#FFDE00",'Ventforet Kofu':"#0F63A3",
    'Kataller Toyama':"#25458F",'Jubilo Iwata':"#7294BA",'Fujieda MYFC':"#875884",'Renofa Yamaguchi':"#F26321",'Tokushima Vortis':"#11233F",'Ehime FC':"#ED9A4C",'FC Imabari':"#908E3C",
    'Sagan Tosu':"#30B7D7",'V-Varen Nagasaki':"#013893",'Roasso Kumamoto':"#A92D27",'Oita Trinita':"#254398",
    'Vanraure Hachinohe':"#13A63B",'Fukushima United FC':"#CF230C",'Tochigi SC':"#0170A4",'Tochigi City':"#001030",'ThespaKusatsu Gunma':"#08406F",'SC Sagamihara':"#408B52",
    'AC Parceiro Nagano':"#E36A2A",'Matsumoto Yamaga FC':"#004B1D",'Ishikawa FC Zweigen Kanazawa':"#3B1216",'FC Azul Claro Numazu':"#13A7DE",'FC Gifu':"#126246",
    'FC Osaka':"#90C9E2",'Nara Club':"#011D64",'Gainare Tottori':"#96C692",'Kamatamare Sanuki':"#669FB9",'Kochi United SC':"#B21E23",
    'Giravanz Kitakyushu':"#E8BD00",'Tegevajaro Miyazaki FC':"#F6E066",'Kagoshima United FC':"#19315F",'FC Ryūkyū':"#AA131B",
}

available_vars = ['Distance','Running Distance','HSR Distance','Sprint Count','HI Distance','HI Count',
                  'Distance TIP','Running Distance TIP','HSR Distance TIP','HSR Count TIP',
                  'Sprint Distance TIP','Sprint Count TIP','Distance OTIP','Running Distance OTIP','HSR Distance OTIP','HSR Count OTIP',
                  'Sprint Distance OTIP','Sprint Count OTIP']
RANKING_METHODS = ['Total', 'Average', 'Max', 'Min']

# --- 2. データロード ---
@st.cache_data(ttl=60*15)
def get_data(league_key):
    file_name = LEAGUE_FILE_MAP.get(league_key)
    file_path = f"data/{file_name}"
    try:
        df = pd.read_csv(file_path)
        df['League'] = league_key
        if 'Match ID' in df.columns:
            # 節(Matchday)の算出を確実に行う
            df = df.sort_values(['Team', 'Match ID'])
            match_counts = df.groupby('Team')['Match ID'].unique().apply(list).reset_index()
            # Match IDごとの順序を保持してMatchdayを割り振る
            df['Matchday'] = df.groupby('Team')['Match ID'].transform(lambda x: pd.factorize(x)[0] + 1)
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60*15)
def get_all_league_data():
    all_dfs = [get_data(lk) for lk in LEAGUE_FILE_MAP.keys()]
    return pd.concat([d for d in all_dfs if not d.empty], ignore_index=True)

# --- 3. 集計ロジック (徹底修正) ---

def apply_aggregation(df, method, target_var):
    """
    1. チーム単位の1試合合計データセットを作成
    2. 異常値(0)を除外
    3. その合計データセットに対して Min/Max/Avg を適用
    """
    # ステップ1: 各試合・各チームの「合計値」を算出
    # (ここを通ることで選手個人の数値は消え、110kmや200回といったチーム単位の数値のみになる)
    match_level_totals = df.groupby(['Team', 'Match ID'])[available_vars].sum().reset_index()

    # ステップ2: Sprintなどで0の試合（計測エラー等）を除外
    if 'Sprint' in target_var or 'HI' in target_var:
        match_level_totals = match_level_totals[match_level_totals[target_var] > 0]

    # ステップ3: 手法に応じて「チームごとの」統計量を算出
    if method == 'Total':
        return match_level_totals.groupby('Team')[available_vars].sum().reset_index()
    elif method == 'Average':
        return match_level_totals.groupby('Team')[available_vars].mean().reset_index()
    elif method == 'Max':
        return match_level_totals.groupby('Team')[available_vars].max().reset_index()
    elif method == 'Min':
        return match_level_totals.groupby('Team')[available_vars].min().reset_index()
    
    return pd.DataFrame()

# --- 4. 描画コンポーネント ---

def render_custom_ranking(df, league_name, team_colors, available_vars):
    st.markdown("### 🏆 カスタムランキング作成")
    team = st.selectbox('注目チームを選択', df['Team'].unique(), key=f"focal_{league_name}")
    focal_color = team_colors.get(team, '#000000')

    col1, col2 = st.columns(2)
    method = col1.selectbox('集計方法', RANKING_METHODS, key=f"meth_{league_name}")
    var = col2.selectbox('評価指標', available_vars, key=f"var_{league_name}")

    rank_df = apply_aggregation(df, method, var)
    if rank_df.empty:
        st.warning("表示できるデータがありません。")
        return

    sort_asc = (method == 'Min')
    plot_df = rank_df.sort_values(by=[var], ascending=sort_asc).reset_index(drop=True)
    plot_df = plot_df[::-1]

    sns.set(rc={'axes.facecolor':'#fbf9f4', 'figure.facecolor':'#fbf9f4'})
    fig, ax = plt.subplots(figsize=(7, 8), dpi=200)
    nrows = plot_df.shape[0]
    ax.set_xlim(0, 3.5); ax.set_ylim(0, nrows + 1.5)
    
    for i in range(nrows):
        t_name = plot_df['Team'].iloc[i]
        is_f = (t_name == team)
        c = focal_color if is_f else '#4A2E19'
        val = plot_df[var].iloc[i]
        
        # 単位変換表示
        if 'Distance' in var:
            txt = f"{round(val/1000, 2)} km"
        else:
            txt = f"{round(val,1)}"
            
        ax.annotate(f"{nrows-i}  {t_name}", xy=(0.1, i + .5), va='center', color=c, weight='bold' if is_f else 'regular')
        ax.annotate(txt, xy=(2.5, i + .5), va='center', color=c, weight='bold' if is_f else 'regular')

    ax.set_axis_off()
    st.pyplot(fig)

def render_league_dashboard(df, league_name, team_colors, available_vars):
    st.header(f"🏆 {league_name} リーグ分析ダッシュボード")
    cur_teams = df['Team'].unique().tolist()
    filt_colors = {t: team_colors[t] for t in cur_teams if t in team_colors}
    
    tabs = st.tabs(['集計ランキング', 'カスタムランキング', 'シーズン動向分析'])
    
    with tabs[0]:
        c1, c2 = st.columns(2)
        method = c1.selectbox('集計方法', RANKING_METHODS, key=f'am_{league_name}')
        opts = [v.replace('Distance', 'Distance (km)') if 'Distance' in v and method == 'Total' else v for v in available_vars]
        sel_v = c2.selectbox('指標', opts, key=f'av_{league_name}')
        actual_v = sel_v.replace(' (km)', '')

        stats = apply_aggregation(df, method, actual_v)
        if stats.empty:
            st.warning("データがありません。")
        else:
            stats['val'] = stats[actual_v] / 1000 if ' (km)' in sel_v else stats[actual_v]
            sort_asc = (method == 'Min')
            
            chart = alt.Chart(stats).mark_bar().encode(
                y=alt.Y('Team:N', sort='x' if sort_asc else '-x', title='チーム'),
                x=alt.X('val:Q', title=f'{method} {sel_v}'),
                color=alt.Color('Team:N', scale=alt.Scale(domain=list(filt_colors.keys()), range=list(filt_colors.values()))),
                tooltip=['Team', alt.Tooltip('val', format='.2f')]
            ).properties(height=600)
            st.altair_chart(chart, use_container_width=True)

    with tabs[1]: render_custom_ranking(df, league_name, team_colors, available_vars)
    with tabs[2]: render_trend_analysis(df, league_name, team_colors, available_vars)

def render_scatter_plot(df, vars, colors, l_colors):
    st.markdown("### 📊 J.League 全体分析：散布図")
    # 散布図も1試合あたりの平均(Totalではない)を表示
    match_totals = df.groupby(['Team', 'League', 'Match ID'])[vars].sum().reset_index()
    team_avg = match_totals.groupby(['Team', 'League'])[vars].mean().reset_index()
    c1, c2 = st.columns(2)
    fig = px.scatter(team_avg, x=c1.selectbox('X軸', vars, index=1), y=c2.selectbox('Y軸', vars, index=2), color='League', color_discrete_map=l_colors, hover_data=['Team'], height=600)
    st.plotly_chart(fig, use_container_width=True)

def render_trend_analysis(df, league_name, team_colors, available_vars):
    st.markdown(f"### 📈 シーズン動向分析 ({league_name})")
    all_teams = sorted(df['Team'].unique().tolist())
    c1, c2 = st.columns(2)
    sel_t = c1.selectbox('チーム', all_teams, key=f'tt_{league_name}')
    sel_v = c2.selectbox('項目', available_vars, key=f'tv_{league_name}')
    # 1試合合計値の推移
    team_data = df[df['Team'] == sel_t].groupby(['Matchday', 'Match ID'])[sel_v].sum().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=team_data['Matchday'], y=team_data[sel_v], mode='lines+markers', name='チーム合計', line=dict(color=team_colors.get(sel_t, '#000'))))
    fig.update_layout(xaxis_title='節', yaxis_title='値', hovermode="x unified", height=500)
    st.plotly_chart(fig, use_container_width=True)

# --- 5. メインロジック ---
with st.sidebar:
    selected = st.selectbox('menu', ['HOME', 'J1', 'J2', 'J3'])

df = get_all_league_data() if selected == 'HOME' else get_data(selected)

if selected == 'HOME':
    st.title('🇯🇵 J.League Physical Dashboard')
    if not df.empty:
        t1, t2 = st.tabs(['全体散布図', 'プレビュー'])
        with t1: render_scatter_plot(df, available_vars, TEAM_COLORS, LEAGUE_COLOR_MAP)
        with t2: st.dataframe(df.head())
elif selected in ['J1', 'J2', 'J3']:
    render_league_dashboard(df, selected, TEAM_COLORS, available_vars)
