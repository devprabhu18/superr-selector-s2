"""Page 3 · Bowler Analytics."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dash_common as D

D.page_setup("Bowler Analytics")
D.require_data()
D.header("Bowler Analytics", "Pressure vs baseline for every eligible bowler · wickets credited, byes/leg-byes not charged")

bowl = D.bowler_rankings()

st.markdown("#### Top 10 bowlers under pressure")
t = bowl.head(10)[["rank", "player", "pace_or_spin", "score", "p_legal_balls", "p_matches",
                   "p_wickets", "p_economy", "b_economy", "p_wkt_rate_over", "p_dot_pct",
                   "reliability"]].copy()
t.columns = ["#", "Player", "Type", "Score", "Pr. balls", "Pr. matches", "Pr. wkts",
             "Pressure econ", "Baseline econ", "Wkts/over", "Dot %", "Reliability"]
t["Reliability"] = (t["Reliability"] * 100).round(0).astype(int).astype(str) + "%"
st.dataframe(t.round(2), hide_index=True, width="stretch")

c1, c2 = st.columns([1.1, 1])
with c1:
    e = bowl.copy()
    fig = go.Figure()
    lo = min(e.b_economy.min(), e.p_economy.min())
    hi = max(e.b_economy.max(), e.p_economy.max())
    fig.add_scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="No change",
                    line=dict(color=D.INK_MUTED, dash="dash", width=1.5), hoverinfo="skip")
    rest = e[e["rank"] > 10]
    fig.add_scatter(x=rest.b_economy, y=rest.p_economy, mode="markers", name="Eligible bowlers",
                    marker=dict(color=D.BASELINE, size=8, opacity=0.5), text=rest.player,
                    hovertemplate="%{text}<br>base %{x:.1f} → pressure %{y:.1f}<extra></extra>")
    top = e[e["rank"] <= 10]
    fig.add_scatter(x=top.b_economy, y=top.p_economy, mode="markers+text", name="Top 10",
                    marker=dict(color=D.PRESSURE, size=12, line=dict(color=D.SURFACE, width=1.5)),
                    text=top.player, textposition="top center", textfont=dict(size=9, color=D.INK),
                    hovertemplate="%{text}<br>base %{x:.1f} → pressure %{y:.1f}<extra></extra>")
    D.style(fig, "Economy: pressure vs baseline (below the line = tighter under pressure)", 440)
    fig.update_xaxes(title="Baseline economy")
    fig.update_yaxes(title="Pressure economy")
    st.plotly_chart(fig, width="stretch")

with c2:
    top = bowl.head(10).iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=top.player, x=top.p_wkt_rate_over, orientation="h", marker_color=D.ACCENT_P,
                text=[f"{v:.2f}" for v in top.p_wkt_rate_over], textposition="outside",
                hovertemplate="%{y}<br>%{x:.2f} wkts/over under pressure<extra></extra>")
    D.style(fig, "Wicket rate under pressure (wkts per over)", 440)
    fig.update_xaxes(title="Credited wickets per over")
    st.plotly_chart(fig, width="stretch")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("#### Full eligible-bowler table")
q = st.text_input("Search player", "")
show = bowl.copy()
if q:
    show = show[show.player.str.contains(q, case=False, na=False)]
cols = ["rank", "player", "pace_or_spin", "score", "reliability", "p_legal_balls", "p_matches",
        "p_wickets", "p_economy", "b_economy", "econ_uplift", "p_wkt_rate_over", "p_dot_pct",
        "p_boundary_pct", "abs_component", "uplift_component", "consistency_component", "ipl_share"]
disp = show[cols].copy()
disp["reliability"] = (disp["reliability"] * 100).round(0).astype(int)
disp["ipl_share"] = (disp["ipl_share"] * 100).round(0).astype(int)
st.dataframe(disp.round(2), hide_index=True, width="stretch", height=380)
st.caption(f"{len(show)} bowlers shown · eligibility: ≥60 pressure legal balls, ≥5 pressure matches, ≥120 baseline balls. "
           "econ_uplift = baseline econ − pressure econ (positive = tighter under pressure).")
