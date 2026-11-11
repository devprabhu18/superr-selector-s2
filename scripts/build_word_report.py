"""Generate the methodology report as a Microsoft Word (.docx) document.

Self-contained: regenerates the print figures from the CURRENT pipeline outputs
(so they reflect the latest rankings) and builds a polished Word document that
covers the full methodology, the factors chosen for batters and bowlers, the
ranking tables, embedded charts, validation and limitations.

Run: python -I scripts/build_word_report.py
Reads outputs/*.csv + data/processed/deliveries_state.parquet; writes
reports/methodology_report.docx (and refreshes reports/figures/*.png).

Set DASHBOARD_URL below to your deployed Streamlit link (see DEPLOY.md). If left
blank, a clearly-marked placeholder is written instead.
"""
import re
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ======== paste your deployed dashboard URL here (see DEPLOY.md) ========
DASHBOARD_URL = ""   # e.g. "https://superr-selector-s2.streamlit.app"
# ========================================================================

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# ---- colours ----
NAVY = RGBColor(0x14, 0x1B, 0x2D)
PINK = RGBColor(0xE0, 0x35, 0x6F)
BLUE = RGBColor(0x2E, 0x7D, 0xD1)
INK = RGBColor(0x1B, 0x22, 0x30)
MUTE = RGBColor(0x5B, 0x64, 0x72)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# ---- matplotlib palette (print-friendly, white bg) ----
mNAVY = "#141B2D"; mPINK = "#E0356F"; mBLUE = "#2E7DD1"; mORANGE = "#C2691A"
mINK = "#1b2230"; mMUTE = "#6b7688"; mGRID = "#dfe3ea"
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "font.size": 11,
    "axes.edgecolor": mGRID, "axes.labelcolor": mINK, "text.color": mINK,
    "xtick.color": mMUTE, "ytick.color": mMUTE, "axes.grid": True,
    "grid.color": mGRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "font.family": "sans-serif", "savefig.dpi": 150, "savefig.bbox": "tight",
})

bat = pd.read_csv(OUT / "batter_rankings.csv")
bowl = pd.read_csv(OUT / "bowler_rankings.csv")
bs = pd.read_csv(OUT / "batter_stability.csv")
ws = pd.read_csv(OUT / "bowler_stability.csv")
d = pd.read_parquet(PROC / "deliveries_state.parquet")


# ============================ FIGURES (refresh) ============================
def fig_pressure_curve():
    g = d.groupby("overid")[["bat_pressure", "bowl_pressure"]].mean().reset_index()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.axvspan(0.5, 6.5, color="#149184", alpha=0.07)
    ax.axvspan(15.5, 20.5, color=mPINK, alpha=0.07)
    ax.plot(g.overid, g.bat_pressure, "-o", color=mPINK, lw=2.2, ms=5, label="Batting pressure")
    ax.plot(g.overid, g.bowl_pressure, "-o", color=mBLUE, lw=2.2, ms=5, label="Bowling pressure")
    ax.set_xlabel("Over"); ax.set_ylabel("Mean pressure intensity (0–1)")
    ax.set_xticks(range(2, 21, 2)); ax.legend(frameon=False, loc="upper left")
    ax.text(3.2, 0.03, "Powerplay", color=mMUTE, fontsize=9)
    ax.text(17.3, 0.03, "Death", color=mMUTE, fontsize=9)
    fig.savefig(FIG / "pressure_curve.png"); plt.close(fig)


def fig_top_bat():
    t = bat.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(t))
    ax.barh(y - 0.2, t.b_strike_rate, 0.4, color=mBLUE, label="Baseline SR")
    ax.barh(y + 0.2, t.p_strike_rate, 0.4, color=mPINK, label="Pressure SR")
    ax.set_yticks(y); ax.set_yticklabels(t.player)
    ax.set_xlabel("Strike rate"); ax.legend(frameon=False, loc="lower right")
    for yi, p in enumerate(t.p_strike_rate):
        ax.text(p + 2, yi + 0.2, f"{p:.0f}", va="center", fontsize=8, color=mINK)
    ax.set_title("Top 10 batters — strike rate under pressure vs baseline", color=mINK, loc="left")
    fig.savefig(FIG / "top_batters.png"); plt.close(fig)


