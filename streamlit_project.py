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
import os
import re

# --- 0. グローバル設定 ---
st.set_page_config(layout="wide", page_title="J.League Physical Dashboard")
st.subheader('All data by SkillCorner')

# --- Excel出力用の関数 ---
def to_excel(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ranking Data')
    return output.getvalue()

# --- 1. データと変数定義 (動的スキャン) ---

def get_available_data():
    """dataフォルダ内のファイルから年度とリーグを自動抽出する"""
    path = "data/"
    data_map = {} # { '2026': {'J1': 'filename', ...}, '2025': {...} }
    
    if not os.path.exists(path):
        os.makedirs(path)
        return data_map

    files = os.listdir(path)
    # ファイル名形式: YYYY_JX_physical_data.csv を想定
    pattern = re.compile(r"(\d{4})_(J[1-3])_physical_data\.csv")
    
    for f in files:
        match = pattern.match(f)
        if match:
            year, league = match.groups()
            if year not in data_map:
                data_map[year] = {}
            data_map[year][league] = f
            
    return data_map

DATA_MAP = get_available_data()
AVAILABLE_YEARS = sorted(DATA_MAP.keys(), reverse=True)

# リーグごとの指定色
LEAGUE_COLOR_MAP = {
    'J1': '#E6002D', # 赤
    'J2': '#127A3A', # 緑
    'J3': '#014099', # 青
}

# 📌 チームカラー定義
TEAM_COLORS = {
    # J1, J2, J3 のチームカラー (既存の定義をそのまま保持)
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

available_vars = ['Distance','Running Distance','M/min','HSR Distance','Sprint Count','HI Distance','HI Count',
                  'Distance TIP','Running Distance TIP','HSR Distance TIP','HSR Count TIP',
                  'Sprint Distance TIP','Sprint Count TIP','Distance OTIP','Running Distance OTIP','HSR Distance OTIP','HSR Count OTIP',
                  'Sprint Distance OTIP','Sprint Count OTIP']
RANKING_METHODS = ['Total', 'Average', 'Max', 'Min']

# --- 2. データロード関数 ---

@st.cache_data(ttl=60*15)
def get_data(year, league_key):
    file_name = DATA_MAP.get(year, {}).get(league_key)
    if not file_name:
        return pd.DataFrame()
    
    file_path = f"data/{file_name}"
    try:
        with st.spinner(f'{year} {league_key}データをロード中...'):
            df = pd.read_csv(file_path)
            df['League'] = league_key
            df['Season'] = year

            # 時系列処理
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
        st.error(f"エラー: {file_name} の読み込みに失敗しました。")
        return pd.DataFrame()

@st.cache_data(ttl=60*15)
def get_all_league_data(year):
    all_dfs = []
    if year in DATA_MAP:
        for league_key in DATA_MAP[year].keys():
            df = get_data(year, league_key)
            if not df.empty:
                all_dfs.append(df)
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

# --- 3. 描画ロジック (既存の関数群) ---
# render_custom_ranking, render_scatter_plot, render_trend_analysis は元のコードと同一のため省略、
# 必要に応じて適宜ここに配置してください。

# (中略: render_custom_ranking などの関数をここに再配置)
# ※ 以前提供された関数をそのまま利用可能です。

# --- 4. メインUI ---

with st.sidebar:
    st.subheader("Filter Settings")
    
    # 1. 年度選択
    if AVAILABLE_YEARS:
        selected_year = st.selectbox('対象シーズン', AVAILABLE_YEARS, key='year_selector')
    else:
        st.error("dataフォルダに適切なCSVファイルが見つかりません。")
        st.stop()
        
    # 2. リーグ選択
    selected_league = st.selectbox('リーグ選択',['HOME','J1','J2','J3'], key='league_selector')

# データの取得
if selected_league == 'HOME':
    df = get_all_league_data(selected_year)
else:
    df = get_data(selected_year, selected_league)

# コンテンツ表示
if df.empty:
    st.warning(f"⚠️ {selected_year}年 {selected_league} のデータが存在しないか、読み込めませんでした。")
else:
    if selected_league == 'HOME':
        st.title(f'🇯🇵 J.League Dashboard: {selected_year} 全体分析')
        # 散布図とプレビューの表示
        tab1, tab2 = st.tabs(['散布図分析', 'データプレビュー'])
        with tab1:
            # 既存の render_scatter_plot を呼び出し
            # render_scatter_plot(df, available_vars, TEAM_COLORS, LEAGUE_COLOR_MAP)
            pass 
    else:
        st.header(f"🏆 {selected_year} {selected_league} 分析ダッシュボード")
        # タブの描画など、元のロジックをここに継続
