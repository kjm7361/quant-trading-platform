import pandas as pd
import numpy as np


class TradingBot:
    def __init__(
        self,
        short_window=5,
        long_window=20,
        risk_pct=0.02,
        max_position_value=20000.0
    ):
        self.short_window = int(short_window)
        self.long_window = int(long_window)
        self.risk_pct = float(risk_pct)
        self.max_position_value = float(max_position_value)

    def prepare_data(self, price_series):
        prices = pd.Series(price_series).dropna().copy()

        df = pd.DataFrame({"price": prices})
        df["short_ma"] = df["price"].rolling(self.short_window).mean()
        df["long_ma"] = df["price"].rolling(self.long_window).mean()
        df["returns"] = df["price"].pct_change()
        df["volatility"] = df["returns"].rolling(self.long_window).std()

        return df

    def generate_signal(self, price_series):
        df = self.prepare_data(price_series)

        if len(df) < self.long_window:
            return {
                "signal": "hold",
                "reason": "Not enough data"
            }

        last_row = df.iloc[-1]

        if pd.isna(last_row["short_ma"]) or pd.isna(last_row["long_ma"]):
            return {
                "signal": "hold",
                "reason": "Moving averages not ready"
            }

        if last_row["short_ma"] > last_row["long_ma"]:
            return {
                "signal": "buy",
                "reason": "Short MA above Long MA"
            }

        if last_row["short_ma"] < last_row["long_ma"]:
            return {
                "signal": "sell",
                "reason": "Short MA below Long MA"
            }

        return {
            "signal": "hold",
            "reason": "No clear edge"
        }

    def suggest_position_size(self, cash, price, volatility=None):
        cash = float(cash)
        price = float(price)

        if price <= 0:
            return 0.0

        capital_at_risk = cash * self.risk_pct

        if volatility is not None and not pd.isna(volatility) and volatility > 0:
            risk_adjustment = max(0.25, min(2.0, 0.02 / float(volatility)))
        else:
            risk_adjustment = 1.0

        target_value = capital_at_risk * 10.0 * risk_adjustment

        if target_value > self.max_position_value:
            target_value = self.max_position_value

        if target_value > cash:
            target_value = cash

        qty = target_value / price
        return max(0.0, float(qty))

    def analyze(self, price_series, cash):
        df = self.prepare_data(price_series)
        signal_info = self.generate_signal(price_series)

        latest_price = float(pd.Series(price_series).dropna().iloc[-1])

        latest_vol = None
        if len(df) > 0 and "volatility" in df.columns:
            latest_vol = df["volatility"].iloc[-1]

        suggested_qty = self.suggest_position_size(
            cash=cash,
            price=latest_price,
            volatility=latest_vol
        )

        return {
            "signal": signal_info["signal"],
            "reason": signal_info["reason"],
            "latest_price": latest_price,
            "suggested_qty": suggested_qty,
            "volatility": 0.0 if latest_vol is None or pd.isna(latest_vol) else float(latest_vol)
        }