def fig_top_bowl():
    t = bowl.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(t))
    ax.barh(y - 0.2, t.b_economy, 0.4, color=mBLUE, label="Baseline economy")
    ax.barh(y + 0.2, t.p_economy, 0.4, color=mPINK, label="Pressure economy")
    ax.set_yticks(y); ax.set_yticklabels(t.player)
    ax.set_xlabel("Economy (runs/over) — lower is better"); ax.legend(frameon=False, loc="lower right")
    ax.set_title("Top 10 bowlers — economy under pressure vs baseline", color=mINK, loc="left")
    fig.savefig(FIG / "top_bowlers.png"); plt.close(fig)


def fig_stability():
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.4))
    for ax, df, title in [(axes[0], bs, "Batters"), (axes[1], ws, "Bowlers")]:
        s = df[df.top10_configs > 0].sort_values("top10_configs").tail(14)
        colors = [mPINK if v == 9 else mBLUE if v >= 6 else mORANGE for v in s.top10_configs]
        ax.barh(np.arange(len(s)), s.top10_configs, color=colors)
        ax.set_yticks(np.arange(len(s))); ax.set_yticklabels(s.player, fontsize=8)
        ax.set_xlim(0, 10); ax.set_xlabel("configs in top 10 (of 9)")
        ax.set_title(title, color=mINK, loc="left")
    fig.suptitle("Ranking stability across 9 model configurations", color=mINK, x=0.1, ha="left")
    fig.savefig(FIG / "stability.png"); plt.close(fig)


def fig_components():
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.2))
    W = {"abs_component": ("Absolute", mPINK, 0.40), "uplift_component": ("Uplift", mBLUE, 0.35),
         "consistency_component": ("Consistency", mORANGE, 0.25)}
    for ax, df, title in [(axes[0], bat.head(10), "Batters"), (axes[1], bowl.head(10), "Bowlers")]:
        t = df.iloc[::-1]; y = np.arange(len(t)); left = np.zeros(len(t))
        for col, (name, color, w) in W.items():
            vals = (t[col] * w * 100).values
            ax.barh(y, vals, left=left, color=color, label=name)
            left += vals
        ax.set_yticks(y); ax.set_yticklabels(t.player, fontsize=8)
        ax.set_xlabel("weighted score contribution"); ax.set_title(title, color=mINK, loc="left")
    axes[1].legend(frameon=False, loc="lower right", fontsize=8)
    fig.suptitle("Score composition: Absolute / Uplift / Consistency", color=mINK, x=0.1, ha="left")
    fig.savefig(FIG / "components.png"); plt.close(fig)


for f in [fig_pressure_curve, fig_top_bat, fig_top_bowl, fig_stability, fig_components]:
    f()
print("figures refreshed ->", FIG)


# ============================ WORD HELPERS ============================
doc = Document()
# base style
normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(10.5)
normal.font.color.rgb = INK

_TOKEN = re.compile(r"(<b>.*?</b>|<i>.*?</i>)")


def _rich(paragraph, text, base_size=10.5, color=INK):
    """Add text with simple <b>/<i> inline markup to a paragraph."""
    for part in _TOKEN.split(text):
        if not part:
            continue
        bold = ital = False
        if part.startswith("<b>"):
            part, bold = part[3:-4], True
        elif part.startswith("<i>"):
            part, ital = part[3:-4], True
        part = (part.replace("&nbsp;", " ").replace("&gt;", ">").replace("&lt;", "<")
                .replace("&amp;", "&"))
        r = paragraph.add_run(part)
        r.bold = bold; r.italic = ital
        r.font.size = Pt(base_size); r.font.color.rgb = color


def H1(text):
    p = doc.add_paragraph(); p.space_before = Pt(10)
    r = p.add_run(text); r.bold = True; r.font.size = Pt(15); r.font.color.rgb = NAVY
    p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(4)


def H2(text):
    p = doc.add_paragraph()
    r = p.add_run(text); r.bold = True; r.font.size = Pt(12); r.font.color.rgb = PINK
    p.paragraph_format.space_before = Pt(8); p.paragraph_format.space_after = Pt(2)


def body(text, size=10.5, color=INK):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    _rich(p, text, size, color)
    return p


def small(text):
    body(text, size=8.6, color=MUTE)


def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    _rich(p, text)


def bullets(items):
    for it in items:
        bullet(it)


