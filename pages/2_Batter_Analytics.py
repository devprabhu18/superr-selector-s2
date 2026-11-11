"""Page 2 · Batter Analytics."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dash_common as D

D.page_setup("Batter Analytics")
D.require_data()
D.header("Batter Analytics", "Pressure vs baseline for every eligible batter · ranked top 10 + full searchable table")

bat = D.batter_rankings()
allb = D.batter_metrics()

# ---- top 10 ----
st.markdown("#### Top 10 batters under pressure")
t = bat.head(10)[["rank", "player", "score", "p_balls", "p_matches", "p_strike_rate",
                  "b_strike_rate", "sr_uplift", "p_average", "p_dot_pct", "reliability"]].copy()
t.columns = ["#", "Player", "Score", "Pr. balls", "Pr. matches", "Pressure SR",
             "Baseline SR", "SR uplift", "Pressure avg", "Dot %", "Reliability"]
t["Reliability"] = (t["Reliability"] * 100).round(0).astype(int).astype(str) + "%"
st.dataframe(t.round(1), hide_index=True, width="stretch")

c1, c2 = st.columns([1.1, 1])
with c1:
    # pressure vs baseline SR scatter, all eligible, top10 highlighted
    e = bat.copy()
    fig = go.Figure()
    lo = min(e.b_strike_rate.min(), e.p_strike_rate.min())
    hi = max(e.b_strike_rate.max(), e.p_strike_rate.max())
    fig.add_scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="No change",
                    line=dict(color=D.INK_MUTED, dash="dash", width=1.5), hoverinfo="skip")
    rest = e[e["rank"] > 10]
    fig.add_scatter(x=rest.b_strike_rate, y=rest.p_strike_rate, mode="markers",
                    name="Eligible batters", marker=dict(color=D.BASELINE, size=8, opacity=0.5),
                    text=rest.player, hovertemplate="%{text}<br>base %{x:.0f} → pressure %{y:.0f}<extra></extra>")
    top = e[e["rank"] <= 10]
    fig.add_scatter(x=top.b_strike_rate, y=top.p_strike_rate, mode="markers+text",
                    name="Top 10", marker=dict(color=D.PRESSURE, size=12,
                    line=dict(color=D.SURFACE, width=1.5)), text=top.player,
                    textposition="top center", textfont=dict(size=9, color=D.INK),
                    hovertemplate="%{text}<br>base %{x:.0f} → pressure %{y:.0f}<extra></extra>")
    D.style(fig, "Strike rate: pressure vs baseline (above the line = raises game under pressure)", 440)
    fig.update_xaxes(title="Baseline strike rate")
    fig.update_yaxes(title="Pressure strike rate")
    st.plotly_chart(fig, width="stretch")

with c2:
    top = bat.head(10).iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=top.player, x=top.sr_uplift, orientation="h",
                marker_color=[D.PRESSURE if v >= 0 else D.BAD for v in top.sr_uplift],
                text=[f"{v:+.0f}" for v in top.sr_uplift], textposition="outside",
                hovertemplate="%{y}<br>SR uplift %{x:+.1f}<extra></extra>")
    D.style(fig, "Strike-rate uplift vs own baseline", 440)
    fig.update_xaxes(title="Pressure SR − baseline SR")
    st.plotly_chart(fig, width="stretch")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("#### Full eligible-batter table")
q = st.text_input("Search player", "")
show = bat.copy()
if q:
    show = show[show.player.str.contains(q, case=False, na=False)]
cols = ["rank", "player", "score", "reliability", "p_balls", "p_matches", "p_strike_rate",
        "b_strike_rate", "sr_uplift", "p_average", "b_average", "p_dot_pct", "p_boundary_pct",
        "abs_component", "uplift_component", "consistency_component", "ipl_share"]
disp = show[cols].copy()
disp["reliability"] = (disp["reliability"] * 100).round(0).astype(int)
disp["ipl_share"] = (disp["ipl_share"] * 100).round(0).astype(int)
st.dataframe(disp.round(2), hide_index=True, width="stretch", height=380)
st.caption(f"{len(show)} batters shown · eligibility: ≥75 pressure balls, ≥5 pressure matches, ≥150 baseline balls. "
           "Components are 0–1 percentile scores within the eligible pool. ipl_share = % of balls in IPL.")
