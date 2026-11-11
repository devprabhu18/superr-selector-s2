"""Player nationality & IPL-availability filter.

Nationality is inferred from the national team a player represents in T20Is
(reliable, from the data itself — not reputation). Players whose nationality is
in config.EXCLUDE_NATIONS (e.g. Pakistan) cannot be signed by an IPL franchise
and are removed from the FINAL ranked lists. Players with no T20I appearance
(uncapped IPL players) are treated as IPL-eligible.
"""
from __future__ import annotations
import pandas as pd
import config as C


def nationality_map() -> pd.DataFrame:
    """player_id -> nationality (national team in T20Is)."""
    pe = pd.read_csv(C.DATA_RAW / "playing_eleven.csv")
    m = pd.read_csv(C.DATA_RAW / "matches.csv")[["match_id", "comp_id"]]
    comps = pd.read_csv(C.DATA_RAW / "competitions.csv")[["comp_id", "match_format"]]
    teams = (pd.read_csv(C.DATA_RAW / "teams.csv")
             .drop_duplicates("team_id").set_index("team_id")["team_name"].to_dict())

    pe = pe.merge(m, on="match_id", how="left").merge(comps, on="comp_id", how="left")
    t20i = pe[pe["match_format"] == "T20I"]
    nat = (t20i.groupby("player_id")["team_id"]
           .agg(lambda s: s.mode().iat[0] if not s.mode().empty else None))
    out = nat.rename("team_id").reset_index()
    out["nationality"] = out["team_id"].map(teams)
    return out[["player_id", "nationality"]]


def attach_nationality(ranked: pd.DataFrame, id_col: str) -> pd.DataFrame:
    """Attach inferred nationality WITHOUT filtering (for the primary lists)."""
    nat = nationality_map().rename(columns={"player_id": id_col})
    return ranked.merge(nat, on=id_col, how="left")


def attach_and_filter(ranked: pd.DataFrame, id_col: str):
    """SECONDARY IPL-availability view: attach nationality, drop EXCLUDE_NATIONS,
    re-rank 1..N. Returns (ipl_available_ranked, removed_rows)."""
    r = ranked.copy()
    if "nationality" not in r.columns:
        nat = nationality_map().rename(columns={"player_id": id_col})
        r = r.merge(nat, on=id_col, how="left")
    r["ipl_ineligible"] = r["nationality"].isin(C.EXCLUDE_NATIONS)
    removed = r[r["ipl_ineligible"]].copy()
    keep = r[~r["ipl_ineligible"]].copy().sort_values("score", ascending=False)
    keep["rank"] = range(1, len(keep) + 1)
    return keep.reset_index(drop=True), removed.reset_index(drop=True)
