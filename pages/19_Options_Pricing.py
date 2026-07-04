import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from math import log, sqrt, exp
from scipy.stats import norm
from scipy.optimize import brentq

from components.layout import setup_page, section, next_step, plotly_config


# =============================
# Page setup
# =============================
setup_page(
    "Options Pricing + Greeks",
    "Price options using Black-Scholes, Monte Carlo simulation, binomial tree pricing, Greeks, payoff diagrams, and implied volatility.",
    "📐"
)


# =============================
# Black-Scholes helpers
# =============================
def black_scholes_price(S, K, T, r, sigma, option_type):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0

    d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)

    if option_type == "Call":
        return S * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)

    return K * exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def black_scholes_greeks(S, K, T, r, sigma, option_type):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {
            "Delta": 0.0,
            "Gamma": 0.0,
            "Vega": 0.0,
            "Theta": 0.0,
            "Rho": 0.0
        }

    d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)

    gamma = norm.pdf(d1) / (S * sigma * sqrt(T))
    vega = S * norm.pdf(d1) * sqrt(T) / 100

    if option_type == "Call":
        delta = norm.cdf(d1)
        theta = (
            -(S * norm.pdf(d1) * sigma) / (2 * sqrt(T))
            - r * K * exp(-r * T) * norm.cdf(d2)
        ) / 365
        rho = K * T * exp(-r * T) * norm.cdf(d2) / 100

    else:
        delta = norm.cdf(d1) - 1
        theta = (
            -(S * norm.pdf(d1) * sigma) / (2 * sqrt(T))
            + r * K * exp(-r * T) * norm.cdf(-d2)
        ) / 365
        rho = -K * T * exp(-r * T) * norm.cdf(-d2) / 100

    return {
        "Delta": float(delta),
        "Gamma": float(gamma),
        "Vega": float(vega),
        "Theta": float(theta),
        "Rho": float(rho)
    }


# =============================
# Monte Carlo pricing
# =============================
def monte_carlo_option_price(S, K, T, r, sigma, option_type, simulations, seed):
    np.random.seed(int(seed))

    z = np.random.standard_normal(int(simulations))

    ST = S * np.exp(
        (r - 0.5 * sigma ** 2) * T
        + sigma * sqrt(T) * z
    )

    if option_type == "Call":
        payoff = np.maximum(ST - K, 0)
    else:
        payoff = np.maximum(K - ST, 0)

    price = exp(-r * T) * np.mean(payoff)

    return float(price), ST, payoff


# =============================
# Binomial tree pricing
# =============================
def binomial_tree_price(S, K, T, r, sigma, option_type, steps):
    steps = int(steps)

    if steps <= 0:
        return 0.0

    dt = T / steps
    u = exp(sigma * sqrt(dt))
    d = 1 / u

    p = (exp(r * dt) - d) / (u - d)

    prices = np.zeros(steps + 1)

    i = 0
    while i <= steps:
        prices[i] = S * (u ** (steps - i)) * (d ** i)
        i += 1

    if option_type == "Call":
        values = np.maximum(prices - K, 0)
    else:
        values = np.maximum(K - prices, 0)

    step = steps - 1

    while step >= 0:
        j = 0
        while j <= step:
            values[j] = exp(-r * dt) * (
                p * values[j] + (1 - p) * values[j + 1]
            )
            j += 1

        step -= 1

    return float(values[0])


# =============================
# Implied volatility
# =============================
def implied_volatility(market_price, S, K, T, r, option_type):
    if market_price <= 0:
        return None

    def objective(vol):
        return black_scholes_price(S, K, T, r, vol, option_type) - market_price

    try:
        iv = brentq(objective, 0.0001, 5.0)
        return float(iv)
    except Exception:
        return None


# =============================
# Payoff
# =============================
def option_payoff_range(S, K, premium, option_type):
    prices = np.linspace(S * 0.5, S * 1.5, 200)

    if option_type == "Call":
        payoff = np.maximum(prices - K, 0) - premium
    else:
        payoff = np.maximum(K - prices, 0) - premium

    return pd.DataFrame({
        "Underlying Price": prices,
        "Profit / Loss": payoff
    })


# =============================
# Sidebar inputs
# =============================
st.sidebar.header("Option Inputs")

# Live spot price fetch
_opt_ticker = st.sidebar.text_input("Ticker for Live Spot", value="AAPL", key="opt_ticker")
if st.sidebar.button("Fetch Live Spot Price"):
    try:
        import yfinance as yf
        _spot = yf.Ticker(_opt_ticker.strip().upper()).fast_info.last_price
        if _spot is not None and _spot == _spot:
            st.session_state["opt_spot"] = float(_spot)
            st.sidebar.success(f"Fetched: ${_spot:,.2f}")
    except Exception:
        st.sidebar.warning("Fetch failed — enter price manually.")

