"""Page 5 · Player Explorer — deep dive on a single player."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dash_common as D

D.page_setup("Player Explorer")
D.require_data()
D.header("Player Explorer", "Match-by-match pressure profile for an individual player")

d = D.deliveries()
teams = D.team_names()
roles = D.player_roles()

role = st.radio("Role", ["Batter", "Bowler"], horizontal=True)

if role == "Batter":
    idcol, namecol, teamcol, pcol = "striker_id", "striker_name", "batting_team_id", "is_bat_pressure"
    rk = D.batter_rankings()
else:
    idcol, namecol, teamcol, pcol = "bowler_id", "bowler_name", "bowling_team_id", "is_bowl_pressure"
    rk = D.bowler_rankings()

names = sorted(d[namecol].dropna().unique().tolist())
default = rk.iloc[0].player if not rk.empty and rk.iloc[0].player in names else names[0]
pick = st.selectbox("Select player", names, index=names.index(default))
sub = d[d[namecol] == pick].copy()
pid = int(sub[idcol].mode().iat[0])

# header card
main_team = teams.get(int(sub[teamcol].mode().iat[0]), "—")
rinfo = roles.get(pid, {})
role_tags = []
if rinfo.get("wk", 0) > 0.5: role_tags.append("Wicketkeeper")
if rinfo.get("cap", 0) > 0.3: role_tags.append("Captain")
fmts = ", ".join(sorted(sub.match_format.dropna().unique()))
rrow = rk[rk[idcol] == pid]
rank_txt = f"#{int(rrow['rank'].iat[0])} (score {rrow['score'].iat[0]:.1f})" if not rrow.empty else "not in eligible pool"

c = st.columns(5)
D.card(c[0], pick, "Player", D.PRESSURE)
D.card(c[1], f"{pid}", "Player ID")
D.card(c[2], main_team, "Main team")
D.card(c[3], f"{sub.match_id.nunique()}", "Matches")
D.card(c[4], rank_txt, "Pressure rank")
if role_tags or fmts:
    st.markdown(f"<div class='sub'>Formats: {fmts} &nbsp;·&nbsp; {' · '.join(role_tags) if role_tags else 'Specialist'}</div>",
                unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# pressure vs baseline summary
if role == "Batter":
    faced = sub[sub.batter_faced == 1]
    def agg(x):
        b = x.batter_faced.sum(); runs = x.bat_runs.sum()
        outs = (x.is_wicket_bool & (x.dismissed_player_id == pid)).sum()
        dots = x.dot_ball.sum()
        return pd.Series({"Balls": int(b), "Runs": int(runs),
                          "SR": round(100 * runs / b, 1) if b else np.nan,
                          "Avg": round(runs / outs, 1) if outs else np.nan,
                          "Dot %": round(100 * dots / b, 1) if b else np.nan,
                          "Matches": x.match_id.nunique()})
    tbl = pd.DataFrame({"Pressure": agg(faced[faced.is_bat_pressure == 1]),
                        "Baseline": agg(faced[faced.is_bat_pressure == 0])}).T.reset_index()
    tbl = tbl.rename(columns={"index": "State"})
    st.markdown("#### Pressure vs baseline")
    st.dataframe(tbl, hide_index=True, width="stretch")
    # per-match pressure SR trend
    pm = (faced[faced.is_bat_pressure == 1].groupby(["match_id", "season"])
          .agg(balls=("batter_faced", "sum"), runs=("bat_runs", "sum")).reset_index())
    pm = pm[pm.balls >= 3]
    pm["sr"] = 100 * pm.runs / pm.balls
    ylab, yval, base = "Pressure strike rate", "sr", tbl.loc[tbl.State=="Baseline","SR"].iat[0]
else:
    def agg(x):
        lb = x.is_legal.sum(); runs = x.bowler_runs.sum(); wk = x.bowler_wicket.sum()
        dots = ((x.bowler_runs == 0) & (x.is_legal == 1)).sum()
        return pd.Series({"Legal balls": int(lb), "Runs": int(runs), "Wickets": int(wk),
                          "Economy": round(6 * runs / lb, 2) if lb else np.nan,
                          "Dot %": round(100 * dots / lb, 1) if lb else np.nan,
                          "Matches": x.match_id.nunique()})
    tbl = pd.DataFrame({"Pressure": agg(sub[sub.is_bowl_pressure == 1]),
                        "Baseline": agg(sub[sub.is_bowl_pressure == 0])}).T.reset_index()
    tbl = tbl.rename(columns={"index": "State"})
    st.markdown("#### Pressure vs baseline")
    st.dataframe(tbl, hide_index=True, width="stretch")
    pm = (sub[sub.is_bowl_pressure == 1].groupby(["match_id", "season"])
          .agg(lb=("is_legal", "sum"), runs=("bowler_runs", "sum")).reset_index())
    pm = pm[pm.lb >= 6]
    pm["sr"] = 6 * pm.runs / pm.lb
    ylab, yval, base = "Pressure economy", "sr", tbl.loc[tbl.State=="Baseline","Economy"].iat[0]

st.markdown(f"#### Match-by-match under pressure")
if pm.empty:
    st.info("Not enough qualifying pressure deliveries per match to chart a trend.")
else:
    pm = pm.sort_values("match_id").reset_index(drop=True)
    pm["n"] = range(1, len(pm) + 1)
    fig = go.Figure()
    fig.add_scatter(x=pm.n, y=pm[yval], mode="lines+markers", line=dict(color=D.PRESSURE, width=2),
                    marker=dict(size=7), name=ylab,
                    text=pm.season, hovertemplate="match %{x} (%{text})<br>"+ylab+" %{y:.1f}<extra></extra>")
    if pd.notna(base):
        fig.add_hline(y=base, line=dict(color=D.BASELINE, dash="dash"),
                      annotation_text="baseline", annotation_font_color=D.INK_MUTED)
    D.style(fig, f"{pick} — {ylab} by pressure match", 380)
    fig.update_xaxes(title="Pressure match (chronological)")
    st.plotly_chart(fig, width="stretch")