def page_break():
    doc.add_page_break()


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def set_cell(cell, text, bold=False, color=INK, align="center", size=8):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = {"center": WD_ALIGN_PARAGRAPH.CENTER, "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
    p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
    r = p.add_run(str(text)); r.bold = bold; r.font.size = Pt(size); r.font.color.rgb = color


def add_figure(name, width_in=6.3):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(FIG / name), width=Inches(width_in))
    p.paragraph_format.space_after = Pt(6)


def ranking_table(df, kind):
    if kind == "bat":
        head = ["#", "Batter", "Score", "Rel.", "Pr. balls", "Pr. mts", "Pr. SR", "Base SR", "SR upl.", "Pr. avg"]
        rows = [[int(r["rank"]), r["player"], f"{r['score']:.1f}", f"{r['reliability']*100:.0f}%",
                 int(r["p_balls"]), int(r["p_matches"]), f"{r['p_strike_rate']:.0f}",
                 f"{r['b_strike_rate']:.0f}", f"+{r['sr_uplift']:.0f}", f"{r['p_average']:.0f}"]
                for _, r in df.head(10).iterrows()]
    else:
        head = ["#", "Bowler", "Type", "Score", "Rel.", "Pr. balls", "Pr. mts", "Pr. wkts",
                "Pr. econ", "Base econ", "Wkts/ov"]
        rows = [[int(r["rank"]), r["player"], r["pace_or_spin"], f"{r['score']:.1f}",
                 f"{r['reliability']*100:.0f}%", int(r["p_legal_balls"]), int(r["p_matches"]),
                 int(r["p_wickets"]), f"{r['p_economy']:.2f}", f"{r['b_economy']:.2f}",
                 f"{r['p_wkt_rate_over']:.2f}"]
                for _, r in df.head(10).iterrows()]
    ncol = len(head)
    table = doc.add_table(rows=1, cols=ncol)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, h in enumerate(head):
        c = table.rows[0].cells[i]
        set_cell(c, h, bold=True, color=WHITE, align="center", size=7.6)
        shade(c, "141B2D")
    for ri, row in enumerate(rows):
        cells = table.add_row().cells
        for i, val in enumerate(row):
            set_cell(cells[i], val, bold=(i == 1), align=("left" if i == 1 else "center"), size=7.8)
            if ri % 2 == 1:
                shade(cells[i], "F2F4F8")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ============================ DOCUMENT BODY ============================
# ---- Title ----
p = doc.add_paragraph()
r = p.add_run("RAJASTHAN ROYALS · SupeRR SELECTOR SEASON 2")
r.bold = True; r.font.size = Pt(11); r.font.color.rgb = PINK

p = doc.add_paragraph()
r = p.add_run("Identifying the Most Reliable Players Under Pressure")
r.bold = True; r.font.size = Pt(24); r.font.color.rgb = NAVY
p.paragraph_format.space_after = Pt(2)

p = doc.add_paragraph()
r = p.add_run("Round 1 — Methodology Report")
r.font.size = Pt(13); r.font.color.rgb = NAVY

body("A reproducible, delivery-level framework that measures how batters and bowlers perform in "
     "high-pressure situations relative to their own baseline, across IPL and T20I cricket (2022–2026). "
     "Every number in this report is traceable to the supplied data via the accompanying code "
     "(<b>run_pipeline.py</b>), an 11-test correctness suite, and an interactive dashboard.")

# ---- Dashboard link box ----
H2("Interactive Dashboard")
if DASHBOARD_URL.strip():
    body(f"A live, interactive version of this analysis — overview, batter & bowler analytics, "
         f"head-to-head pressure comparison, a player explorer, the final rankings and the full "
         f"model-validation evidence — is hosted here:")
    p = doc.add_paragraph()
    r = p.add_run(DASHBOARD_URL.strip())
    r.bold = True; r.font.size = Pt(12); r.font.color.rgb = BLUE
else:
    body("A live, interactive version of this analysis (7 pages: overview, batter & bowler analytics, "
         "head-to-head pressure comparison, player explorer, final rankings, and model validation) "
         "accompanies this report. <b>[ PASTE DEPLOYED DASHBOARD URL HERE — see DEPLOY.md ]</b>")
    small("To deploy for free: push the project to GitHub and connect it to Streamlit Community Cloud "
          "(main file app.py); then paste the resulting https://…streamlit.app link above.")

