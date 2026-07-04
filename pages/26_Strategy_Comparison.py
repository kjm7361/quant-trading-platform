"""
26_Strategy_Comparison.py
Side-by-side comparison of all saved strategies.

Loads metrics from storage/backtests/ (saved automatically by the Backtest page)
and renders a comparison table + bar charts + delete controls.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

from components.layout import (
    setup_page, section, plotly_config,
    _AMBER, _CYAN, _GREEN, _RED, _TEXT_SEC, _TEXT_MUT,
)
from core.state import bootstrap
from core.context import load_context

setup_page(
    "Strategy Comparison",
    "Side-by-side performance of all saved strategies — Sharpe, IC, drawdown, turnover, net cost.",
    "📊",
)
bootstrap()

# ── Storage paths ─────────────────────────────────────────────────────────────
STRAT_CSV = Path("storage/strategies/strategies.csv")
BT_DIR    = Path("storage/backtests")

# ── Load saved strategies ─────────────────────────────────────────────────────
if not STRAT_CSV.exists() or not BT_DIR.exists():
    st.warning("No saved strategies found. Run a backtest and save it first.", icon="⚠️")
    st.stop()

strats = pd.read_csv(STRAT_CSV)

if strats.empty:
    st.info("No saved strategies yet. Go to **Backtest** and click *Save Strategy*.")
    st.stop()

# ── Load latest backtest metrics per strategy ─────────────────────────────────
rows: list[dict] = []

for _, s in strats.iterrows():
    sid  = str(s.get("strategy_id", ""))
    name = str(s.get("name", sid[:8]))
    sigs = str(s.get("signals", ""))

    bt_files = sorted(BT_DIR.glob(f"{sid}_*.csv"), reverse=True)
    if not bt_files:
        continue

    bt = pd.read_csv(bt_files[0])
    if bt.empty:
        continue

    rec = bt.iloc[0].to_dict()

    sharpe      = float(rec.get("sharpe",       np.nan))
    max_dd      = float(rec.get("max_drawdown", np.nan))
    final_eq    = float(rec.get("final_equity", np.nan))
    avg_turn    = float(rec.get("avg_turnover", np.nan))
    cost_bps    = float(rec.get("cost_bps",     10.0))
    start       = str(rec.get("start", ""))
    end         = str(rec.get("end",   ""))

    # Approximate net Sharpe: every 10 bps of extra cost ≈ 0.05 Sharpe drag
    net_sharpe = sharpe - (cost_bps / 10.0) * 0.05 if not np.isnan(sharpe) else np.nan

    rows.append({
        "Strategy":           name,
        "Signals":            sigs,
        "Sharpe":             sharpe,
        "Net Sharpe (est.)":  net_sharpe,
        "Max DD":             max_dd,
        "Total Return":       final_eq - 1.0 if not np.isnan(final_eq) else np.nan,
        "Avg Turnover":       avg_turn,
        "Cost (bps)":         cost_bps,
        "Start":              start,
        "End":                end,
        "_id":                sid,
    })

if not rows:
    st.info("Strategies are saved but no backtest files found. Re-run and save a backtest.")
    st.stop()

df = pd.DataFrame(rows)

# ── Active context banner ─────────────────────────────────────────────────────
ctx = load_context()
if ctx and ctx.is_complete():
    ctx_row = {
        "Strategy":          f"[CURRENT] {ctx.strategy_name}",
        "Signals":           ", ".join(ctx.signals_used),
        "Sharpe":            ctx.sharpe or np.nan,
        "Net Sharpe (est.)": (ctx.sharpe or np.nan) - (ctx.cost_bps / 10) * 0.05,
        "Max DD":            ctx.max_drawdown or np.nan,
        "Total Return":      np.nan,
        "Avg Turnover":      ctx.avg_turnover or np.nan,
        "Cost (bps)":        ctx.cost_bps,
        "Start":             ctx.start_date,
        "End":               ctx.end_date,
        "_id":               "current",
    }
    df = pd.concat([pd.DataFrame([ctx_row]), df], ignore_index=True)
    st.info("Current session strategy is included at the top.", icon="📌")

# ── Comparison table ──────────────────────────────────────────────────────────
section("Comparison Table", "All saved strategies with their most recent backtest metrics.")

DISPLAY_COLS = [
    "Strategy", "Signals", "Sharpe", "Net Sharpe (est.)",
    "Max DD", "Total Return", "Avg Turnover", "Cost (bps)", "Start", "End",
]
show_cols = [c for c in DISPLAY_COLS if c in df.columns]

def _highlight_best(s: pd.Series) -> list[str]:
    styles = [""] * len(s)
    valid  = s.dropna()
    if valid.empty:
        return styles
    best_idx = valid.idxmax()
    styles[list(s.index).index(best_idx)] = "background-color: rgba(16,185,129,0.18); font-weight:700"
    return styles

def _highlight_worst(s: pd.Series) -> list[str]:
    styles = [""] * len(s)
    valid  = s.dropna()
    if valid.empty:
        return styles
    worst_idx = valid.idxmin()
    styles[list(s.index).index(worst_idx)] = "background-color: rgba(239,68,68,0.18)"
    return styles

styled = (
    df[show_cols]
    .style
    .apply(_highlight_best,  subset=["Sharpe", "Net Sharpe (est.)", "Total Return"], axis=0)
    .apply(_highlight_worst, subset=["Max DD", "Avg Turnover"], axis=0)
    .format({
        "Sharpe":            "{:.2f}",
        "Net Sharpe (est.)": "{:.2f}",
        "Max DD":            lambda v: f"{v:.2%}" if not pd.isna(v) else "—",
        "Total Return":      lambda v: f"{v:.2%}" if not pd.isna(v) else "—",
        "Avg Turnover":      lambda v: f"{v:.4f}" if not pd.isna(v) else "—",
        "Cost (bps)":        lambda v: f"{v:.0f}" if not pd.isna(v) else "—",
    }, na_rep="—")
)
st.dataframe(styled, use_container_width=True, height=300)

st.divider()

# ── Visual comparison ─────────────────────────────────────────────────────────
section("Visual Comparison", "Bar charts across key metrics — green highlights the best value.")

METRICS = ["Sharpe", "Net Sharpe (est.)", "Max DD", "Avg Turnover"]
avail   = [m for m in METRICS if m in df.columns]

cols_per_row = 2
chart_cols = st.columns(cols_per_row)

for i, metric in enumerate(avail):
    with chart_cols[i % cols_per_row]:
        vals = df[metric].fillna(0)

        if metric == "Max DD":
            colors = [_RED if v < 0 else "#475569" for v in vals]
        else:
            max_v = vals.max()
            colors = [_GREEN if v == max_v else _AMBER for v in vals]

        fig = go.Figure(go.Bar(
            x=df["Strategy"].tolist(),
            y=vals.tolist(),
            marker_color=colors,
            text=[f"{v:.2f}" if metric not in ("Max DD", "Total Return")
                  else f"{v:.1%}" for v in vals],
            textposition="outside",
        ))
        fig.update_layout(
            title=metric,
            xaxis_title="Strategy",
            yaxis_title=metric,
            **plotly_config(),
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Cost vs Sharpe scatter ────────────────────────────────────────────────────
section("Cost vs Sharpe Trade-off", "Strategies in the top-left are best: high Sharpe at low cost.")

plot_df = df.dropna(subset=["Cost (bps)", "Sharpe"])
if len(plot_df) >= 2:
    fig_sc = go.Figure()
    for _, row in plot_df.iterrows():
        fig_sc.add_trace(go.Scatter(
            x=[row["Cost (bps)"]],
            y=[row["Sharpe"]],
            mode="markers+text",
            name=str(row["Strategy"]),
            text=[str(row["Strategy"])],
            textposition="top center",
            marker=dict(size=12, color=_AMBER if "[CURRENT]" in str(row["Strategy"]) else _CYAN),
        ))
    fig_sc.update_layout(
        title="Cost (bps) vs Sharpe Ratio",
        xaxis_title="Transaction Cost (bps)",
        yaxis_title="Sharpe Ratio",
        showlegend=False,
        **plotly_config(),
    )
    st.plotly_chart(fig_sc, use_container_width=True)
else:
    st.caption("Need at least 2 strategies to plot the scatter.")

st.divider()

# ── Delete strategies ─────────────────────────────────────────────────────────
section("Manage Strategies", "Remove strategies from the store (irreversible).")

saved_only = df[df["_id"] != "current"]
to_delete  = st.multiselect(
    "Select strategies to delete",
    options=saved_only["Strategy"].tolist(),
    default=[],
)

if to_delete:
    if st.button("🗑️ Delete Selected", type="secondary"):
        ids_to_del = saved_only.loc[
            saved_only["Strategy"].isin(to_delete), "_id"
        ].tolist()

        full = pd.read_csv(STRAT_CSV)
        full = full[~full["strategy_id"].isin(ids_to_del)]
        full.to_csv(STRAT_CSV, index=False)

        for sid in ids_to_del:
            for f in BT_DIR.glob(f"{sid}_*.csv"):
                f.unlink(missing_ok=True)

        st.success(f"Deleted {len(ids_to_del)} strategy/strategies.")
        st.rerun()
else:
    st.caption("Select strategies above to enable deletion.")
