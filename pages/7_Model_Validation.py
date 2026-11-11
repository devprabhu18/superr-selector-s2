"""Page 7 · Model Validation — robustness, sensitivity, data-quality, limitations."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dash_common as D

D.page_setup("Model Validation")
D.require_data()
D.header("Model Validation", "Does the answer survive reasonable changes to the model? Where is it less certain?")

d = D.deliveries()
bs = D.batter_stability()
ws = D.bowler_stability()
bcr = D.batter_config_ranks()
wcr = D.bowler_config_ranks()
n_cfg = 9

# ---- stability bars ----
st.markdown("#### Ranking stability — top-10 appearances across 9 model configurations")
c1, c2 = st.columns(2)
def stab_bar(df, title):
    df = df[df.top10_configs > 0].sort_values("top10_configs").tail(16)
    colors = [D.PRESSURE if v == n_cfg else D.BASELINE if v >= n_cfg*0.6 else D.ACCENT_O
              for v in df.top10_configs]
    fig = go.Figure(go.Bar(y=df.player, x=df.top10_configs, orientation="h", marker_color=colors,
                           text=[f"{v}/{n_cfg}" for v in df.top10_configs], textposition="outside",
                           hovertemplate="%{y}<br>%{x} of 9 configs<extra></extra>"))
    D.style(fig, title, 460)
    fig.update_xaxes(title="Configurations in top 10", range=[0, n_cfg+1])
    return fig
c1.plotly_chart(stab_bar(bs, "Batters"), width="stretch")
c2.plotly_chart(stab_bar(ws, "Bowlers"), width="stretch")
st.caption("Pink = appears in all 9 configs (rock-solid); blue = ≥6; orange = more model-dependent. "
           "Configs vary the pressure definition, threshold (0.50/0.55/0.60), eligibility minimums, and the "
           "absolute/uplift/consistency weights.")

with st.expander("IPL-availability view (optional, secondary) — not applied to the primary rankings"):
    import pandas as _pd
    try:
        xb = _pd.read_csv(D.OUT / "excluded_batters.csv")
        xw = _pd.read_csv(D.OUT / "excluded_bowlers.csv")
        st.markdown("The **primary rankings apply no nationality filter**. This optional view removes players "
                    "whose **inferred** nationality (national team in T20Is) is one an IPL franchise cannot sign "
                    "(e.g. Pakistan). The inference is a **data-only heuristic, not independently verified** — "
                    "players with no T20I record cannot be classified — so it is presented only as a secondary lens.")
        c = st.columns(2)
        c[0].markdown("**Removed from the IPL-availability view — batters**")
        c[0].dataframe(xb[["player", "nationality", "score"]].round(1), hide_index=True, width="stretch")
        c[1].markdown("**Removed from the IPL-availability view — bowlers**")
        c[1].dataframe(xw[["player", "nationality", "score"]].round(1), hide_index=True, width="stretch")
    except Exception:
        st.caption("No IPL-availability file found.")

st.markdown("<hr>", unsafe_allow_html=True)

# ---- pressure definition: mean intensity by over (shows definition is meaningful) ----
st.markdown("#### The pressure definition is meaningful, not arbitrary")
by_over = d.groupby("overid")[["bat_pressure", "bowl_pressure"]].mean().reset_index()
fig = go.Figure()
fig.add_scatter(x=by_over.overid, y=by_over.bat_pressure, name="Batting", mode="lines+markers",
                line=dict(color=D.PRESSURE, width=2.5))
fig.add_scatter(x=by_over.overid, y=by_over.bowl_pressure, name="Bowling", mode="lines+markers",
                line=dict(color=D.BASELINE, width=2.5))
D.style(fig, "Mean pressure intensity rises through the innings (and differs by role)", 340)
fig.update_xaxes(title="Over", dtick=2); fig.update_yaxes(title="Mean intensity")
st.plotly_chart(fig, width="stretch")

# ---- sample-size effect ----
st.markdown("#### Sample size vs score — small samples are shrunk, not rewarded")
c3, c4 = st.columns(2)
with c3:
    b = D.batter_rankings()
    fig = go.Figure(go.Scatter(x=b.p_balls, y=b.score, mode="markers",
                    marker=dict(color=D.PRESSURE, size=8, opacity=0.6), text=b.player,
                    hovertemplate="%{text}<br>%{x:.0f} pressure balls · score %{y:.1f}<extra></extra>"))
    D.style(fig, "Batters: pressure balls vs score", 320)
    fig.update_xaxes(title="Pressure balls"); fig.update_yaxes(title="Score")
    st.plotly_chart(fig, width="stretch")
with c4:
    w = D.bowler_rankings()
    fig = go.Figure(go.Scatter(x=w.p_legal_balls, y=w.score, mode="markers",
                    marker=dict(color=D.BASELINE, size=8, opacity=0.6), text=w.player,
                    hovertemplate="%{text}<br>%{x:.0f} pressure balls · score %{y:.1f}<extra></extra>"))
    D.style(fig, "Bowlers: pressure legal balls vs score", 320)
    fig.update_xaxes(title="Pressure legal balls"); fig.update_yaxes(title="Score")
    st.plotly_chart(fig, width="stretch")

st.markdown("<hr>", unsafe_allow_html=True)
cL, cR = st.columns(2)
with cL:
    st.markdown("#### Data-quality checks (Phase 1)")
    st.markdown("""
| Check | Result |
|---|---|
| Delivery key uniqueness | ✅ 0 duplicates |
| Ball data → match metadata join | ✅ 867/867 matched |
| `extras1_runs` meaning | ✅ confirmed a category code, not runs |
| `runs` = off the bat | ✅ 0 contradictions vs is_four/is_six |
| Bowler wicket credit | ✅ run-outs/retired excluded (10,272 credited) |
| Legal-ball counting (`other` extra) | ✅ handled → 6-ball overs |
| Player identity | ✅ keyed on player_id (names not unique) |
| Innings-total reconstruction vs margins | ⚠️ ±1–3 runs (bye/leg-bye magnitudes not stored) |
""")
with cR:
    st.markdown("#### Limitations (stated plainly)")
    st.markdown("""
- **Targets / RRR are approximate** (±1–3 runs); DLS matches excluded from chase logic. Coarse RRR bands make this immaterial to classification.
- **Pressure is a modelling choice**, not an RR-official definition. We mitigate by testing 9 configurations and reporting per-player reliability.
- **Context-matched baseline**: pressure is compared to the player's own non-pressure level *in the same phases*, removing death-over bias. Death is a thin non-pressure sample, so each per-phase baseline is shrunk toward the player's overall baseline.
- **IPL-availability is a secondary view only** — the primary ranking applies no nationality filter. Nationality is inferred from T20I appearances and is not independently verified.
- **No win-probability model**: closeness is proxied by RRR, wickets and phase, not a fitted WP model.
""")
st.caption("Everything here is reproducible from the supplied data via `run_pipeline.py` and `src/sensitivity_analysis.py`.")
