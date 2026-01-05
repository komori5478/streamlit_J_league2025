import pandas as pd
import streamlit as st
import altair as alt

# --- 1. 基本設定 ---
st.set_page_config(layout="wide", page_title="J.League Physical Dashboard")

LEAGUE_FILE_MAP = {
    'J1': '2025_J1_physical_data.csv', 
    'J2': '2025_J2_physical_data.csv', 
    'J3': '2025_J3_physical_data.csv'
}

# チームカラー（分析時に色が固定されるよう設定）
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

available_vars = [
    'Distance','Running Distance','HSR Distance','Sprint Count','HI Distance','HI Count',
    'Distance TIP','Running Distance TIP','HSR Distance TIP','HSR Count TIP',
    'Sprint Distance TIP','Sprint Count TIP','Distance OTIP','Running Distance OTIP',
    'HSR Distance OTIP','HSR Count OTIP','Sprint Distance OTIP','Sprint Count OTIP'
]

# --- 2. データの読み込みと集計ロジック ---

@st.cache_data
def get_league_data(league_key):
    try:
        # 生データをロード
        raw_df = pd.read_csv(f"data/{LEAGUE_FILE_MAP[league_key]}")
        
        # 指示通り: 「まず1試合の選手が出した数値を合計する。＝チームの数値」
        # これにより全38試合分（または消化試合分）のチーム合計行が生成されます
        team_match_df = raw_df.groupby(['Team', 'Match ID'])[available_vars].sum().reset_index()
        
        return team_match_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- 3. メインUI ---

st.sidebar.title("Physical Dashboard")
selected_league = st.sidebar.selectbox('League Select', ['J1', 'J2', 'J3'])

# 1試合合計ベースのデータを取得 (ここで各チーム約38行のデータになっている)
df_match_totals = get_league_data(selected_league)

if not df_match_totals.empty:
    st.title(f"🏆 {selected_league} Ranking")
    
    col1, col2 = st.columns(2)
    with col1:
        method = st.selectbox('Aggregation', ['Max', 'Min', 'Average', 'Total'])
    with col2:
        target_var = st.selectbox('Metric', available_vars)

    # --- 4. MAX/MINの選出 ---

    # Sprint等の0除外 (計測エラー試合の排除)
    working_df = df_match_totals[df_match_totals[target_var] > 0].copy()

    # 指示通り: 「38個出して、その中からMAX/MINを出す」
    if method == 'Max':
        final_stats = working_df.groupby('Team')[target_var].max().reset_index()
    elif method == 'Min':
        final_stats = working_df.groupby('Team')[target_var].min().reset_index()
    elif method == 'Average':
        final_stats = working_df.groupby('Team')[target_var].mean().reset_index()
    else: # Total
        final_stats = working_df.groupby('Team')[target_var].sum().reset_index()

    # 表示単位の調整 (Distance系はkmに)
    display_name = target_var
    if 'Distance' in target_var:
        final_stats[target_var] = final_stats[target_var] / 1000
        display_name = f"{target_var} (km)"

    # ソート設定
    is_ascending = (method == 'Min')
    final_stats = final_stats.sort_values(by=target_var, ascending=is_ascending)

    # --- 5. グラフの描画 ---
    
    # カラーマップの生成
    color_scale = alt.Scale(domain=list(TEAM_COLORS.keys()), range=list(TEAM_COLORS.values()))

    chart = alt.Chart(final_stats).mark_bar().encode(
        y=alt.Y('Team:N', sort='x' if is_ascending else '-x', title='Team'),
        x=alt.X(f'{target_var}:Q', title=f'{method} of {display_name}'),
        color=alt.Color('Team:N', scale=color_scale, legend=None),
        tooltip=['Team', alt.Tooltip(target_var, format='.2f')]
    ).properties(height=600, title=f"{selected_league} Team {method} Ranking")

    st.altair_chart(chart, use_container_width=True)

    # 実際に38試合分あるかの確認用（デバッグ表示）
    with st.expander("Show Calculation Logic Detail"):
        st.write("1. Each row below represents the SUM of all players in a single match (Team Value).")
        st.write(f"2. Your selected {method} is picked from these values for each team.")
        st.dataframe(df_match_totals)

else:
    st.error("Data could not be loaded. Please check your CSV files.")
