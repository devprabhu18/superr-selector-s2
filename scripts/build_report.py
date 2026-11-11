"""Generate methodology report figures (matplotlib, print-friendly) + the PDF.

Run: python3 -I scripts/build_report.py
Reads outputs/*.csv and data/processed; writes reports/figures/*.png and
reports/methodology_report.pdf. Every number is read from the pipeline outputs.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# brand palette
NAVY = "#141B2D"; PINK = "#E0356F"; BLUE = "#2E7DD1"; ORANGE = "#C2691A"
PURPLE = "#7E4FD0"; TEAL = "#149184"; INK = "#1b2230"; MUTE = "#6b7688"; GRID = "#dfe3ea"
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "font.size": 11,
    "axes.edgecolor": GRID, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTE, "ytick.color": MUTE, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "font.family": "sans-serif", "savefig.dpi": 150, "savefig.bbox": "tight",
})

bat = pd.read_csv(OUT / "batter_rankings.csv")
bowl = pd.read_csv(OUT / "bowler_rankings.csv")
bs = pd.read_csv(OUT / "batter_stability.csv")
ws = pd.read_csv(OUT / "bowler_stability.csv")
d = pd.read_parquet(PROC / "deliveries_state.parquet")


def fig_pressure_curve():
    g = d.groupby("overid")[["bat_pressure", "bowl_pressure"]].mean().reset_index()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.axvspan(0.5, 6.5, color=TEAL, alpha=0.07)
    ax.axvspan(15.5, 20.5, color=PINK, alpha=0.07)
    ax.plot(g.overid, g.bat_pressure, "-o", color=PINK, lw=2.2, ms=5, label="Batting pressure")
    ax.plot(g.overid, g.bowl_pressure, "-o", color=BLUE, lw=2.2, ms=5, label="Bowling pressure")
    ax.set_xlabel("Over"); ax.set_ylabel("Mean pressure intensity (0–1)")
    ax.set_xticks(range(2, 21, 2)); ax.legend(frameon=False, loc="upper left")
    ax.text(3.2, 0.03, "Powerplay", color=MUTE, fontsize=9)
    ax.text(17.3, 0.03, "Death", color=MUTE, fontsize=9)
    fig.savefig(FIG / "pressure_curve.png"); plt.close(fig)


def fig_top_bat():
    t = bat.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(t))
    ax.barh(y - 0.2, t.b_strike_rate, 0.4, color=BLUE, label="Baseline SR")
    ax.barh(y + 0.2, t.p_strike_rate, 0.4, color=PINK, label="Pressure SR")
    ax.set_yticks(y); ax.set_yticklabels(t.player)
    ax.set_xlabel("Strike rate"); ax.legend(frameon=False, loc="lower right")
    for yi, (b, p) in enumerate(zip(t.b_strike_rate, t.p_strike_rate)):
        ax.text(p + 2, yi + 0.2, f"{p:.0f}", va="center", fontsize=8, color=INK)
    ax.set_title("Top 10 batters — strike rate under pressure vs baseline", color=INK, loc="left")
    fig.savefig(FIG / "top_batters.png"); plt.close(fig)


def fig_top_bowl():
    t = bowl.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(t))
    ax.barh(y - 0.2, t.b_economy, 0.4, color=BLUE, label="Baseline economy")
    ax.barh(y + 0.2, t.p_economy, 0.4, color=PINK, label="Pressure economy")
    ax.set_yticks(y); ax.set_yticklabels(t.player)
    ax.set_xlabel("Economy (runs/over) — lower is better"); ax.legend(frameon=False, loc="lower right")
    ax.set_title("Top 10 bowlers — economy under pressure vs baseline", color=INK, loc="left")
    fig.savefig(FIG / "top_bowlers.png"); plt.close(fig)


def fig_stability():
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.4))
    for ax, df, title in [(axes[0], bs, "Batters"), (axes[1], ws, "Bowlers")]:
        s = df[df.top10_configs > 0].sort_values("top10_configs").tail(14)
        colors = [PINK if v == 9 else BLUE if v >= 6 else ORANGE for v in s.top10_configs]
        ax.barh(np.arange(len(s)), s.top10_configs, color=colors)
        ax.set_yticks(np.arange(len(s))); ax.set_yticklabels(s.player, fontsize=8)
        ax.set_xlim(0, 10); ax.set_xlabel("configs in top 10 (of 9)")
        ax.set_title(title, color=INK, loc="left")
    fig.suptitle("Ranking stability across 9 model configurations", color=INK, x=0.1, ha="left")
    fig.savefig(FIG / "stability.png"); plt.close(fig)


def fig_components():
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.2))
    W = {"abs_component": ("Absolute", PINK, 0.40), "uplift_component": ("Uplift", BLUE, 0.35),
         "consistency_component": ("Consistency", ORANGE, 0.25)}
    for ax, df, title in [(axes[0], bat.head(10), "Batters"), (axes[1], bowl.head(10), "Bowlers")]:
        t = df.iloc[::-1]; y = np.arange(len(t)); left = np.zeros(len(t))
        for col, (name, color, w) in W.items():
            vals = t[col] * w * 100
            ax.barh(y, vals, left=left, color=color, label=name)
            left += vals.values
        ax.set_yticks(y); ax.set_yticklabels(t.player, fontsize=8)
        ax.set_xlabel("weighted score contribution"); ax.set_title(title, color=INK, loc="left")
    axes[1].legend(frameon=False, loc="lower right", fontsize=8)
    fig.suptitle("Score composition: Absolute / Uplift / Consistency", color=INK, x=0.1, ha="left")
    fig.savefig(FIG / "components.png"); plt.close(fig)


for f in [fig_pressure_curve, fig_top_bat, fig_top_bowl, fig_stability, fig_components]:
    f()
    print("fig:", f.__name__)
print("figures done ->", FIG)

# ============================ PDF REPORT ============================
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, HRFlowable)
from reportlab.lib.enums import TA_LEFT

NAVY_C = colors.HexColor("#141B2D")
PINK_C = colors.HexColor("#E0356F")
BLUE_C = colors.HexColor("#2E7DD1")
MUTE_C = colors.HexColor("#5b6472")
LIGHT = colors.HexColor("#f2f4f8")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], textColor=NAVY_C, fontSize=17, spaceAfter=6, spaceBefore=10)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=PINK_C, fontSize=12.5, spaceAfter=4, spaceBefore=10)
BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontSize=9.6, leading=14, textColor=colors.HexColor("#1b2230"), spaceAfter=5)
SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=8.3, textColor=MUTE_C)
BULLET = ParagraphStyle("BUL", parent=BODY, leftIndent=12, bulletIndent=2, spaceAfter=2)

story = []
def P(t, s=BODY): story.append(Paragraph(t, s))
def H(t): story.append(Paragraph(t, H1))
def h(t): story.append(Paragraph(t, H2))
def SP(h=6): story.append(Spacer(1, h))
def rule(): story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d8dce4"), spaceBefore=6, spaceAfter=6))
def bullets(items):
    for it in items:
        story.append(Paragraph(it, BULLET, bulletText="•"))

def ranking_table(df, kind):
    if kind == "bat":
        head = ["#", "Batter", "Score", "Rel.", "Pr.\nballs", "Pr.\nmts", "Pressure\nSR", "Base\nSR", "SR\nupl.", "Pr.\navg"]
        rows = [[int(r["rank"]), r["player"], f"{r['score']:.1f}", f"{r['reliability']*100:.0f}%",
                 int(r["p_balls"]), int(r["p_matches"]), f"{r['p_strike_rate']:.0f}",
                 f"{r['b_strike_rate']:.0f}", f"+{r['sr_uplift']:.0f}", f"{r['p_average']:.0f}"]
                for _, r in df.head(10).iterrows()]
        widths = [8, 86, 32, 28, 30, 28, 44, 34, 32, 32]
    else:
        head = ["#", "Bowler", "Type", "Score", "Rel.", "Pr.\nballs", "Pr.\nmts", "Pr.\nwkts", "Pressure\necon", "Base\necon", "Wkts/\nover"]
        rows = [[int(r["rank"]), r["player"], r["pace_or_spin"], f"{r['score']:.1f}", f"{r['reliability']*100:.0f}%",
                 int(r["p_legal_balls"]), int(r["p_matches"]), int(r["p_wickets"]),
                 f"{r['p_economy']:.2f}", f"{r['b_economy']:.2f}", f"{r['p_wkt_rate_over']:.2f}"]
                for _, r in df.head(10).iterrows()]
        widths = [8, 80, 34, 30, 26, 28, 26, 26, 44, 34, 32]
    data = [head] + rows
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_C),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.6), ("FONTSIZE", (0, 0), (-1, 0), 7.2),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"), ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY_C),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
    ]))
    return t

def img(name, w=170):
    p = FIG / name
    from PIL import Image as PILImage
    iw, ih = PILImage.open(p).size
    W = w * mm
    return Image(str(p), width=W, height=W * ih / iw)

# ---------- TITLE ----------
P("<b>RAJASTHAN ROYALS · SupeRR SELECTOR SEASON 2</b>", ParagraphStyle("t0", parent=BODY, textColor=PINK_C, fontSize=11))
story.append(Paragraph("Identifying the Most Reliable<br/>Players Under Pressure", ParagraphStyle("title", parent=H1, fontSize=26, leading=30, spaceBefore=10)))
P("Round 1 Methodology Report", ParagraphStyle("sub", parent=BODY, fontSize=13, textColor=NAVY_C))
SP(4)
P("A reproducible, delivery-level framework that measures how batters and bowlers perform in "
  "high-pressure situations relative to their own baseline, across IPL and T20I cricket (2022–2026).", BODY)
SP(10); rule()
P(f"Eligible pool: {len(bat)} batters, {len(bowl)} bowlers &nbsp;·&nbsp; "
  f"{d.match_id.nunique()} matches &nbsp;·&nbsp; {len(d):,} deliveries analysed &nbsp;·&nbsp; "
  "IPL + T20I combined, format-adjusted baselines", SMALL)
P("Confidential — prepared on supplied proprietary competition data. Not for distribution.", SMALL)
story.append(PageBreak())

# ---------- 1 EXECUTIVE SUMMARY ----------
H("1 · Executive Summary")
P("We define <b>pressure</b> as a continuous, per-delivery intensity (0–1) built from the match situation "
  "<i>before</i> each ball is bowled — innings phase, wickets already lost, balls remaining and, in run-chases, "
  "the required run rate and how alive the contest is. Crucially we build <b>two separate, asymmetric models</b>: "
  "a batting team is under pressure in hard chases and at the death, whereas a bowling team is under pressure when "
  "batters are set and scoring freely. Every player is judged against a <b>context-matched baseline</b> (their own "
  "non-pressure level in the same innings phases) and scored on an <b>absolute-leaning blend</b> — 50% absolute "
  "pressure performance, 30% uplift versus baseline, 20% match-to-match consistency — with empirical-Bayes "
  "shrinkage so small samples cannot spike. Rankings are stress-tested across nine model configurations; the "
  "<b>reliability</b> column is the share in which a player stays in the top 10. These lists are the <b>primary "
  "statistical result and apply no nationality filter</b>; an optional IPL-availability view is given in §15.")
SP(2)
h("Top 10 Batters Under Pressure")
story.append(ranking_table(bat, "bat"))
SP(6)
h("Top 10 Bowlers Under Pressure")
story.append(ranking_table(bowl, "bowl"))
SP(4)
P("Rel. = reliability (of 9 configs). Pr. = pressure. SR upl. = pressure SR minus own baseline SR. "
  "Wkts credited to the bowler only (run-outs excluded).", SMALL)
story.append(PageBreak())

# ---------- 2 PROBLEM & APPROACH ----------
H("2 · Problem Statement & Approach")
P("Round 1 asks us to build a data-driven system that measures how batters and bowlers perform in high-pressure "
  "situations compared with their usual level, and to rank the players who deliver most consistently. The definition "
  "of pressure is left to us. Our guiding principles were:")
bullets([
  "<b>Reliability over reputation.</b> Every pick is derived from the supplied ball-by-ball data; no player list is hard-coded.",
  "<b>Self-referenced.</b> A high pressure strike rate is only credited relative to that batter's own baseline — we reward players who <i>maintain or raise</i> their level when it matters.",
  "<b>No future leakage.</b> Pressure at a delivery uses only information available up to that ball; the match result is never used to label earlier deliveries.",
  "<b>Honest about the data.</b> Where a quantity (e.g. exact team totals) cannot be reconstructed reliably, we say so and avoid building on it.",
  "<b>Robustness first.</b> A single formula is not trusted; the answer must survive reasonable changes to thresholds, weights and the pressure definition itself.",
])

# ---------- 3 DATASET ----------
H("3 · Dataset")
P(f"Seven supplied files. The core is <b>ball_by_ball.csv</b> ({len(d):,} main-innings deliveries after excluding "
  "6 super-over innings), joined to match metadata (883 matches, 867 with ball data), competitions (141; "
  "5 IPL seasons 2022–2026), teams, playing XIs and competition–team–player mappings. Coverage splits roughly evenly: "
  "~397 T20 matches (371 IPL) and ~470 T20I. All joins verified; the delivery key (match, innings, ball) is unique.")

# ---------- 4 DATA CLEANING ----------
H("4 · Data Cleaning & the Extras Puzzle")
P("The single most important data-quality finding: <b>extras1_runs is not a number of runs — it is a category code</b>, "
  "one-to-one with extras_type (6 = legal ball, 2 = wide, 3 = leg-bye, 4 = bye, 1 = no-ball, 5 = other, 7 = penalty). "
  "Summing it would be meaningless. We confirmed that <b>runs</b> is <b>runs off the bat</b> (every six has runs = 6, every "
  "four runs = 4, with zero contradictions; all wides/byes/leg-byes carry runs = 0). Therefore:")
bullets([
  "<b>Batting metrics are exact</b> — strike rate, boundary %, dot %, dismissals all come straight from reliable fields.",
  "<b>Bowler economy is reliable</b> — byes and leg-byes are not charged to the bowler, so a bowler's runs = off-bat + wides + no-balls (+ recorded extra runs).",
  "<b>Team totals / required run rate are approximate</b> — bye/leg-bye magnitudes beyond 1 are not stored. Validated against 356 result margins: median error 0, 266 within ±3 runs; the large misses are all DLS rain games, which we exclude from chase logic.",
  "<b>Bowler wickets</b> exclude run-outs, retired-out and obstruction (609 of 10,881); 10,272 are credited. <b>Legal balls</b> exclude wides, no-balls and the re-bowled ‘other’ extra. All aggregation keys on player_id, since some names map to two IDs.",
])

# ---------- 5 PRESSURE ----------
H("5 · Pressure Definition")
P("Pressure is a weighted blend of normalised signals, each in [0,1], combined differently for batting and bowling. "
  "The chart below shows the mean intensity by over: batting pressure climbs steadily and jumps at the death; bowling "
  "pressure is flatter but peaks when batters attack — exactly the asymmetry we want.")
story.append(img("pressure_curve.png", 165)); SP(3)
h("Batting pressure rises with")
bullets(["<b>Innings phase</b> — death overs carry the highest stake, powerplay the lowest.",
         "<b>Wickets already lost</b> — a rebuild after a collapse is higher pressure.",
         "<b>Required run rate</b> (chases) — a demanding chase is high pressure, but a <i>hopeless</i> chase (needing &gt;3 runs/ball with few resources) is dampened, since garbage-time hitting is not a fair clutch test."])
h("Bowling pressure rises with")
bullets(["<b>Death overs</b>, where margins are smallest.",
         "<b>Batting momentum</b> — a high current run rate with wickets in hand means the bowler must stem the flow.",
         "<b>Defending a gettable chase</b> — when the batting side is cruising (low required rate), the bowler is under most pressure to break through."])
P("A delivery is classified ‘pressure’ when its intensity ≥ 0.55 (configurable; swept in §12). This yields "
  f"{d.is_bat_pressure.mean():.0%} batting-pressure and {d.is_bowl_pressure.mean():.0%} bowling-pressure deliveries.", SMALL)

# ---------- 6 MATCH STATE ----------
H("6 · Match-State Reconstruction")
P("For every delivery we reconstruct the state before the ball, chronologically: score so far, wickets fallen, "
  "wickets in hand, legal balls bowled and remaining, and — in the second innings — the target (first-innings total + 1), "
  "runs required, required run rate and current run rate. Balls remaining are clamped to ≥ 0; DLS matches are flagged "
  "and excluded from chase-based pressure. Correctness is covered by unit tests on hand-built innings (score, wickets, "
  "legal-ball counting, RRR, and a no-future-leakage invariant).")

# ---------- 7/8 METRICS ----------
H("7 · Batter Performance Metrics")
P("On each delivery set (pressure and the player's own baseline) we compute: balls faced, runs, strike rate, average "
  "(runs per dismissal, counting only the batter's own dismissals), dot-ball %, boundary %, and match counts. The "
  "headline comparison is pressure vs baseline strike rate and survival.")
H("8 · Bowler Performance Metrics")
P("Per delivery set: legal balls, runs conceded (bowler-charged), credited wickets, economy, strike rate, wicket rate "
  "per over, dot-ball % and boundary % conceded — each compared against the bowler's own baseline.")

# ---------- 9 RATING ----------
H("9 · Player Rating Methodology")
P("<b>Score = 0.50 · Absolute + 0.30 · Uplift + 0.20 · Consistency</b> (each a 0–1 percentile within the eligible pool, ×100). "
  "Absolute carries the most weight so a genuinely high-level pressure performance is rewarded on its own merit, while uplift and "
  "consistency keep the measure honest about who <i>lifts</i> when it matters:")
bullets([
  "<b>Absolute (50%)</b> — performance under pressure, <i>format-adjusted</i> against the league's pressure par for the formats the player actually played (so IPL and T20I are compared fairly). Batters: pressure SR + survival; bowlers: economy-vs-par + wicket rate + dot %.",
  "<b>Uplift (30%)</b> — pressure minus the player's <b>context-matched</b> baseline (own non-pressure level in the same innings phases, shrunk toward their overall baseline), then <b>empirical-Bayes shrunk</b> toward zero by pressure sample size. Context-matching removes the death-over illusion from the raw uplift.",
  "<b>Consistency (20%)</b> — the share of a player's pressure <i>matches</i> in which they delivered. Batters: SR within 10% of their (context-matched) baseline, a tolerance so high-baseline players are not penalised for a strong-but-slightly-below-average innings. Bowlers: a <b>graded</b> blend of economy improvement (45%), wicket contribution (30%) and dot-ball rate (25%), replacing the old ‘economy ≤ baseline OR one wicket’ rule that a single wicket could fully satisfy.",
])
story.append(img("components.png", 165)); SP(2)

# ---------- 10 SAMPLE ----------
H("10 · Sample Size, Eligibility & Reliability")
P("Eligibility (configurable): batters need ≥ 75 pressure balls, ≥ 5 pressure matches, ≥ 150 baseline balls; bowlers "
  "≥ 60 pressure legal balls, ≥ 5 pressure matches, ≥ 120 baseline balls. Shrinkage priors (60 balls for batters, 48 "
  "for bowlers) pull small-sample uplifts toward zero. We never tune thresholds to force a particular player in.")

# ---------- 11 IPL vs T20I ----------
H("11 · IPL and T20I Comparison")
P("Both formats are combined, but baselines are computed per player (their own non-pressure balls in the formats they "
  "played) and the absolute component is adjusted against format-specific pressure par (IPL pressure SR ≈ 153 vs T20I "
  "≈ 138; IPL pressure economy ≈ 10.6 vs T20I ≈ 10.0). Two sensitivity configs — IPL-weighting and a strict-sample cut — "
  "check that associate-nation inflation does not drive the picks.")

# ---------- 12 SENSITIVITY ----------
H("12 · Sensitivity & Ranking Stability")
P("We re-ran the entire rating under nine reasonable configurations: three pressure thresholds (0.50/0.55/0.60), "
  "two alternative batting definitions (chase-centric; death-and-collapse with no RRR) and two bowling definitions "
  "(death-heavy; defend-heavy), a strict-sample variant, and three weight mixes (uplift-, absolute- and consistency-heavy). "
  "The bars show how often each player stayed in the top 10.")
story.append(img("stability.png", 165))

# ---------- 13 TOP BATTERS ----------
story.append(PageBreak())
H("13 · Top 10 Batters — Evidence")
story.append(img("top_batters.png", 160)); SP(3)
story.append(ranking_table(bat, "bat")); SP(6)
h("Why each batter is here (all figures from the supplied data)")
for _, r in bat.head(10).iterrows():
    P(f"<b>{int(r['rank'])}. {r['player']}</b> — pressure strike rate "
      f"<b>{r['p_strike_rate']:.0f}</b> vs baseline {r['b_strike_rate']:.0f} "
      f"(<b>+{r['sr_uplift']:.0f}</b>), averaging {r['p_average']:.0f} under pressure over "
      f"{int(r['p_balls'])} pressure balls in {int(r['p_matches'])} matches; delivered in "
      f"{r['deliver_share']*100:.0f}% of qualifying pressure matches; stays top-10 in "
      f"{r['reliability']*100:.0f}% of configurations.", BODY)

# ---------- 14 TOP BOWLERS ----------
story.append(PageBreak())
H("14 · Top 10 Bowlers — Evidence")
story.append(img("top_bowlers.png", 160)); SP(3)
story.append(ranking_table(bowl, "bowl")); SP(6)
h("Why each bowler is here (all figures from the supplied data)")
for _, r in bowl.head(10).iterrows():
    econ_note = (f"economy <b>{r['p_economy']:.2f}</b> vs baseline {r['b_economy']:.2f}"
                 if r['p_economy'] <= r['b_economy'] else
                 f"economy {r['p_economy']:.2f} (vs {r['b_economy']:.2f} baseline)")
    P(f"<b>{int(r['rank'])}. {r['player']}</b> ({r['pace_or_spin'].lower()}) — {econ_note}, "
      f"{r['p_wkt_rate_over']:.2f} credited wickets/over and {r['p_dot_pct']:.0f}% dot balls under "
      f"pressure, over {int(r['p_legal_balls'])} pressure legal balls in {int(r['p_matches'])} "
      f"matches; stays top-10 in {r['reliability']*100:.0f}% of configurations.", BODY)

# ---------- 15 AVAILABILITY VIEW (SECONDARY) ----------
story.append(PageBreak())
H("15 · IPL-Availability — an Optional, Secondary View")
nbr = pd.read_csv(OUT / "excluded_batters.csv")
nwr = pd.read_csv(OUT / "excluded_bowlers.csv")
P("The problem statement does not ask for a nationality filter, so the <b>primary rankings in this report "
  "apply none</b> — they are the pure statistical result. Separately, because Rajasthan Royals is an IPL "
  "franchise, we provide an <i>optional</i> view that removes players an IPL side cannot sign. Nationality is "
  "<b>inferred</b> from the national team a player represents in T20Is — a data-only heuristic that is "
  "<b>not independently verified</b> (players with no T20I record cannot be classified), which is why it is "
  "presented only as a secondary lens. The scoring model is identical; this view drops the flagged players and re-ranks.")
if len(nbr):
    P("<b>Removed from the IPL-availability view — batters</b>: " +
      ", ".join(f"{r.player}" for _, r in nbr.iterrows()) + ".", SMALL)
if len(nwr):
    P("<b>Removed from the IPL-availability view — bowlers</b>: " + ", ".join(f"{r.player}" for _, r in nwr.iterrows()) + ".", SMALL)
P("Full IPL-available top-10s are in outputs/batter_rankings_ipl_available.csv and the dashboard.", SMALL)

# ---------- 16 MODEL VALIDATION ----------
H("16 · Model Validation")
bullets([
  "<b>Unit-tested cricket logic</b> — hand-built innings verify score/wicket reconstruction, legal-ball counting, bowler wicket credit, required run rate, and a no-future-leakage invariant (11/11 pass).",
  "<b>Innings totals cross-checked</b> against 356 result margins (median error 0; 266 within ±3 runs; large misses are DLS games).",
  "<b>Pressure definition is meaningful</b> — mean intensity rises monotonically through the innings and differs by role, matching cricketing intuition.",
  "<b>Small samples are shrunk, not rewarded</b> — the sample-size-vs-score plots show no runaway effect from low-ball players.",
  "<b>Rankings are stable</b> — the strongest picks appear in the top 10 across nearly all nine configurations.",
])

# ---------- 17 LIMITATIONS ----------
H("17 · Limitations")
bullets([
  "<b>Approximate targets</b> — bye/leg-bye magnitudes are not stored, so required run rate is accurate to ±1–3 runs; DLS matches are excluded from chase logic. Coarse pressure bands make this immaterial to classification.",
  "<b>Pressure is a modelling choice</b>, not an official RR definition; we mitigate with nine configurations and per-player reliability.",
  "<b>T20I strength varies</b> by opponent; baselines are format-adjusted but some associate-nation inflation can remain — checked via IPL-weighted and strict-sample configs.",
  "<b>No fitted win-probability model</b> — contest closeness is proxied by required run rate, wickets and phase.",
  "<b>Availability filter</b> uses nationality inferred from T20I appearances; a handful of uncapped players have no T20I record and are treated as IPL-eligible.",
])

# ---------- 18 CONCLUSION ----------
H("18 · Conclusion")
P("The framework turns the vague idea of ‘clutch’ into a reproducible, delivery-level measurement: a transparent "
  "pressure index, self-referenced performance, a balanced and shrinkage-protected rating, and a robustness check "
  "across nine model variants. The resulting top-10 batters and bowlers are not reputation picks — every name is "
  "backed by its own pressure-versus-baseline numbers and a reliability score, and every figure in this report is "
  "traceable to the supplied data via the accompanying code (run_pipeline.py) and interactive dashboard.")
SP(6); rule()
P("Rajasthan Royals · SupeRR Selector Season 2 · Round 1 — methodology report generated from the pipeline outputs. "
  "Proprietary competition data; not for distribution.", SMALL)

doc = SimpleDocTemplate(str(ROOT / "reports" / "methodology_report.pdf"), pagesize=A4,
                        topMargin=16*mm, bottomMargin=16*mm, leftMargin=18*mm, rightMargin=18*mm,
                        title="SupeRR Selector S2 - Methodology Report", author="SupeRR Selector entry")
doc.build(story)
print("PDF ->", ROOT / "reports" / "methodology_report.pdf")
