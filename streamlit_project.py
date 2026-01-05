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

# --- 2. データロード ---
@st.cache_data
def get_data(league_key):
    try:
        df = pd.read_csv(f"data/{LEAGUE_FILE_MAP[league_key]}")
        df['League'] = league_key
        return df
    except:
        return pd.DataFrame()

# --- 3. 集計ロジック (再徹底修正) ---

def get_ranked_df(df, method, target_var):
    """
    Match IDを使い、確実に『チーム合計』からMIN/MAXを出す
    """
    # 1. まず、チーム×試合ごとに合計値を出す (ここで選手個人データは完全に消える)
    # Match ID が存在することを前提に、全選手の数値を足し合わせる
    match_data = df.groupby(['Team', 'Match ID'])[target_var].sum().reset_index()
    
    # 2. 0の除外 (Sprint系でデータがない試合を消す)
    match_data = match_data[match_data[target_var] > 0]
    
    if match_data.empty:
        return pd.DataFrame()

    # 3. 集計方法の適用
    if method == 'Total':
        res = match_data.groupby('Team')[target_var].sum().reset_index()
    elif method == 'Average':
        res = match_data.groupby('Team')[target_var].mean().reset_index()
    elif method == 'Max':
        res = match_data.groupby('Team')[target_var].max().reset_index()
    elif method == 'Min':
        res = match_data.groupby('Team')[target_var].min().reset_index()
    
    return res

# --- 4. 描画 ---

def render_league_dashboard(df, league_name):
    st.header(f"🏆 {league_name} 分析")
    
    # 指標と集計方法の選択
    col1, col2 = st.columns(2)
    method = col1.selectbox('集計方法', ['Total', 'Average', 'Max', 'Min'], key=f"m_{league_name}")
    var = col2.selectbox('指標', available_vars, key=f"v_{league_name}")

    # ランキングデータの取得
    rank_df = get_ranked_df(df, method, var)

    if not rank_df.empty:
        # Distanceの時はkm表示に調整（Total時のみkm、それ以外は生のmでも良いがkmの方が見やすい）
        display_var = var
        if 'Distance' in var:
            rank_df[var] = rank_df[var] / 1000
            display_var = f"{var} (km)"

        # ソート順: Minなら小さい順、それ以外は大きい順
        ascending = True if method == 'Min' else False
        rank_df = rank_df.sort_values(by=var, ascending=ascending).reset_index(drop=True)

        # グラフ描画
        chart = alt.Chart(rank_df).mark_bar().encode(
            y=alt.Y('Team:N', sort='x' if ascending else '-x', title='チーム'),
            x=alt.X(f'{var}:Q', title=f'{method} {display_var}'),
            color=alt.Color('Team:N', scale=alt.Scale(domain=list(TEAM_COLORS.keys()), range=list(TEAM_COLORS.values())), legend=None),
            tooltip=['Team', alt.Tooltip(var, format='.2f')]
        ).properties(height=600)
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("表示できるデータがありません（Sprintが全試合0の可能性があります）")

# --- 5. メイン ---
selected = st.sidebar.selectbox('menu', ['HOME', 'J1', 'J2', 'J3'])
df = pd.concat([get_data(k) for k in LEAGUE_FILE_MAP.keys()]) if selected == 'HOME' else get_data(selected)

if selected == 'HOME':
    st.title('J.League Physical Dashboard')
    st.write("左メニューから各リーグを選択してください。")
else:
    render_league_dashboard(df, selected)