small(f"Eligible pool: {len(bat)} batters, {len(bowl)} bowlers  ·  {d.match_id.nunique()} matches  ·  "
      f"{len(d):,} deliveries analysed  ·  IPL + T20I combined, with format-adjusted baselines.")
page_break()

# ---- 1 Executive summary ----
H1("1 · Executive Summary")
body("We define <b>pressure</b> as a continuous, per-delivery intensity (0–1) built from the match "
     "situation <i>before</i> each ball is bowled — innings phase, wickets already lost, balls remaining "
     "and, in run-chases, the required run rate and how alive the contest is. Crucially we build "
     "<b>two separate, asymmetric models</b>: a batting team is under pressure in hard chases and at the "
     "death, whereas a bowling team is under pressure when batters are set and scoring freely. Every "
     "player is judged against a <b>context-matched baseline</b> — their own non-pressure level in the "
     "<i>same innings phases</i> — and scored on an <b>absolute-leaning blend</b>: 50% absolute pressure "
     "performance, 30% uplift versus baseline, 20% match-to-match consistency, with empirical-Bayes "
     "shrinkage so small samples cannot spike. Rankings are stress-tested across nine model "
     "configurations; the <b>reliability</b> column is the share in which a player stays in the top 10. "
     "The lists below are the <b>primary statistical result and apply no nationality filter</b>; an "
     "optional IPL-availability view is given separately in §15.")
H2("Top 10 Batters Under Pressure")
ranking_table(bat, "bat")
H2("Top 10 Bowlers Under Pressure")
ranking_table(bowl, "bowl")
small("Rel. = reliability (of 9 configs). Pr. = pressure. SR upl. = pressure SR minus own baseline SR. "
      "Wickets credited to the bowler only (run-outs excluded).")
page_break()

# ---- 2 Problem & approach ----
H1("2 · Problem Statement & Approach")
body("Round 1 asks us to build a data-driven system that measures how batters and bowlers perform in "
     "high-pressure situations compared with their usual level, and to rank the players who deliver most "
     "consistently. The definition of pressure is left to us. Our guiding principles were:")
bullets([
    "<b>Reliability over reputation.</b> Every pick is derived from the supplied ball-by-ball data; no player list is hard-coded.",
    "<b>Self-referenced.</b> A high pressure strike rate is only credited relative to that batter's own baseline — we reward players who <i>maintain or raise</i> their level when it matters.",
    "<b>No future leakage.</b> Pressure at a delivery uses only information available up to that ball; the match result is never used to label earlier deliveries.",
    "<b>Honest about the data.</b> Where a quantity (e.g. exact team totals) cannot be reconstructed reliably, we say so and avoid building on it.",
    "<b>Robustness first.</b> A single formula is not trusted; the answer must survive reasonable changes to thresholds, weights and the pressure definition itself.",
])

# ---- 3 Dataset ----
H1("3 · Dataset")
body(f"Seven supplied files. The core is <b>ball_by_ball.csv</b> ({len(d):,} main-innings deliveries after "
     "excluding 6 super-over innings), joined to match metadata (883 matches, 867 with ball data), "
     "competitions (141; 5 IPL seasons 2022–2026), teams, playing XIs and competition–team–player "
     "mappings. Coverage splits roughly evenly: ~397 T20 matches (371 IPL) and ~470 T20I. All joins are "
     "verified; the delivery key (match, innings, ball) is unique.")

# ---- 4 Data cleaning ----
H1("4 · Data Cleaning & the Extras Puzzle")
body("The single most important data-quality finding: <b>extras1_runs is not a number of runs — it is a "
     "category code</b>, one-to-one with extras_type (6 = legal ball, 2 = wide, 3 = leg-bye, 4 = bye, "
     "1 = no-ball, 5 = other, 7 = penalty). Summing it would be meaningless. We confirmed that <b>runs</b> "
     "is <b>runs off the bat</b> (every six has runs = 6, every four runs = 4, with zero contradictions). "
     "Therefore:")
bullets([
    "<b>Batting metrics are exact</b> — strike rate, boundary %, dot %, dismissals all come from reliable fields.",
    "<b>Bowler economy is reliable</b> — byes and leg-byes are not charged to the bowler, so a bowler's runs = off-bat + wides + no-balls (+ recorded extra runs).",
    "<b>Team totals / required run rate are approximate</b> — bye/leg-bye magnitudes beyond 1 are not stored. Validated against 356 result margins: median error 0, 266 within ±3 runs; the large misses are all DLS rain games, which we exclude from chase logic.",
    "<b>Bowler wickets</b> exclude run-outs, retired-out and obstruction (609 of 10,881); 10,272 are credited. <b>Legal balls</b> exclude wides, no-balls and the re-bowled ‘other’ extra. All aggregation keys on player_id, since some names map to two IDs.",
])

