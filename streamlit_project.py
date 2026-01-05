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

# 変数リスト
available_vars = [
    'Distance','Running Distance','HSR Distance','Sprint Count','HI Distance','HI Count',
    'Distance TIP','Running Distance TIP','HSR Distance TIP','HSR Count TIP',
    'Sprint Distance TIP','Sprint Count TIP','Distance OTIP','Running Distance OTIP',
    'HSR Distance OTIP','HSR Count OTIP','Sprint Distance OTIP','Sprint Count OTIP'
]

# --- 2. 徹底的な「チーム1試合合計」の作成 ---

@st.cache_data
def load_and_group_by_match(league_key):
    try:
        raw_df = pd.read_csv(f"data/{LEAGUE_FILE_MAP[league_key]}")
        
        # Match IDだけでは不安なため、日付や相手チーム(があれば)も含めて「1試合」を特定する
        # ここではTeamとMatch IDを基点にします
        group_keys = ['Team', 'Match ID']
        if 'Match Date' in raw_df.columns:
            group_keys.append('Match Date')

        # --- ステップ1: 1試合内の選手全員を合計して「チーム1試合の数値」を作る ---
        # 38試合あるなら、ここで各チームちょうど38行のデータになります
        team_match_totals = raw_df.groupby(group_keys)[available_vars].sum().reset_index()
        
        return team_match_totals
    except Exception as e:
        st.error(f"データ読み込みに失敗しました: {e}")
        return pd.DataFrame()

# --- 3. メインUI ---

st.sidebar.title("Physical Dashboard")
selected_league = st.sidebar.selectbox('リーグ選択', ['J1', 'J2', 'J3'])

# ここで「チームの1試合合計リスト（38個）」を取得
df_match_list = load_and_group_by_match(selected_league)

if not df_match_list.empty:
    st.title(f"🏆 {selected_league} フィジカル分析")
    
    col1, col2 = st.columns(2)
    with col1:
        method = st.selectbox('集計方法 (38試合の中から抽出)', ['Max', 'Min', 'Average', 'Total'])
    with col2:
        target_var = st.selectbox('評価指標', available_vars)

    # --- 4. ランキング算出 ---

    # 0の除外 (Sprint 0などの異常値試合を排除)
    working_df = df_match_list[df_match_list[target_var] > 0].copy()

    # --- ステップ2: 38試合のリストの中から1つの数値(Max/Min)を選ぶ ---
    if method == 'Max':
        final_stats = working_df.groupby('Team')[target_var].max().reset_index()
    elif method == 'Min':
        final_stats = working_df.groupby('Team')[target_var].min().reset_index()
    elif method == 'Average':
        final_stats = working_df.groupby('Team')[target_var].mean().reset_index()
    else:
        final_stats = working_df.groupby('Team')[target_var].sum().reset_index()

    # Distanceの単位をkmへ
    if 'Distance' in target_var:
        final_stats[target_var] = final_stats[target_var] / 1000

    # ソート
    is_asc = (method == 'Min')
    final_stats = final_stats.sort_values(by=target_var, ascending=is_asc)

    # --- 5. グラフと検証用データの表示 ---

    chart = alt.Chart(final_stats).mark_bar().encode(
        y=alt.Y('Team:N', sort='x' if is_asc else '-x'),
        x=alt.X(f'{target_var}:Q', title=f"{method} {target_var}"),
        color=alt.Color('Team:N', legend=None),
        tooltip=['Team', target_var]
    ).properties(height=600)

    st.altair_chart(chart, use_container_width=True)

    # --- 検証用表示 (ここを見れば計算が合っているか分かります) ---
    st.markdown("---")
    st.subheader("📊 数値の検証（計算プロセス）")
    
    test_team = st.selectbox("確認したいチームを選択", sorted(df_match_list['Team'].unique()))
    
    # そのチームの全試合(38試合)の合計値リストを表示
    team_full_list = df_match_list[df_match_list['Team'] == test_team].sort_values('Match ID')
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write(f"**{test_team} の全試合合計値リスト (38試合分)**")
        st.write("この数値群の中から MAX や MIN が選ばれています。")
        st.dataframe(team_full_list[['Match ID', target_var]])
    
    with col_b:
        st.write(f"**抽出結果**")
        current_val = final_stats[final_stats['Team'] == test_team][target_var].values[0]
        st.metric(label=f"{test_team} の {method} 値", value=f"{current_val:.2f}")
        
else:
    st.error("CSVデータが見つかりません。")
