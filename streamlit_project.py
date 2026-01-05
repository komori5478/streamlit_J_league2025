import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

# --- 0. 設定 ---
st.set_page_config(layout="wide", page_title="J.League Physical Dashboard")
st.subheader('All data by SkillCorner')

# --- 1. 定数 ---
LEAGUE_FILE_MAP = {'J1': '2025_J1_physical_data.csv', 'J2': '2025_J2_physical_data.csv', 'J3': '2025_J3_physical_data.csv'}
LEAGUE_COLOR_MAP = {'J1': '#E6002D', 'J2': '#127A3A', 'J3': '#014099'}

# チームカラー（省略なし）
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
    file_path = f"data/{LEAGUE_FILE_MAP.get(league_key)}"
    try:
        df = pd.read_csv(file_path)
        df['League'] = league_key
        # 節(Matchday)の割り当て
        if 'Match ID' in df.columns:
            unique_matches = df[['Team', 'Match ID']].drop_duplicates().sort_values(['Team', 'Match ID'])
            unique_matches['Matchday'] = unique_matches.groupby('Team').cumcount() + 1
            df = pd.merge(df, unique_matches, on=['Team', 'Match ID'], how='left')
        return df
    except:
        return pd.DataFrame()

# --- 3. 集計ロジック (コア部分：徹底修正) ---

def apply_aggregation(df, method, target_var):
    """
    1. 選手単位のデータを、試合単位の合計(Sum)に圧縮する
    2. 合計が0の試合を排除する
    3. その『1試合合計値のリスト』から Min/Max/Avg を選ぶ
    """
    # ステップ1: 各試合・各チームの【合計値】を算出
    # ここで選手個人の行（10kmなど）が消え、チームの行（115kmなど）になる
    match_sums = df.groupby(['Team', 'Match ID'])[target_var].sum().reset_index()

    # ステップ2: 異常値(0)の除外
    # SprintCountが0の試合などはランキングから外す
    match_sums = match_sums[match_sums[target_var] > 0]

    if match_sums.empty:
        return pd.DataFrame(columns=['Team', target_var])

    # ステップ3: チームごとに統計処理
    if method == 'Total':
        res = match_sums.groupby('Team')[target_var].sum().reset_index()
    elif method == 'Average':
        res = match_sums.groupby('Team')[target_var].mean().reset_index()
    elif method == 'Max':
        res = match_sums.groupby('Team')[target_var].max().reset_index()
    elif method == 'Min':
        res = match_sums.groupby('Team')[target_var].min().reset_index()
    
    return res

# --- 4. 描画コンポーネント ---

def render_custom_ranking(df, league_name, team_colors, available_vars):
    st.markdown("### 🏆 カスタムランキング")
    team = st.selectbox('注目チーム', df['Team'].unique(), key=f"f_{league_name}")
    col1, col2 = st.columns(2)
    method = col1.selectbox('集計方法', RANKING_METHODS, key=f"m_{league_name}")
    var = col2.selectbox('指標', available_vars, key=f"v_{league_name}")

    rank_df = apply_aggregation(df, method, var)
    if rank_df.empty:
        st.warning("データがありません")
        return

    sort_asc = (method == 'Min')
    plot_df = rank_df.sort_values(by=var, ascending=sort_asc).reset_index(drop=True)
    plot_df = plot_df[::-1] # 上から順位順にするため

    sns.set(rc={'axes.facecolor':'#fbf9f4', 'figure.facecolor':'#fbf9f4'})
    fig, ax = plt.subplots(figsize=(7, 8), dpi=200)
    
    for i in range(len(plot_df)):
        t_name = plot_df['Team'].iloc[i]
        val = plot_df[var].iloc[i]
        is_focal = (t_name == team)
        color = team_colors.get(t_name, '#4A2E19') if is_focal else '#4A2E19'
        
        # 単位変換
        label = f"{round(val/1000, 2)} km" if 'Distance' in var else f"{round(val, 1)}"
        rank_num = len(plot_df) - i
        
        ax.annotate(f"{rank_num}  {t_name}", xy=(0.1, i + .5), va='center', color=color, weight='bold' if is_focal else 'regular')
        ax.annotate(label, xy=(2.5, i + .5), va='center', color=color, weight='bold' if is_focal else 'regular')

    ax.set_xlim(0, 3.5); ax.set_ylim(0, len(plot_df) + 1); ax.set_axis_off()
    st.pyplot(fig)

def render_league_dashboard(df, league_name, team_colors, available_vars):
    st.header(f"🏆 {league_name} 分析")
    tabs = st.tabs(['集計ランキング', 'カスタムランキング', '動向分析'])
    
    with tabs[0]:
        c1, c2 = st.columns(2)
        method = c1.selectbox('集計', RANKING_METHODS, key=f'am_{league_name}')
        var = c2.selectbox('指標', available_vars, key=f'av_{league_name}')
        
        stats = apply_aggregation(df, method, var)
        if not stats.empty:
            stats['val'] = stats[var] / 1000 if 'Distance' in var and method == 'Total' else stats[var]
            sort_asc = (method == 'Min')
            chart = alt.Chart(stats).mark_bar().encode(
                y=alt.Y('Team:N', sort='x' if sort_asc else '-x'),
                x=alt.X('val:Q', title=f'{method} {var}'),
                color=alt.Color('Team:N', scale=alt.Scale(domain=list(team_colors.keys()), range=list(team_colors.values())), legend=None),
                tooltip=['Team', 'val']
            ).properties(height=600)
            st.altair_chart(chart, use_container_width=True)

    with tabs[1]: render_custom_ranking(df, league_name, team_colors, available_vars)
    with tabs[2]: 
        t_sel = st.selectbox('チーム', sorted(df['Team'].unique()), key=f'tr_t_{league_name}')
        v_sel = st.selectbox('項目', available_vars, key=f'tr_v_{league_name}')
        # トレンドも必ず「合計」で出す
        trend_data = df[df['Team'] == t_sel].groupby(['Matchday', 'Match ID'])[v_sel].sum().reset_index()
        fig = px.line(trend_data, x='Matchday', y=v_sel, markers=True, title=f"{t_sel} の推移")
        st.plotly_chart(fig, use_container_width=True)

# --- 5. メイン ---
selected = st.sidebar.selectbox('menu', ['HOME', 'J1', 'J2', 'J3'])
df = pd.concat([get_data(k) for k in LEAGUE_FILE_MAP.keys()]) if selected == 'HOME' else get_data(selected)

if selected == 'HOME':
    st.title('J.League Dashboard')
    if not df.empty:
        # 散布図も1試合あたりのチーム平均をベースにする
        match_totals = df.groupby(['Team', 'League', 'Match ID'])[available_vars].sum().reset_index()
        team_avg = match_totals.groupby(['Team', 'League'])[available_vars].mean().reset_index()
        v1 = st.selectbox('X', available_vars, index=0)
        v2 = st.selectbox('Y', available_vars, index=3)
        st.plotly_chart(px.scatter(team_avg, x=v1, y=v2, color='League', hover_data=['Team'], color_discrete_map=LEAGUE_COLOR_MAP), use_container_width=True)
else:
    render_league_dashboard(df, selected, TEAM_COLORS, available_vars)