# ---- 5 Pressure definition (THE FACTORS) ----
H1("5 · Pressure Definition — the Factors We Chose")
body("Pressure is a weighted blend of normalised signals, each in [0,1], combined differently for batting "
     "and bowling. The chart below shows the mean intensity by over: batting pressure climbs steadily and "
     "jumps at the death; bowling pressure is flatter but peaks when batters attack — exactly the asymmetry "
     "we want.")
add_figure("pressure_curve.png", 6.2)
H2("Batting-pressure factors")
bullets([
    "<b>Innings phase</b> — death overs carry the highest stake, the powerplay the lowest.",
    "<b>Wickets already lost</b> — rebuilding after a collapse is higher pressure than batting with a full hand.",
    "<b>Required run rate</b> (chases) — a demanding chase is high pressure; but a <i>hopeless</i> chase (needing &gt;3 runs/ball with few resources) is dampened, since garbage-time hitting is not a fair clutch test.",
    "<b>Balls remaining</b> — pressure concentrates as the innings runs out.",
])
H2("Bowling-pressure factors")
bullets([
    "<b>Death overs</b>, where margins are smallest and every ball is decisive.",
    "<b>Batting momentum</b> — a high current run rate with wickets in hand means the bowler must stem the flow.",
    "<b>Defending a gettable chase</b> — when the batting side is cruising (low required rate), the bowler is under the most pressure to break through.",
])
body(f"A delivery is classified ‘pressure’ when its intensity ≥ 0.55 (configurable; swept in §12). This "
     f"yields {d.is_bat_pressure.mean():.0%} batting-pressure and {d.is_bowl_pressure.mean():.0%} "
     f"bowling-pressure deliveries.", size=8.6, color=MUTE)

# ---- 6 Match state ----
H1("6 · Match-State Reconstruction")
body("For every delivery we reconstruct the state before the ball, chronologically: score so far, wickets "
     "fallen, wickets in hand, legal balls bowled and remaining, and — in the second innings — the target "
     "(first-innings total + 1), runs required, required run rate and current run rate. Balls remaining are "
     "clamped to ≥ 0; DLS matches are flagged and excluded from chase-based pressure. Correctness is covered "
     "by unit tests on hand-built innings (score, wickets, legal-ball counting, RRR, and a no-future-leakage "
     "invariant) — 11/11 pass.")

# ---- 7/8 metrics ----
H1("7 · Batter Performance Metrics")
body("On each delivery set (pressure and the player's own baseline) we compute: balls faced, runs, strike "
     "rate, average (runs per dismissal, counting only the batter's own dismissals), dot-ball %, boundary % "
     "and match counts. The headline comparison is pressure vs baseline strike rate and survival.")
H1("8 · Bowler Performance Metrics")
body("Per delivery set: legal balls, runs conceded (bowler-charged), credited wickets, economy, strike rate, "
     "wicket rate per over, dot-ball % and boundary % conceded — each compared against the bowler's own baseline.")

H2("Context-matched baseline — controlling for innings-phase bias")
body("A subtle but important issue: pressure deliveries are heavily concentrated at the death (≈59% of "
     "batting-pressure balls) whereas a player's pooled non-pressure baseline is dominated by the powerplay "
     "and middle overs (death is only ≈4% of it). Because strike rate and economy are naturally higher at the "
     "death, a raw pressure-minus-baseline uplift partly measures the <i>phase</i>, not a pressure response. "
     "We therefore compare each player to their own non-pressure level <b>in the same phases</b>, reweighted to "
     "the phase mix of their pressure balls. Since death-over non-pressure samples are thin, each per-phase "
     "baseline is <b>shrunk toward the player's overall baseline</b>, trading phase-bias for a controlled, "
     "honest estimate rather than noise.")

