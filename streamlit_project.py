import pandas as pd
import streamlit as st
import altair as alt

# --- 1. 設定 ---
st.set_page_config(layout="wide", page_title="J.League Physical Dashboard")

LEAGUE_FILE_MAP = {'J1': '2025_J1_physical_data.csv', 'J2': '2025_J2_physical_data.csv', 'J3': '2025_J3_physical_data.csv'}
PHYSICAL_VARS = ['Distance','Running Distance','HSR Distance','Sprint Count','HI Distance','HI Count']

# --- 2. データの自動変換エンジン ---
@st.cache_data
def get_match_summaries(league_key):
    try:
        raw_df = pd.read_csv(f"data/{LEAGUE_FILE_MAP[league_key]}")
        
        # ステップA: 「1節のデータを合計して、1節=合計値にする」
        # Match IDとTeamで括り、その試合の全選手を合計。
        # これで、生データ(選手単位)から、新たな「1試合1行のチームデータ」が生成されます。
        match_summary = raw_df.groupby(['Team', 'Match ID'])[PHYSICAL_VARS].sum().reset_index()
        
        # 節番号を見やすく追加
        match_summary = match_summary.sort_values(['Team', 'Match ID'])
        match_summary['Match_No'] = match_summary.groupby('Team').cumcount() + 1
        
        return match_summary
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

# --- 3. メイン画面 ---
selected = st.sidebar.selectbox('リーグ選択', ['J1', 'J2', 'J3'])
df_matches = get_match_summaries(selected) # ここでもう「38個の合計値リスト」になっている

if not df_matches.empty:
    st.title(f"🏆 {selected} チーム分析")
    
    col1, col2 = st.columns(2)
    with col1:
        method = st.selectbox('集計方法', ['Max', 'Min', 'Average'])
    with col2:
        target_var = st.selectbox('指標', PHYSICAL_VARS)

    # ステップB: 「38個出した中からMAX/MINを出す」
    # 0の試合（計測ミス等）を排除してから抽出
    working_df = df_matches[df_matches[target_var] > 0].copy()

    if method == 'Max':
        rank_df = working_df.groupby('Team')[target_var].max().reset_index()
    elif method == 'Min':
        rank_df = working_df.groupby('Team')[target_var].min().reset_index()
    else:
        rank_df = working_df.groupby('Team')[target_var].mean().reset_index()

    # km変換
    if 'Distance' in target_var:
        rank_df[target_var] = rank_df[target_var] / 1000
        y_title = f"{method} {target_var} (km)"
    else:
        y_title = f"{method} {target_var}"

    # ソート (Minなら昇順、それ以外は降順)
    is_asc = (method == 'Min')
    rank_df = rank_df.sort_values(by=target_var, ascending=is_asc)

    # --- 4. グラフ表示 ---
    chart = alt.Chart(rank_df).mark_bar().encode(
        y=alt.Y('Team:N', sort='x' if is_asc else '-x', title='チーム'),
        x=alt.X(f'{target_var}:Q', title=y_title),
        color=alt.Color('Team:N', legend=None),
        tooltip=['Team', alt.Tooltip(target_var, format='.2f')]
    ).properties(height=600)
    
    st.altair_chart(chart, use_container_width=True)

    # --- 5. プロセスの完全可視化 (ここを見れば納得できます) ---
    st.markdown("---")
    st.subheader("📝 計算プロセスの透明化")
    st.write("「1節ごとの合計」を算出し、そのリスト（最大38試合分）から選んでいる証拠です。")
    
    check_team = st.selectbox("内訳を確認するチーム", sorted(df_matches['Team'].unique()))
    team_list = df_matches[df_matches['Team'] == check_team].copy()
    
    if 'Distance' in target_var:
        team_list[target_var] = team_list[target_var] / 1000

    st.write(f"**{check_team} の各試合合計値リスト:**")
    st.dataframe(team_list[['Match_No', 'Match ID', target_var]].rename(columns={target_var: f'チーム合計 {target_var}'}))

else:
    st.error("データが読み込めませんでした。")