option_type = st.sidebar.selectbox(
    "Option Type",
    ["Call", "Put"],
    index=0
)

_spot_default = float(st.session_state.get("opt_spot", 100.0))
S = st.sidebar.number_input(
    "Stock Price",
    min_value=1.0,
    value=_spot_default,
    step=1.0
)

K = st.sidebar.number_input(
    "Strike Price",
    min_value=1.0,
    value=100.0,
    step=1.0
)

T = st.sidebar.number_input(
    "Time to Expiration Years",
    min_value=0.01,
    value=1.0,
    step=0.05
)

r = st.sidebar.number_input(
    "Risk-Free Rate",
    min_value=0.0,
    value=0.05,
    step=0.005
)

sigma = st.sidebar.number_input(
    "Volatility",
    min_value=0.01,
    value=0.20,
    step=0.01
)

market_price = st.sidebar.number_input(
    "Market Option Price for IV",
    min_value=0.0,
    value=10.0,
    step=0.25
)

st.sidebar.header("Advanced Settings")

simulations = st.sidebar.slider(
    "Monte Carlo Simulations",
    1000,
    100000,
    20000,
    1000
)

tree_steps = st.sidebar.slider(
    "Binomial Tree Steps",
    10,
    500,
    100,
    10
)

seed = st.sidebar.number_input(
    "Random Seed",
    min_value=0,
    value=42,
    step=1
)

run = st.sidebar.button(
    "Run Option Pricing",
    use_container_width=True
)


# =============================
# Waiting state
# =============================
if not run:
    st.info("Enter option inputs in the sidebar and click Run Option Pricing.")
    st.stop()


# =============================
# Pricing calculations
# =============================
bs_price = black_scholes_price(
    S,
    K,
    T,
    r,
    sigma,
    option_type
)

greeks = black_scholes_greeks(
    S,
    K,
    T,
    r,
    sigma,
    option_type
)

mc_price, terminal_prices, payoffs = monte_carlo_option_price(
    S,
    K,
    T,
    r,
    sigma,
    option_type,
    simulations,
    seed
)

tree_price = binomial_tree_price(
    S,
    K,
    T,
    r,
    sigma,
    option_type,
    tree_steps
)

iv = implied_volatility(
    market_price,
    S,
    K,
    T,
    r,
    option_type
)