# ---- 9 Rating ----
H1("9 · Player Rating — the Factors We Score")
body("<b>Score = 0.50 · Absolute + 0.30 · Uplift + 0.20 · Consistency</b> (each component a 0–1 percentile "
     "within the eligible pool, ×100). Absolute carries the most weight so that a genuinely high-level "
     "pressure performance is rewarded on its own merit — a clutch knock is a clutch knock — while uplift and "
     "consistency keep the measure honest about who <i>lifts</i> when it matters:")
bullets([
    "<b>Absolute (50%)</b> — performance under pressure, <i>format-adjusted</i> against the league's pressure par for the formats the player actually played (so IPL and T20I are compared fairly). Batters: pressure SR + survival; bowlers: economy-vs-par + wicket rate + dot %.",
    "<b>Uplift (30%)</b> — pressure minus the player's <b>context-matched</b> baseline (own non-pressure level in the same phases, shrunk toward their overall baseline), then <b>empirical-Bayes shrunk</b> toward zero by pressure sample size, so a player with 15 good balls cannot outrank one with 300.",
    "<b>Consistency (20%)</b> — the share of a player's pressure <i>matches</i> in which they delivered. Batters: strike rate within 10% of their (context-matched) baseline — a tolerance so high-baseline players are not punished for a strong-but-slightly-below-average innings. Bowlers: a <b>graded</b> blend of economy improvement (45%), wicket contribution (30%) and dot-ball rate (25%), replacing the old ‘economy ≤ baseline OR one wicket’ rule, which a single wicket could fully satisfy.",
])
add_figure("components.png", 6.4)

# ---- 10 sample ----
H1("10 · Sample Size, Eligibility & Reliability")
body("Eligibility (configurable): batters need ≥ 75 pressure balls, ≥ 5 pressure matches, ≥ 150 baseline "
     "balls; bowlers ≥ 60 pressure legal balls, ≥ 5 pressure matches, ≥ 120 baseline balls. Shrinkage priors "
     "(60 balls for batters, 48 for bowlers) pull small-sample uplifts toward zero. We never tune thresholds "
     "to force a particular player in.")

# ---- 11 IPL vs T20I ----
H1("11 · IPL and T20I Comparison")
body("Both formats are combined, but baselines are computed per player (their own non-pressure balls in the "
     "formats they played) and the absolute component is adjusted against format-specific pressure par (IPL "
     "pressure SR ≈ 153 vs T20I ≈ 138; IPL pressure economy ≈ 10.6 vs T20I ≈ 10.0). Two sensitivity configs — "
     "IPL-weighting and a strict-sample cut — check that associate-nation inflation does not drive the picks.")

# ---- 12 sensitivity ----
H1("12 · Sensitivity & Ranking Stability")
body("We re-ran the entire rating under nine reasonable configurations: three pressure thresholds "
     "(0.50/0.55/0.60), two alternative batting definitions (chase-centric; death-and-collapse with no RRR) "
     "and two bowling definitions (death-heavy; defend-heavy), a strict-sample variant, and three weight mixes "
     "(uplift-, absolute- and consistency-heavy). The context-matched baseline and the balanced bowling "
     "consistency are applied inside <i>every</i> configuration, so reliability reflects the final model. The "
     "bars show how often each player stayed in the top 10.")
add_figure("stability.png", 6.4)

# ---- 13 top batters ----
page_break()
H1("13 · Top 10 Batters — Evidence")
add_figure("top_batters.png", 6.1)
ranking_table(bat, "bat")
H2("Why each batter is here (all figures from the supplied data)")
for _, r in bat.head(10).iterrows():
    body(f"<b>{int(r['rank'])}. {r['player']}</b> — pressure strike rate <b>{r['p_strike_rate']:.0f}</b> "
         f"vs baseline {r['b_strike_rate']:.0f} (<b>+{r['sr_uplift']:.0f}</b>), averaging "
         f"{r['p_average']:.0f} under pressure over {int(r['p_balls'])} pressure balls in "
         f"{int(r['p_matches'])} matches; delivered in {r['deliver_share']*100:.0f}% of qualifying "
         f"pressure matches; stays top-10 in {r['reliability']*100:.0f}% of configurations.", size=9.6)

