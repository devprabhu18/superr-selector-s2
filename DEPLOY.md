# Deploying the dashboard (free) — Streamlit Community Cloud

The full 7-page dashboard runs from `app.py` and needs only ~4.6 MB of data
(the derived `deliveries_state.parquet`, two lookup CSVs, and the `outputs/` CSVs).
That fits the free tier easily. The `.gitignore` already excludes the 41 MB raw
`ball_by_ball.csv` (the dashboard doesn't use it) and RR's problem-statement PDF.

## What gets published
- Live app URL (public, e.g. `https://your-name-superr.streamlit.app`) — anyone with the link can view it.
- Source + the 4.6 MB of derived data.

If you'd rather the **raw files not be downloadable from GitHub**, make the GitHub
repo **private** — Streamlit Community Cloud can still deploy a private repo, and the
app URL stays public. (Recommended.)

## Steps

1. **Create a GitHub repo** (private recommended), e.g. `superr-selector-s2`.

2. **Push this project:**
   ```bash
   cd /Users/I578485/Downloads/superr_pressure_dashboard
   git init
   git add .
   git status                 # confirm NO ball_by_ball.csv and NO *.pdf from the data pack
   git commit -m "SupeRR Selector S2 — pressure analytics dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-username>/superr-selector-s2.git
   git push -u origin main
   ```
   Check `git status` output before committing — the data-pack PDF and the 41 MB
   CSV should be ignored.

3. **Deploy on Streamlit Community Cloud:**
   - Go to <https://share.streamlit.io> and sign in with GitHub.
   - Click **New app** → **Deploy a public/private app from GitHub**.
   - Repository: `<your-username>/superr-selector-s2`
   - Branch: `main`
   - **Main file path: `app.py`**
   - Click **Deploy**. First build takes ~2-3 min (installs `requirements.txt`).

4. **Copy the app URL** it gives you (e.g. `https://superr-selector-s2.streamlit.app`)
   and paste it into the methodology Word document (there's a placeholder marked for it).

## If the build fails
- "No module named pyarrow" → make sure `requirements.txt` includes `pyarrow` (it does now).
- App can't find data → confirm `data/processed/deliveries_state.parquet`,
  `6af3166e7b922_data_pack/teams.csv`, `6af3166e7b922_data_pack/playing_eleven.csv`
  and `outputs/*.csv` were committed (they are not git-ignored).

## Alternative free hosts
- **Hugging Face Spaces** (Streamlit SDK) — same files; can be set Private.
- **Render / Railway** free web service — start command `streamlit run app.py --server.port $PORT`.
