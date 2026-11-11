"""SupeRR Selector S2 — Pressure Analytics Dashboard.
Page 1: Executive Overview.  Run: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import dash_common as D

D.page_setup("Overview")
D.require_data()

d = D.deliveries()
bat = D.batter_rankings()
bowl = D.bowler_rankings()

D.header("🏏 SupeRR Selector · Pressure Analytics",
         "Identifying the most reliable batters & bowlers under pressure · IPL + T20I, 2022–2026")

# ---- KPI row ----
c = st.columns(6)
D.card(c[0], f"{d.match_id.nunique():,}", "Matches analysed")
D.card(c[1], f"{len(d):,}", "Deliveries")
D.card(c[2], f"{d.striker_id.nunique():,}", "Batters")
D.card(c[3], f"{d.bowler_id.nunique():,}", "Bowlers")
D.card(c[4], f"{int(d.is_bat_pressure.sum()):,}", "Batting-pressure balls", D.PRESSURE)
D.card(c[5], f"{int(d.is_bowl_pressure.sum()):,}", "Bowling-pressure balls", D.ACCENT_T)

st.markdown("<hr>", unsafe_allow_html=True)

left, right = st.columns([1, 1])

with left:
    # format distribution
    fm = (d.groupby("match_format")
          .agg(deliveries=("match_id", "size"), matches=("match_id", "nunique"))
          .reset_index())
    fig = go.Figure()
    fig.add_bar(x=fm.match_format, y=fm.deliveries,
                marker_color=[D.FORMAT_COLORS.get(f, D.ACCENT_O) for f in fm.match_format],
                text=[f"{v:,}" for v in fm.deliveries], textposition="outside",
                hovertemplate="%{x}<br>%{y:,} deliveries<extra></extra>")
    fig.update_traces(marker_line_width=0)
    D.style(fig, "Deliveries by format", 320)
    fig.update_yaxes(title=None)
    st.plotly_chart(fig, width="stretch")

with right:
    # pressure vs non-pressure share (batting)
    share = pd.DataFrame({
        "state": ["Pressure", "Ordinary"],
        "balls": [int(d.is_bat_pressure.sum()), int((1 - d.is_bat_pressure).sum())]})
    fig = go.Figure(go.Pie(labels=share.state, values=share.balls, hole=0.62,
                           marker=dict(colors=[D.PRESSURE, D.GRID]),
                           textinfo="label+percent", sort=False))
    D.style(fig, "Batting-pressure share of all deliveries", 320)
    st.plotly_chart(fig, width="stretch")

# ---- pressure intensity by over (the heart of the definition) ----
by_over = (d.groupby("overid")[["bat_pressure", "bowl_pressure"]].mean().reset_index())
fig = go.Figure()
fig.add_scatter(x=by_over.overid, y=by_over.bat_pressure, name="Batting pressure",
                mode="lines+markers", line=dict(color=D.PRESSURE, width=2.5),
                marker=dict(size=7))
fig.add_scatter(x=by_over.overid, y=by_over.bowl_pressure, name="Bowling pressure",
                mode="lines+markers", line=dict(color=D.BASELINE, width=2.5),
                marker=dict(size=7))
fig.add_vrect(x0=0.5, x1=6.5, fillcolor=D.ACCENT_T, opacity=0.06, line_width=0,
              annotation_text="Powerplay", annotation_position="top left",
              annotation_font_color=D.INK_MUTED)
fig.add_vrect(x0=15.5, x1=20.5, fillcolor=D.PRESSURE, opacity=0.06, line_width=0,
              annotation_text="Death", annotation_position="top right",
              annotation_font_color=D.INK_MUTED)
D.style(fig, "Mean pressure intensity by over — the asymmetry we model", 360)
fig.update_xaxes(title="Over", dtick=2)
fig.update_yaxes(title="Mean intensity (0–1)")
st.plotly_chart(fig, width="stretch")
st.caption("Batting pressure peaks at the death and in hard chases; bowling pressure peaks when "
           "batters are set and scoring freely. The two are modelled separately and asymmetrically.")

st.markdown("<hr>", unsafe_allow_html=True)

# ---- headline top-5 snapshot ----
cL, cR = st.columns(2)
with cL:
    st.markdown("#### Top 5 batters under pressure")
    t = bat.head(5)[["rank", "player", "score", "p_strike_rate", "sr_uplift", "reliability"]].copy()
    t.columns = ["#", "Player", "Score", "Pressure SR", "SR uplift", "Reliability"]
    t["Reliability"] = (t["Reliability"] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(t.round(1), hide_index=True, width="stretch")
with cR:
    st.markdown("#### Top 5 bowlers under pressure")
    t = bowl.head(5)[["rank", "player", "score", "p_economy", "p_wkt_rate_over", "reliability"]].copy()
    t.columns = ["#", "Player", "Score", "Pressure econ", "Wkts/over", "Reliability"]
    t["Reliability"] = (t["Reliability"] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(t.round(2), hide_index=True, width="stretch")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""
<div class='sub'>
<b>How to read this dashboard.</b> Pressure is a per-delivery intensity (0–1) built from innings phase,
wickets lost, balls remaining and — in run-chases — required run rate & chase proximity, computed
chronologically with no future information. Every player is judged against their <i>own context-matched</i>
baseline (same-phase non-pressure level) and scored on an absolute-leaning blend — 50% absolute pressure
performance, 30% uplift vs baseline, 20% match-to-match consistency — with empirical-Bayes shrinkage for small
samples. The rankings shown are the <b>primary statistical result with no nationality filter</b>; an optional
IPL-availability view is on the Final Rankings and Model Validation pages. Use the pages on the left to explore
batters, bowlers, head-to-head comparisons, individual players, the final rankings, and the model-validation evidence.
<br><br><i>Proprietary RR competition data — for evaluation only, not for distribution.</i>
</div>""", unsafe_allow_html=True)
