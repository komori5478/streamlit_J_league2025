import pandas as pd
import streamlit as st
import altair as alt

# --- 1. 定数・設定 ---
st.set_page_config(layout="wide", page_title="J.League Physical Dashboard")

LEAGUE_FILE_MAP = {
    'J1': '2025_J1_physical_data.csv', 
    'J2': '2025_J2_physical_data.csv', 
    'J3': '2025_J3_physical_data.csv'
}

# 全チームのカラー定義（主要チームのみ抜粋、適宜追加してください）
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

# --- 2. データ読み込みと「チーム合計化」のコアロジック ---

@st.cache_data
def get_processed_team_data(league_key):
    """
    選手単位のデータを即座に捨て、Match IDを基点に『チーム1試合合計』データに変換する
    """
    try:
        # 1. 生データの読み込み
        raw_df = pd.read_csv(f"data/{LEAGUE_FILE_MAP[league_key]}")
        
        # 2. Match ID と Team でグルーピングして『合計』を算出
        # ここを通ることで、データは「チーム名 / Match ID / 各項目の合計値」のみになる
        # つまり「1行 ＝ そのチームの1試合の結果」という形に固定される
        team_match_summary = raw_df.groupby(['Team', 'Match ID'])[available_vars].sum().reset_index()
        
        # 3. リーグ情報を付与
        team_match_summary['League'] = league_key
        return team_match_summary
    except Exception as e:
        st.error(f"データのロードに失敗しました ({league_key}): {e}")
        return pd.DataFrame()

# --- 3. UI表示メインロジック ---

# サイドバーメニュー
st.sidebar.title("MENU")
selected_league = st.sidebar.selectbox('League Select', ['J1', 'J2', 'J3'])

# データの取得（ここで既に1試合合計データになっている）
df_summary = get_processed_team_data(selected_league)

if not df_summary.empty:
    st.title(f"🏆 {selected_league} Physical Analysis")
    st.subheader('Analysis based on Team-Match Totals (Match ID used as anchor)')
    
    # 指標と集計方法の選択
    col1, col2 = st.columns(2)
    with col1:
        method = st.selectbox('Aggregation Method', ['Max', 'Min', 'Average', 'Total'])
    with col2:
        target_var = st.selectbox('Variable', available_vars)

    # --- 4. ランキングの計算 ---

    # Sprint等の0除外処理（0の試合は未計測・エラーとして除外）
    # 既に1試合合計なので、合計が0の試合を無視する
    working_df = df_summary[df_summary[target_var] > 0].copy()

    if working_df.empty:
        st.warning(f"No valid data found for {target_var} (All values are 0).")
    else:
        # 指定された手法でチームごとに最終集計
        if method == 'Max':
            final_stats = working_df.groupby('Team')[target_var].max().reset_index()
        elif method == 'Min':
            final_stats = working_df.groupby('Team')[target_var].min().reset_index()
        elif method == 'Average':
            final_stats = working_df.groupby('Team')[target_var].mean().reset_index()
        else: # Total
            final_stats = working_df.groupby('Team')[target_var].sum().reset_index()

        # Distance項目の単位調整 (m -> km)
        plot_var = target_var
        if 'Distance' in target_var:
            final_stats[target_var] = final_stats[target_var] / 1000
            plot_var = f"{target_var} (km)"

        # ソート設定: Minなら小さい順(昇順)、それ以外は大きい順(降順)
        is_ascending = (method == 'Min')
        final_stats = final_stats.sort_values(by=target_var, ascending=is_ascending)

        # --- 5. グラフ描画 (Altair) ---
        
        # チームカラーの適用（辞書にない場合はグレー）
        color_scale = alt.Scale(
            domain=list(TEAM_COLORS.keys()), 
            range=list(TEAM_COLORS.values())
        )

        chart = alt.Chart(final_stats).mark_bar().encode(
            y=alt.Y('Team:N', sort='x' if is_ascending else '-x', title='Team'),
            x=alt.X(f'{target_var}:Q', title=f'{method} {plot_var}'),
            color=alt.Color('Team:N', scale=color_scale, legend=None),
            tooltip=['Team', alt.Tooltip(target_var, format='.2f')]
        ).properties(
            height=600,
            title=f"{selected_league} {method} Ranking: {target_var}"
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14
        )

        st.altair_chart(chart, use_container_width=True)

        # データプレビュー（確認用）
        with st.expander("See Raw Aggregated Data"):
            st.dataframe(final_stats)

else:
    st.error("No data available. Please check the CSV files in 'data/' folder.")