# ---- 14 top bowlers ----
page_break()
H1("14 · Top 10 Bowlers — Evidence")
add_figure("top_bowlers.png", 6.1)
ranking_table(bowl, "bowl")
H2("Why each bowler is here (all figures from the supplied data)")
for _, r in bowl.head(10).iterrows():
    econ_note = (f"economy <b>{r['p_economy']:.2f}</b> vs baseline {r['b_economy']:.2f}"
                 if r["p_economy"] <= r["b_economy"] else
                 f"economy {r['p_economy']:.2f} (vs {r['b_economy']:.2f} baseline)")
    body(f"<b>{int(r['rank'])}. {r['player']}</b> ({r['pace_or_spin'].lower()}) — {econ_note}, "
         f"{r['p_wkt_rate_over']:.2f} credited wickets/over and {r['p_dot_pct']:.0f}% dot balls under "
         f"pressure, over {int(r['p_legal_balls'])} pressure legal balls in {int(r['p_matches'])} "
         f"matches; stays top-10 in {r['reliability']*100:.0f}% of configurations.", size=9.6)

# ---- 15 availability view (secondary) ----
page_break()
H1("15 · IPL-Availability — an Optional, Secondary View")
nbr = pd.read_csv(OUT / "excluded_batters.csv")
nwr = pd.read_csv(OUT / "excluded_bowlers.csv")
body("The problem statement does not ask for a nationality filter, so the <b>primary rankings in this report "
     "apply none</b> — they are the pure statistical result. Separately, because Rajasthan Royals is an IPL "
     "franchise, we provide an <i>optional</i> view that removes players an IPL side cannot sign. Nationality "
     "is <b>inferred</b> from the national team a player represents in T20Is — a data-only heuristic that is "
     "<b>not independently verified</b> (players with no T20I record cannot be classified), which is why it is "
     "presented only as a secondary lens, never as the headline answer. The scoring model is identical; this "
     "view simply drops the flagged players and re-ranks.")
if len(nbr):
    small("Removed from the IPL-availability view — batters: " +
          ", ".join(str(r.player) for _, r in nbr.iterrows()) + ".")
if len(nwr):
    small("Removed from the IPL-availability view — bowlers: " +
          ", ".join(str(r.player) for _, r in nwr.iterrows()) + ".")
small("Full IPL-available top-10s are in outputs/batter_rankings_ipl_available.csv and the dashboard.")

# ---- 16 validation ----
H1("16 · Model Validation")
bullets([
    "<b>Unit-tested cricket logic</b> — hand-built innings verify score/wicket reconstruction, legal-ball counting, bowler wicket credit, required run rate, and a no-future-leakage invariant (11/11 pass).",
    "<b>Innings totals cross-checked</b> against 356 result margins (median error 0; 266 within ±3 runs; large misses are DLS games).",
    "<b>Pressure definition is meaningful</b> — mean intensity rises monotonically through the innings and differs by role, matching cricketing intuition.",
    "<b>Small samples are shrunk, not rewarded</b> — the sample-size-vs-score plots show no runaway effect from low-ball players.",
    "<b>Rankings are stable</b> — the strongest picks appear in the top 10 across nearly all nine configurations.",
])

# ---- 17 limitations ----
H1("17 · Limitations")
bullets([
    "<b>Approximate targets</b> — bye/leg-bye magnitudes are not stored, so required run rate is accurate to ±1–3 runs; DLS matches are excluded from chase logic. Coarse pressure bands make this immaterial to classification.",
    "<b>Pressure is a modelling choice</b>, not an official RR definition; we mitigate with nine configurations and per-player reliability.",
    "<b>T20I strength varies</b> by opponent; baselines are format-adjusted but some associate-nation inflation can remain — checked via IPL-weighted and strict-sample configs.",
    "<b>No fitted win-probability model</b> — contest closeness is proxied by required run rate, wickets and phase.",
    "<b>Availability filter</b> uses nationality inferred from T20I appearances; a handful of uncapped players have no T20I record and are treated as IPL-eligible.",
])

# ---- 18 conclusion ----
H1("18 · Conclusion")
body("The framework turns the vague idea of ‘clutch’ into a reproducible, delivery-level measurement: a "
     "transparent pressure index, self-referenced performance, a balanced and shrinkage-protected rating, "
     "and a robustness check across nine model variants. The resulting top-10 batters and bowlers are not "
     "reputation picks — every name is backed by its own pressure-versus-baseline numbers and a reliability "
     "score, and every figure in this report is traceable to the supplied data via the accompanying code "
     "(run_pipeline.py) and the interactive dashboard.")

out = ROOT / "reports" / "methodology_report.docx"
doc.save(str(out))
print("Word document ->", out)
