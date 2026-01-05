import pandas as pd
import streamlit as st
import altair as alt

# --- 1. 設定 ---
st.set_page_config(layout="wide", page_title="J.League Physical Dashboard")

LEAGUE_FILE_MAP = {
    'J1': '2025_J1_physical_data.csv', 
    'J2': '2025_J2_physical_data.csv', 
    'J3': '2025_J3_physical_data.csv'
}

physical_vars = [
    'Distance','Running Distance','HSR Distance','Sprint Count','HI Distance','HI Count',
    'Distance TIP','Running Distance TIP','HSR Distance TIP','HSR Count TIP',
    'Sprint Distance TIP','Sprint Count TIP','Distance OTIP','Running Distance OTIP',
    'HSR Distance OTIP','HSR Count OTIP','Sprint Distance OTIP','Sprint Count OTIP'
]

# --- 2. チーム×節ごとの合計データ作成 ---

@st.cache_data
def get_match_day_summary(league_key):
    try:
        raw_df = pd.read_csv(f"data/{LEAGUE_FILE_MAP[league_key]}")
        
        # 【重要】Team と Match ID (またはDate) を組み合わせて「その試合」を特定
        # その試合に紐づく全選手の数値を合計(sum)し、「1試合＝1行」のデータに変換
        # これで個人の数値（2km）は消え、チームの数値（110km）に置き換わる
        match_summary = raw_df.groupby(['Team', 'Match ID'])[physical_vars].sum().reset_index()
        
        # 節番号（第1節、第2節...）を分かりやすく付与
        match_summary = match_summary.sort_values(['Team', 'Match ID'])
        match_summary['Match_Count'] = match_summary.groupby('Team').cumcount() + 1
        
        return match_summary
    except Exception as e:
        st.error(f"データ処理エラー: {e}")
        return pd.DataFrame()

# --- 3. メインUI ---

selected = st.sidebar.selectbox('リーグ選択', ['J1', 'J2', 'J3'])
df_team_matches = get_match_day_summary(selected)

if not df_team_matches.empty:
    st.title(f"🏆 {selected} チーム別ランキング")
    st.write("各節の**『チーム全員の合計値』**を算出し、そのリストから最大・最小を抽出しています。")

    col1, col2 = st.columns(2)
    with col1:
        method = st.selectbox('集計方法 (全試合のリストから選出)', ['Max', 'Min', 'Average', 'Total'])
    with col2:
        target_var = st.selectbox('指標', physical_vars)

    # --- 4. 38試合のリストから MIN/MAX を抽出 ---

    # Sprint等の0（未計測）を除外
    working_df = df_team_matches[df_team_matches[target_var] > 0].copy()

    if method == 'Max':
        res = working_df.groupby('Team')[target_var].max().reset_index()
    elif method == 'Min':
        res = working_df.groupby('Team')[target_var].min().reset_index()
    elif method == 'Average':
        res = working_df.groupby('Team')[target_var].mean().reset_index()
    else: # Total
        res = working_df.groupby('Team')[target_var].sum().reset_index()

    # 単位変換 (Distanceはkmへ)
    if 'Distance' in target_var:
        res[target_var] = res[target_var] / 1000
        unit = "km"
    else:
        unit = "回/m"

    # ソート (Minなら昇順)
    is_asc = (method == 'Min')
    res = res.sort_values(by=target_var, ascending=is_asc)

    # --- 5. グラフ表示 ---
    chart = alt.Chart(res).mark_bar().encode(
        y=alt.Y('Team:N', sort='x' if is_asc else '-x', title='チーム'),
        x=alt.X(f'{target_var}:Q', title=f"{method} {target_var} ({unit})"),
        color=alt.Color('Team:N', legend=None),
        tooltip=['Team', alt.Tooltip(target_var, format='.2f')]
    ).properties(height=550)

    st.altair_chart(chart, use_container_width=True)

    # --- 6. 算出プロセスの「見える化」 ---
    st.markdown("---")
    st.subheader("🔍 計算プロセスの確認（1試合ごとの合計リスト）")
    check_team = st.selectbox("チームを選択して数値の内訳を確認", sorted(df_team_matches['Team'].unique()))
    
    # そのチームの全試合の「合計値」をリスト表示
    team_list = df_team_matches[df_team_matches['Team'] == check_team].copy()
    if 'Distance' in target_var:
        team_list[target_var] = team_list[target_var] / 1000
    
    st.write(f"**{check_team} の各節のチーム合計数値 ({unit}):**")
    st.write(f"以下の数値（全{len(team_list)}試合分）の中から、最も大きい/小さい値が上のグラフに反映されています。")
    st.dataframe(team_list[['Match_Count', 'Match ID', target_var]].rename(columns={'Match_Count': '節'}))

else:
    st.error("データが読み込めませんでした。")
