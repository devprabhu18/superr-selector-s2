"""Page 6 · Final Rankings — the submission lists with scoring breakdown."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dash_common as D

D.page_setup("Final Rankings")
D.require_data()
D.header("Final Rankings", "The submission Top 10s, with transparent component scoring")

bat = D.batter_rankings().head(10)
bowl = D.bowler_rankings().head(10)
W = {"Absolute": 0.40, "Uplift": 0.35, "Consistency": 0.25}

st.info("These are the **primary statistical rankings** — the pure, data-driven result with "
        "**no nationality filter**. A separate, clearly-labelled **IPL-availability view** (which removes "
        "players an IPL franchise cannot sign) is in the expander below and on the *Model Validation* page.")


def component_bar(df, title):
    df = df.iloc[::-1]
    fig = go.Figure()
    comps = [("abs_component", "Absolute", D.PRESSURE, W["Absolute"]),
             ("uplift_component", "Uplift", D.BASELINE, W["Uplift"]),
             ("consistency_component", "Consistency", D.ACCENT_O, W["Consistency"])]
    for col, name, color, w in comps:
        fig.add_bar(y=df.player, x=df[col] * w * 100, name=name, orientation="h",
                    marker_color=color,
                    hovertemplate="%{y}<br>"+name+" contrib %{x:.1f}<extra></extra>")
    D.style(fig, title, 460)
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Weighted contribution to score (0–100)")
    return fig

c1, c2 = st.columns(2)
c1.plotly_chart(component_bar(bat, "Top 10 batters — score composition"), width="stretch")
c2.plotly_chart(component_bar(bowl, "Top 10 bowlers — score composition"), width="stretch")

st.markdown("<hr>", unsafe_allow_html=True)
cL, cR = st.columns(2)
with cL:
    st.markdown("#### 🏏 Top 10 Batters Under Pressure")
    t = bat[["rank", "player", "score", "reliability", "p_balls", "p_matches",
             "p_strike_rate", "sr_uplift"]].copy()
    t.columns = ["#", "Player", "Score", "Rel.", "Pr.balls", "Pr.mts", "Pr. SR", "SR uplift"]
    t["Rel."] = (t["Rel."] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(t.round(1), hide_index=True, width="stretch")
with cR:
    st.markdown("#### 🎯 Top 10 Bowlers Under Pressure")
    t = bowl[["rank", "player", "score", "reliability", "p_legal_balls", "p_matches",
              "p_economy", "p_wkt_rate_over"]].copy()
    t.columns = ["#", "Player", "Score", "Rel.", "Pr.balls", "Pr.mts", "Pr. econ", "Wkts/ov"]
    t["Rel."] = (t["Rel."] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(t.round(2), hide_index=True, width="stretch")

st.markdown("<hr>", unsafe_allow_html=True)
with st.expander("🇮🇳 IPL-availability view (optional, secondary) — players an IPL side could actually sign"):
    st.caption("This removes players whose **inferred** nationality (from their T20I national team) is one an "
               "IPL franchise cannot sign. Nationality inference is a data-only heuristic and is **not "
               "independently verified** — uncapped players have no T20I record and cannot be classified. "
               "This is NOT the primary ranking.")
    try:
        bipl = pd.read_csv(D.OUT / "batter_rankings_ipl_available.csv").head(10)
        wipl = pd.read_csv(D.OUT / "bowler_rankings_ipl_available.csv").head(10)
        ic1, ic2 = st.columns(2)
        with ic1:
            st.markdown("**Top 10 batters (IPL-available)**")
            tt = bipl[["rank", "player", "score", "p_strike_rate", "sr_uplift"]].copy()
            tt.columns = ["#", "Player", "Score", "Pr. SR", "SR uplift"]
            st.dataframe(tt.round(1), hide_index=True, width="stretch")
        with ic2:
            st.markdown("**Top 10 bowlers (IPL-available)**")
            tt = wipl[["rank", "player", "score", "p_economy", "p_wkt_rate_over"]].copy()
            tt.columns = ["#", "Player", "Score", "Pr. econ", "Wkts/ov"]
            st.dataframe(tt.round(2), hide_index=True, width="stretch")
    except Exception:
        st.caption("IPL-availability files not found — run the pipeline.")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""
#### Scoring methodology (identical logic, role-specific metrics)
**Score = 0.50 · Absolute + 0.30 · Uplift + 0.20 · Consistency**, each component a 0–1 percentile within the eligible pool, ×100.

- **Absolute (50%)** — how good under pressure, *format-adjusted* against league pressure par (batters: pressure SR + survival; bowlers: economy vs par + wicket rate + dot %). Weighted highest so a genuinely high-level pressure performance is rewarded on its own merit.
- **Uplift (30%)** — pressure minus the player's **context-matched** baseline (their own non-pressure level *in the same innings phases*, shrunk toward their overall baseline), **empirical-Bayes shrunk** toward zero by pressure sample size. Context-matching removes the death-over illusion from the raw uplift.
- **Consistency (20%)** — share of pressure *matches* in which the player delivered. Batters: SR within 10% of their (context-matched) baseline. Bowlers: a **graded** blend of economy improvement (45%), wicket contribution (30%) and dot-ball rate (25%) — replacing the old "economy ≤ baseline **or** one wicket" rule, which a single wicket could fully satisfy.
- **Reliability (Rel.)** — % of 9 model configurations (pressure definitions, thresholds, eligibility, weights) in which the player still makes the top 10. See *Model Validation*.

Eligibility: batters ≥ 75 pressure balls, ≥ 5 pressure matches, ≥ 150 baseline balls; bowlers ≥ 60 pressure legal balls, ≥ 5 pressure matches, ≥ 120 baseline balls. No player identity or target list is hard-coded anywhere, and the primary ranking applies no nationality filter.
""")