# =============================
# Summary
# =============================
section(
    "Option Pricing Summary",
    "Compare Black-Scholes, Monte Carlo, and binomial tree option prices."
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Black-Scholes Price", f"${bs_price:,.2f}")
c2.metric("Monte Carlo Price", f"${mc_price:,.2f}")
c3.metric("Binomial Tree Price", f"${tree_price:,.2f}")

if iv is None:
    c4.metric("Implied Volatility", "N/A")
else:
    c4.metric("Implied Volatility", f"{iv*100:.2f}%")

st.divider()


# =============================
# Greeks
# =============================
section(
    "Option Greeks",
    "Risk sensitivities of the option price to market variables."
)

g1, g2, g3, g4, g5 = st.columns(5)

g1.metric("Delta", f"{greeks['Delta']:.4f}")
g2.metric("Gamma", f"{greeks['Gamma']:.4f}")
g3.metric("Vega", f"{greeks['Vega']:.4f}")
g4.metric("Theta / Day", f"{greeks['Theta']:.4f}")
g5.metric("Rho", f"{greeks['Rho']:.4f}")

greek_df = pd.DataFrame({
    "Greek": list(greeks.keys()),
    "Value": list(greeks.values()),
    "Meaning": [
        "Price change for $1 move in stock",
        "Change in Delta for $1 move in stock",
        "Price change for 1 volatility point",
        "Daily time decay",
        "Price change for 1 rate point"
    ]
})

st.dataframe(
    greek_df,
    use_container_width=True
)

st.divider()


# =============================
# Volatility sensitivity
# =============================
section(
    "Volatility Sensitivity",
    "How the option price changes as implied volatility changes."
)

vol_range = np.linspace(
    max(0.01, sigma * 0.25),
    sigma * 2.5,
    80
)

vol_prices = []

i = 0
while i < len(vol_range):
    vol_prices.append(
        black_scholes_price(
            S,
            K,
            T,
            r,
            float(vol_range[i]),
            option_type
        )
    )
    i += 1

vol_df = pd.DataFrame({
    "Volatility": vol_range,
    "Option Price": vol_prices
})

fig1 = go.Figure(go.Scatter(x=vol_df["Volatility"], y=vol_df["Option Price"],
                            mode="lines", line=dict(color="#10b981", width=2)))
fig1.update_layout(title="Option Price vs Volatility", xaxis_title="Volatility",
                   yaxis_title="Option Price", **plotly_config())
st.plotly_chart(fig1, use_container_width=True)

st.divider()


# =============================
# Payoff diagram
# =============================
section(
    "Payoff Diagram",
    "Profit and loss at expiration using the Black-Scholes premium."
)

payoff_df = option_payoff_range(
    S,
    K,
    bs_price,
    option_type
)

fig2 = go.Figure(go.Scatter(x=payoff_df["Underlying Price"], y=payoff_df["Profit / Loss"],
                            mode="lines", line=dict(color="#3b82f6", width=2)))
fig2.add_hline(y=0, line_dash="dash", line_color="#64748b")
fig2.add_vline(x=K, line_dash="dash", line_color="#f59e0b",
               annotation_text="Strike", annotation_position="top right")
fig2.update_layout(title=f"{option_type} Option Payoff at Expiration",
                   xaxis_title="Underlying Price at Expiration", yaxis_title="Profit / Loss",
                   **plotly_config())
st.plotly_chart(fig2, use_container_width=True)

st.divider()


# =============================
# Monte Carlo distribution
# =============================
section(
    "Monte Carlo Terminal Price Distribution",
    "Simulated terminal stock prices and option payoff behavior."
)

c1, c2 = st.columns(2)

with c1:
    fig3 = go.Figure(go.Histogram(x=terminal_prices, nbinsx=50, marker_color="#3b82f6", opacity=0.75))
    fig3.add_vline(x=K, line_dash="dash", line_color="#f59e0b",
                   annotation_text="Strike", annotation_position="top right")
    fig3.update_layout(title="Simulated Terminal Stock Prices", xaxis_title="Terminal Price",
                       yaxis_title="Frequency", **plotly_config())
    st.plotly_chart(fig3, use_container_width=True)

with c2:
    fig4 = go.Figure(go.Histogram(x=payoffs, nbinsx=50, marker_color="#10b981", opacity=0.75))
    fig4.update_layout(title="Simulated Option Payoffs", xaxis_title="Payoff",
                       yaxis_title="Frequency", **plotly_config())
    st.plotly_chart(fig4, use_container_width=True)

st.divider()


# =============================
# Pricing comparison table
# =============================
section(
    "Pricing Model Comparison",
    "Compare outputs across multiple option pricing methods."
)

comparison_df = pd.DataFrame({
    "Model": [
        "Black-Scholes",
        "Monte Carlo",
        "Binomial Tree"
    ],
    "Price": [
        bs_price,
        mc_price,
        tree_price
    ],
    "Difference vs Black-Scholes": [
        0.0,
        mc_price - bs_price,
        tree_price - bs_price
    ]
})

st.dataframe(
    comparison_df.style.format({
        "Price": "${:.2f}",
        "Difference vs Black-Scholes": "${:.2f}"
    }),
    use_container_width=True
)

st.divider()


# =============================
# Moneyness explanation
# =============================
section(
    "Option Interpretation",
    "Plain-English interpretation of the option setup."
)

moneyness = S / K

if option_type == "Call":
    if S > K:
        st.success("This call option is in-the-money because stock price is above strike.")
    elif S < K:
        st.warning("This call option is out-of-the-money because stock price is below strike.")
    else:
        st.info("This call option is at-the-money.")
else:
    if S < K:
        st.success("This put option is in-the-money because stock price is below strike.")
    elif S > K:
        st.warning("This put option is out-of-the-money because stock price is above strike.")
    else:
        st.info("This put option is at-the-money.")

st.write(f"Moneyness S/K: {moneyness:.3f}")

if greeks["Gamma"] > 0.05:
    st.warning("Gamma is relatively high. Delta may change quickly as the stock price moves.")

if abs(greeks["Theta"]) > 0.05:
    st.warning("Theta decay is meaningful. The option loses noticeable value each day, all else equal.")

if abs(greeks["Vega"]) > 0.10:
    st.info("Vega exposure is meaningful. The option is sensitive to volatility changes.")


# =============================
# Save state
# =============================
st.session_state["option_bs_price"] = float(bs_price)
st.session_state["option_mc_price"] = float(mc_price)
st.session_state["option_tree_price"] = float(tree_price)
st.session_state["option_delta"] = float(greeks["Delta"])
st.session_state["option_gamma"] = float(greeks["Gamma"])
st.session_state["option_vega"] = float(greeks["Vega"])
st.session_state["option_theta"] = float(greeks["Theta"])
st.session_state["option_rho"] = float(greeks["Rho"])

if iv is not None:
    st.session_state["option_implied_volatility"] = float(iv)


# =============================
# Next step
# =============================
next_step(
    "Use VaR/CVaR Risk Engine or Monte Carlo next to compare option risk with portfolio-level downside risk."
)