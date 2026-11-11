"""Page 4 · Pressure Comparison — head-to-head and distribution views."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dash_common as D

D.page_setup("Pressure Comparison")
D.require_data()
D.header("Pressure Comparison", "Compare players head-to-head and see how pressure intensity is distributed")

role = st.radio("Role", ["Batters", "Bowlers"], horizontal=True)
d = D.deliveries()

if role == "Batters":
    r = D.batter_rankings()
    names = r.sort_values("rank").player.tolist()
    picks = st.multiselect("Select batters to compare", names, default=names[:3], max_selections=5)
    sub = r[r.player.isin(picks)]
    if not sub.empty:
        # grouped pressure vs baseline SR
        fig = go.Figure()
        fig.add_bar(x=sub.player, y=sub.b_strike_rate, name="Baseline SR", marker_color=D.BASELINE)
        fig.add_bar(x=sub.player, y=sub.p_strike_rate, name="Pressure SR", marker_color=D.PRESSURE)
        D.style(fig, "Strike rate: pressure vs baseline", 380)
        fig.update_layout(barmode="group", bargap=0.3)
        st.plotly_chart(fig, width="stretch")

        # normalized radar of 0-1 components
        metrics = ["abs_component", "uplift_component", "consistency_component"]
        labels = ["Absolute", "Uplift", "Consistency"]
        fig = go.Figure()
        for i, (_, row) in enumerate(sub.iterrows()):
            vals = [row[m] for m in metrics]
            fig.add_scatterpolar(r=vals + [vals[0]], theta=labels + [labels[0]], fill="toself",
                                 name=row.player, line=dict(color=D.CATEGORICAL[i % 5]),
                                 opacity=0.75)
        fig.update_layout(template="superr", height=420,
                          polar=dict(bgcolor="rgba(0,0,0,0)",
                                     radialaxis=dict(range=[0, 1], gridcolor=D.GRID, color=D.INK_MUTED),
                                     angularaxis=dict(gridcolor=D.GRID, color=D.INK)),
                          title=dict(text="Rating components (0–1)", font=dict(color=D.INK, size=15)))
        st.plotly_chart(fig, width="stretch")
    pcol = "is_bat_pressure"; icol = "bat_pressure"
else:
    r = D.bowler_rankings()
    names = r.sort_values("rank").player.tolist()
    picks = st.multiselect("Select bowlers to compare", names, default=names[:3], max_selections=5)
    sub = r[r.player.isin(picks)]
    if not sub.empty:
        fig = go.Figure()
        fig.add_bar(x=sub.player, y=sub.b_economy, name="Baseline econ", marker_color=D.BASELINE)
        fig.add_bar(x=sub.player, y=sub.p_economy, name="Pressure econ", marker_color=D.PRESSURE)
        D.style(fig, "Economy: pressure vs baseline (lower is better)", 380)
        fig.update_layout(barmode="group", bargap=0.3)
        st.plotly_chart(fig, width="stretch")

        metrics = ["abs_component", "uplift_component", "consistency_component"]
        labels = ["Absolute", "Uplift", "Consistency"]
        fig = go.Figure()
        for i, (_, row) in enumerate(sub.iterrows()):
            vals = [row[m] for m in metrics]
            fig.add_scatterpolar(r=vals + [vals[0]], theta=labels + [labels[0]], fill="toself",
                                 name=row.player, line=dict(color=D.CATEGORICAL[i % 5]), opacity=0.75)
        fig.update_layout(template="superr", height=420,
                          polar=dict(bgcolor="rgba(0,0,0,0)",
                                     radialaxis=dict(range=[0, 1], gridcolor=D.GRID, color=D.INK_MUTED),
                                     angularaxis=dict(gridcolor=D.GRID, color=D.INK)),
                          title=dict(text="Rating components (0–1)", font=dict(color=D.INK, size=15)))
        st.plotly_chart(fig, width="stretch")
    icol = "bowl_pressure"

st.markdown("<hr>", unsafe_allow_html=True)
cL, cR = st.columns(2)
with cL:
    # pressure intensity distribution by format
    fig = go.Figure()
    for fmt, col in [("IPL", D.ACCENT_O), ("T20I", D.ACCENT_T)]:
        mask = (d.is_ipl == 1) if fmt == "IPL" else (d.is_ipl == 0)
        fig.add_histogram(x=d.loc[mask, icol], name=fmt, marker_color=col, opacity=0.6,
                          nbinsx=25, histnorm="probability density")
    D.style(fig, f"{role} pressure-intensity distribution by format", 360)
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="Pressure intensity (0–1)")
    st.plotly_chart(fig, width="stretch")
with cR:
    # IPL vs T20I mean intensity by phase
    icol2 = icol
    g = d.groupby(["phase", "is_ipl"])[icol2].mean().reset_index()
    g["fmt"] = g.is_ipl.map({1: "IPL", 0: "T20I"})
    order = ["powerplay", "middle", "death"]
    fig = go.Figure()
    for fmt, col in [("IPL", D.ACCENT_O), ("T20I", D.ACCENT_T)]:
        gg = g[g.fmt == fmt].set_index("phase").reindex(order).reset_index()
        fig.add_bar(x=gg.phase, y=gg[icol2], name=fmt, marker_color=col)
    D.style(fig, f"Mean {role.lower()} pressure by phase & format", 360)
    fig.update_layout(barmode="group")
    st.plotly_chart(fig, width="stretch")
