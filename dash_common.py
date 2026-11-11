"""Shared theme, palette and cached data loaders for the Streamlit dashboard.

Palette validated for dark mode via the dataviz skill validator (all checks pass):
pink=pressure, blue=baseline, plus orange/purple/teal for categoricals.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parent
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

# ---- validated palette ----
INK = "#F5F7FA"
INK_MUTED = "#9BA6B7"
SURFACE = "#0E1117"
PANEL = "#161B26"
GRID = "#262C3A"
PRESSURE = "#F2447A"     # pink  (pressure)
BASELINE = "#3B8EEA"     # blue  (baseline)
ACCENT_O = "#CC7320"     # orange
ACCENT_P = "#9B6BE0"     # purple
ACCENT_T = "#1FA594"     # teal
GOOD = "#2FB170"
BAD = "#E0574A"
CATEGORICAL = [PRESSURE, BASELINE, ACCENT_O, ACCENT_P, ACCENT_T]

PHASE_COLORS = {"powerplay": BASELINE, "middle": ACCENT_P, "death": PRESSURE}
FORMAT_COLORS = {"T20": ACCENT_O, "T20I": ACCENT_T, "IPL": ACCENT_O}

_TEMPLATE = go.layout.Template()
_TEMPLATE.layout = go.Layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, Segoe UI, system-ui, sans-serif", color=INK, size=13),
    colorway=CATEGORICAL,
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, color=INK_MUTED),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, color=INK_MUTED),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=INK_MUTED)),
    margin=dict(l=10, r=10, t=48, b=10), hoverlabel=dict(font_size=12),
)
pio.templates["superr"] = _TEMPLATE


def style(fig, title=None, height=360):
    fig.update_layout(template="superr", height=height,
                      title=dict(text=title, font=dict(size=15, color=INK)) if title else None)
    return fig


def page_setup(title):
    st.set_page_config(page_title=f"SupeRR · {title}", page_icon="🏏", layout="wide")
    st.markdown(f"""
    <style>
      .stApp {{ background: {SURFACE}; }}
      section[data-testid="stSidebar"] {{ background: {PANEL}; }}
      h1,h2,h3,h4 {{ color: {INK}; font-family: Inter, system-ui, sans-serif; letter-spacing:-0.01em;}}
      p, label, span, div {{ color: {INK}; }}
      [data-testid="stMetricValue"] {{ color: {INK}; font-weight:700; }}
      [data-testid="stMetricLabel"] {{ color: {INK_MUTED}; }}
      .pill {{ display:inline-block; padding:2px 10px; border-radius:999px;
              font-size:12px; font-weight:600; margin-right:6px;}}
      .stDataFrame {{ border:1px solid {GRID}; border-radius:8px; }}
      hr {{ border-color:{GRID}; }}
      .card {{ background:{PANEL}; border:1px solid {GRID}; border-radius:12px;
              padding:16px 18px; }}
      .big {{ font-size:34px; font-weight:800; color:{INK}; line-height:1.1; }}
      .sub {{ font-size:13px; color:{INK_MUTED}; }}
      .accent {{ color:{PRESSURE}; }}
    </style>""", unsafe_allow_html=True)


def header(title, subtitle=""):
    st.markdown(f"<h1 style='margin-bottom:0'>{title}</h1>"
                f"<div class='sub' style='margin-bottom:14px'>{subtitle}</div>",
                unsafe_allow_html=True)


def card(col, value, label, accent=INK):
    col.markdown(f"<div class='card'><div class='big' style='color:{accent}'>{value}</div>"
                 f"<div class='sub'>{label}</div></div>", unsafe_allow_html=True)


# ---------- cached loaders ----------
@st.cache_data(show_spinner=False)
def deliveries():
    return pd.read_parquet(PROC / "deliveries_state.parquet")

@st.cache_data(show_spinner=False)
def batter_rankings():
    return pd.read_csv(OUT / "batter_rankings.csv")

@st.cache_data(show_spinner=False)
def bowler_rankings():
    return pd.read_csv(OUT / "bowler_rankings.csv")

@st.cache_data(show_spinner=False)
def batter_metrics():
    return pd.read_csv(OUT / "batter_metrics_all.csv")

@st.cache_data(show_spinner=False)
def bowler_metrics():
    return pd.read_csv(OUT / "bowler_metrics_all.csv")

@st.cache_data(show_spinner=False)
def batter_stability():
    return pd.read_csv(OUT / "batter_stability.csv")

@st.cache_data(show_spinner=False)
def bowler_stability():
    return pd.read_csv(OUT / "bowler_stability.csv")

@st.cache_data(show_spinner=False)
def batter_config_ranks():
    return pd.read_csv(OUT / "batter_config_ranks.csv")

@st.cache_data(show_spinner=False)
def bowler_config_ranks():
    return pd.read_csv(OUT / "bowler_config_ranks.csv")


@st.cache_data(show_spinner=False)
def team_names():
    """team_id -> team_name from the (local) pack."""
    t = pd.read_csv(ROOT / "6af3166e7b922_data_pack" / "teams.csv")
    return dict(zip(t.team_id, t.team_name))


@st.cache_data(show_spinner=False)
def player_roles():
    """player_id -> dict(is_wk, is_captain fraction) from playing_eleven (local)."""
    pe = pd.read_csv(ROOT / "6af3166e7b922_data_pack" / "playing_eleven.csv")
    for c in ("is_wk", "is_captain"):
        pe[c] = pe[c].map({"True": True, "False": False, True: True, False: False})
    g = pe.groupby("player_id").agg(wk=("is_wk", "mean"), cap=("is_captain", "mean"))
    return g.to_dict("index")


def data_available():
    return (PROC / "deliveries_state.parquet").exists() and (OUT / "batter_rankings.csv").exists()


def require_data():
    if not data_available():
        st.error("Processed data not found. Run `python3 -I run_pipeline.py` first.")
        st.stop()