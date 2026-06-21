"""
23_ML_Alpha_Lab.py  ·  ML Alpha Signal Generation
Models: Random Forest · Gradient Boosting · Logistic Regression
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import confusion_matrix, classification_report
    _SKL_OK = True
except ImportError:
    _SKL_OK = False

from components.layout import (
    setup_page, section, next_step, plotly_config,
    _AMBER, _CYAN, _GREEN, _RED, _TEXT_SEC, _TEXT_MUT,
)
from core.state import bootstrap, set_ml_signal, set_signal

# ── Page init ─────────────────────────────────────────────────────────────────
setup_page(
    "ML Alpha Lab",
    "Machine-learning signal generation: Random Forest · Gradient Boosting · Logistic Regression",
    "🤖",
)
bootstrap()

if not _SKL_OK:
    st.error(
        "scikit-learn is not installed. Run `pip install scikit-learn` and restart the app.",
        icon="⚠️",
    )
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ ML Alpha Lab")
    ticker   = st.text_input("Ticker", value="AAPL", key="ml_ticker").upper().strip()
    model_choice = st.selectbox(
        "Model",
        ["Random Forest", "Gradient Boosting", "Logistic Regression"],
        key="ml_model",
    )
    lookback = st.slider("Training Lookback (years)", 1, 5, 3, key="ml_lb")
    n_splits = st.slider("Walk-Forward Folds", 2, 6, 3, key="ml_folds")
    horizon  = st.selectbox("Signal Horizon", [1, 3, 5, 10], index=1, key="ml_hor",
                             format_func=lambda x: f"{x}-day forward return")
    threshold = st.slider("Threshold (buy/sell)", 0.001, 0.03, 0.01, 0.001,
                           format="%.3f", key="ml_thr")
    with st.expander("RF / GBM Hyperparams"):
        n_estimators = st.slider("n_estimators",  50, 400, 150, key="ml_n_est")
        max_depth    = st.slider("max_depth",       2, 12,    5, key="ml_depth")
        learning_rate = st.slider("learning_rate (GBM)", 0.01, 0.5, 0.1, key="ml_lr")
    run_btn = st.button("▶ Train & Score", type="primary", use_container_width=True)

# ── Feature engineering ───────────────────────────────────────────────────────
def _build_features(df: pd.DataFrame, horizon: int, thr: float) -> tuple[pd.DataFrame, pd.Series]:
    c = df["Close"].copy()
    feat = pd.DataFrame(index=c.index)

    # Price-based
    for w in [5, 10, 20, 60]:
        feat[f"ret_{w}d"]  = c.pct_change(w)
        feat[f"ma_{w}d"]   = c.rolling(w).mean() / c - 1

    # Volatility
    ret = c.pct_change()
    for w in [10, 20]:
        feat[f"vol_{w}d"]  = ret.rolling(w).std() * np.sqrt(252)

    # RSI
    delta = c.diff()
    up    = delta.clip(lower=0)
    dn    = (-delta).clip(lower=0)
    rs    = up.rolling(14).mean() / (dn.rolling(14).mean() + 1e-9)
    feat["rsi_14"] = 100 - 100 / (1 + rs)

    # MACD
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    feat["macd"]        = (ema12 - ema26) / c
    feat["macd_signal"] = feat["macd"].ewm(span=9, adjust=False).mean()
    feat["macd_hist"]   = feat["macd"] - feat["macd_signal"]

    # Bollinger bands
    ma20  = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    feat["bb_pct"] = (c - ma20) / (2 * std20 + 1e-9)

    # Volume features (if available)
    if "Volume" in df.columns:
        v = df["Volume"]
        feat["vol_ratio_20"] = v / v.rolling(20).mean().replace(0, 1)
    else:
        feat["vol_ratio_20"] = 1.0

    # Label: future return > +thr → BUY (1), < -thr → SELL (-1), else HOLD (0)
    fwd = c.pct_change(horizon).shift(-horizon)
    label = pd.Series(0, index=fwd.index)
    label[fwd >  thr] =  1
    label[fwd < -thr] = -1

    feat = feat.dropna()
    common = feat.index.intersection(label.dropna().index)
    return feat.loc[common], label.loc[common]


@st.cache_data(ttl=3600, show_spinner=False)
def _load_ohlcv(ticker: str, years: int) -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(days=365 * years + 90)
    try:
        df = yf.download(
            ticker, start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True, progress=False,
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.ffill().dropna()
    except Exception:
        return pd.DataFrame()


def _get_model(choice: str, n_est: int, depth: int, lr: float):
    if choice == "Random Forest":
        return RandomForestClassifier(
            n_estimators=n_est, max_depth=depth, random_state=42,
            class_weight="balanced", n_jobs=-1,
        )
    elif choice == "Gradient Boosting":
        return GradientBoostingClassifier(
            n_estimators=n_est, max_depth=depth, learning_rate=lr, random_state=42,
        )
    else:
        return LogisticRegression(max_iter=1000, class_weight="balanced", C=0.5)


# ── Placeholder ───────────────────────────────────────────────────────────────
if not run_btn and "ml_results" not in st.session_state:
    st.markdown(
        f"""<div style="background:rgba(6,182,212,0.06);border:1px solid rgba(6,182,212,0.18);
        border-left:4px solid {_CYAN};border-radius:8px;padding:20px 24px;
        font-family:Inter,sans-serif;color:{_TEXT_SEC};line-height:1.7;">
        <b style="color:{_CYAN};">How to use this module</b><br>
        1. Enter a ticker and configure the model in the sidebar.<br>
        2. Set the signal horizon (how many days forward the label is computed) and the
           buy/sell threshold (minimum return to classify as a directional move).<br>
        3. Press <b>▶ Train & Score</b>.<br><br>
        The lab uses walk-forward cross-validation so there is no look-ahead bias.
        Signals and confidence scores are written to shared platform state.
        </div>""",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Train ─────────────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner(f"Downloading {ticker} OHLCV — {lookback}yr…"):
        df = _load_ohlcv(ticker, lookback)

    if df.empty or "Close" not in df.columns:
        st.error(f"No data for {ticker}. Check the ticker and try again.")
        st.stop()

    with st.spinner("Engineering features…"):
        X, y = _build_features(df, horizon, threshold)

    if len(X) < 120:
        st.error("Not enough data to train (need ≥ 120 rows after feature construction). Try a longer lookback or different ticker.")
        st.stop()

    model  = _get_model(model_choice, n_estimators, max_depth, learning_rate)
    scaler = StandardScaler()
    tscv   = TimeSeriesSplit(n_splits=n_splits)

    all_y_true, all_y_pred, all_proba = [], [], []
    fold_scores = []

    prog = st.progress(0, text="Walk-forward training…")
    X_arr = X.values
    y_arr = y.values

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X_arr)):
        X_tr, X_te = X_arr[train_idx], X_arr[test_idx]
        y_tr, y_te = y_arr[train_idx], y_arr[test_idx]
        X_tr_s = scaler.fit_transform(X_tr)
        X_te_s = scaler.transform(X_te)
        model.fit(X_tr_s, y_tr)
        y_pred = model.predict(X_te_s)
        all_y_true.extend(y_te.tolist())
        all_y_pred.extend(y_pred.tolist())
        if hasattr(model, "predict_proba"):
            all_proba.extend(model.predict_proba(X_te_s).max(axis=1).tolist())
        fold_acc = (y_pred == y_te).mean()
        fold_scores.append(fold_acc)
        prog.progress((fold + 1) / n_splits, text=f"Fold {fold+1}/{n_splits} accuracy: {fold_acc:.2%}")

    prog.empty()

    # Final fit on all data → predict on last available window
    X_s = scaler.fit_transform(X_arr)
    model.fit(X_s, y_arr)
    last_feats = X_s[-1:].copy()
    final_pred  = model.predict(last_feats)[0]
    final_proba = model.predict_proba(last_feats)[0] if hasattr(model, "predict_proba") else None

    label_map  = {1: "BUY", 0: "HOLD", -1: "SELL"}
    signal_str = label_map.get(int(final_pred), "HOLD")
    confidence = float(final_proba.max()) if final_proba is not None else float((np.array(all_y_true) == np.array(all_y_pred)).mean())

    set_ml_signal(ticker, signal_str, confidence)
    set_signal(ticker, signal_str, confidence, f"ML/{model_choice[:2]}")

    report = classification_report(all_y_true, all_y_pred, labels=[-1, 0, 1],
                                   target_names=["SELL","HOLD","BUY"], zero_division=0, output_dict=True)
    cm     = confusion_matrix(all_y_true, all_y_pred, labels=[-1, 0, 1])

    # Feature importance (RF/GBM) or coefficients (LR)
    if hasattr(model, "feature_importances_"):
        fi = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    elif hasattr(model, "coef_"):
        coef = np.abs(model.coef_).mean(axis=0)
        fi   = pd.Series(coef, index=X.columns).sort_values(ascending=False)
    else:
        fi = pd.Series(0.0, index=X.columns)

    st.session_state["ml_results"] = {
        "ticker":       ticker,
        "model_choice": model_choice,
        "signal":       signal_str,
        "confidence":   confidence,
        "fold_scores":  fold_scores,
        "report":       report,
        "cm":           cm,
        "fi":           fi,
        "y_true":       all_y_true,
        "y_pred":       all_y_pred,
        "proba":        all_proba,
        "final_proba":  final_proba,
        "X_cols":       X.columns.tolist(),
        "horizon":      horizon,
        "threshold":    threshold,
    }
    st.success(f"✓ {model_choice} trained on {len(X_arr)} samples across {n_splits} folds.")

# ── Results ───────────────────────────────────────────────────────────────────
if "ml_results" not in st.session_state:
    st.stop()

res   = st.session_state["ml_results"]
sig   = res["signal"]
conf  = res["confidence"]
fold_scores = res["fold_scores"]
report      = res["report"]
cm          = res["cm"]
fi          = res["fi"]

sig_color = {
    "BUY":  _GREEN,
    "SELL": _RED,
    "HOLD": _AMBER,
}.get(sig, _TEXT_SEC)

# ── Current signal hero ───────────────────────────────────────────────────────
section("Current ML Signal")

col_s, col_c, col_f, col_acc, col_h = st.columns([1.6, 1.2, 1.2, 1.2, 1.2])
col_s.markdown(
    f"""<div style="padding:16px;border-radius:10px;background:rgba(0,0,0,0.2);
    border:2px solid {sig_color};text-align:center;">
    <div style="font-size:0.62rem;font-family:'JetBrains Mono',monospace;
        color:{_TEXT_MUT};text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;">Signal</div>
    <div style="font-size:2rem;font-weight:900;font-family:'JetBrains Mono',monospace;
        color:{sig_color};">{sig}</div>
    </div>""",
    unsafe_allow_html=True,
)
col_c.metric("Confidence",      f"{conf:.2%}")
col_f.metric("Avg Fold Acc",    f"{np.mean(fold_scores):.2%}")
col_acc.metric("Horizon",        f"{res['horizon']}d")
col_h.metric("Threshold",        f"±{res['threshold']:.1%}")

# Per-class report
section("Classification Report", "Walk-forward cross-validation results (no look-ahead bias)")
rep_rows = []
for label, name in [("SELL","SELL"),("HOLD","HOLD"),("BUY","BUY")]:
    row = report.get(name, {})
    rep_rows.append({
        "Class":     name,
        "Precision": f"{row.get('precision',0):.3f}",
        "Recall":    f"{row.get('recall',0):.3f}",
        "F1-Score":  f"{row.get('f1-score',0):.3f}",
        "Support":   int(row.get("support", 0)),
    })
st.dataframe(pd.DataFrame(rep_rows).set_index("Class"), use_container_width=True)

# ── Confusion matrix ──────────────────────────────────────────────────────────
section("Confusion Matrix")
labels = ["SELL", "HOLD", "BUY"]
cm_pct = cm.astype(float) / (cm.sum(axis=1, keepdims=True) + 1e-9)
text   = [[f"{cm[i,j]}<br>({cm_pct[i,j]:.0%})" for j in range(3)] for i in range(3)]

fig_cm = go.Figure(go.Heatmap(
    z=cm_pct,
    x=labels,
    y=labels,
    colorscale=[[0,"#0F172A"],[0.5,"#1E3A5F"],[1,_CYAN]],
    showscale=False,
    text=text,
    texttemplate="%{text}",
    textfont={"size": 11, "family": "JetBrains Mono, monospace", "color": "#E2E8F0"},
))
fig_cm.update_layout(
    **plotly_config(
        height=300, margin=dict(l=60, r=20, t=20, b=50),
        xaxis=dict(title="Predicted", tickfont=dict(family="JetBrains Mono", size=11)),
        yaxis=dict(title="Actual",    tickfont=dict(family="JetBrains Mono", size=11),
                   autorange="reversed"),
    ),
)
st.plotly_chart(fig_cm, use_container_width=True)

# ── Feature importance ────────────────────────────────────────────────────────
section("Feature Importance / Coefficient Magnitude", "Top 15 features by importance")
top_fi = fi.head(15).sort_values(ascending=True)
colors = [_AMBER if v >= top_fi.quantile(0.7) else _CYAN for v in top_fi.values]

fig_fi = go.Figure(go.Bar(
    x=top_fi.values.tolist(),
    y=top_fi.index.tolist(),
    orientation="h",
    marker=dict(color=colors, line=dict(width=0)),
    text=[f"{v:.4f}" for v in top_fi.values],
    textposition="outside",
    textfont=dict(family="JetBrains Mono, monospace", size=9, color="#E2E8F0"),
))
fig_fi.update_layout(
    **plotly_config(
        height=400, margin=dict(l=110, r=20, t=10, b=40),
        yaxis=dict(tickfont=dict(family="JetBrains Mono", size=9)),
    ),
    xaxis_title="Importance",
)
st.plotly_chart(fig_fi, use_container_width=True)

# ── Fold accuracy chart ───────────────────────────────────────────────────────
section("Walk-Forward Fold Accuracy")
fig_fold = go.Figure()
fig_fold.add_trace(go.Bar(
    x=[f"Fold {i+1}" for i in range(len(fold_scores))],
    y=fold_scores,
    marker_color=[_GREEN if s >= 0.5 else _RED for s in fold_scores],
    text=[f"{s:.2%}" for s in fold_scores],
    textposition="outside",
    textfont=dict(family="JetBrains Mono, monospace", size=10, color="#E2E8F0"),
))
fig_fold.add_hline(y=0.5, line_dash="dot", line_color=_AMBER,
                   annotation_text="Random baseline 50%", annotation_font_color=_AMBER)
fig_fold.update_layout(
    **plotly_config(
        height=280, margin=dict(l=0, r=0, t=20, b=40),
        yaxis=dict(range=[0, 1.1], title="Accuracy"),
    ),
    bargap=0.25,
)
st.plotly_chart(fig_fold, use_container_width=True)

# ── Final probability distribution ───────────────────────────────────────────
if res.get("final_proba") is not None:
    section("Latest Prediction Probability Distribution")
    fp = res["final_proba"]
    cls_labels = ["-1 SELL", "0 HOLD", "+1 BUY"] if len(fp) == 3 else [str(i) for i in range(len(fp))]
    bar_c = [_RED, _AMBER, _GREEN] if len(fp) == 3 else [_CYAN] * len(fp)
    fig_p = go.Figure(go.Bar(
        x=cls_labels, y=fp.tolist(),
        marker=dict(color=bar_c, line=dict(width=0)),
        text=[f"{v:.2%}" for v in fp],
        textposition="outside",
        textfont=dict(family="JetBrains Mono, monospace", size=11, color="#E2E8F0"),
    ))
    fig_p.update_layout(
        **plotly_config(
            height=260, margin=dict(l=0, r=0, t=10, b=40),
            yaxis=dict(range=[0, 1.2], title="Probability"),
        ),
    )
    st.plotly_chart(fig_p, use_container_width=True)

# ── Signal summary ────────────────────────────────────────────────────────────
section("Signal Summary")
st.info(
    f"**{res['ticker']}** — {res['model_choice']} predicts **{sig}** "
    f"(confidence {conf:.2%}) over a **{res['horizon']}-day horizon**. "
    f"This signal has been written to shared platform state and is visible in the Command Center.",
    icon="🤖",
)

next_step("Check News Sentiment for a fundamental overlay on this signal, or open Trading Sim to act on it.")
