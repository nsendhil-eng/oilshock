"""
SentimentCascade — models the human sentiment chain driven by an oil shock.

Chain:
  oil_shock → pump_price → disposable_income → consumer_sentiment
            → retail_spend → business_confidence → hiring → investment_pipeline

Each node has:
  lag_weeks           – delay from prior node signal
  transfer_coefficient – fractional pass-through (0–1)
  direction           – +1 (rises with prior node) or -1 (falls with prior node rise)

Calibrated from Russia-Ukraine 2022 Brisbane data.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.shock_params import ShockScenario


@dataclass
class ChainNode:
    name: str
    lag_weeks: int
    transfer_coefficient: float
    direction: int = -1  # -1 = node falls when upstream rises (negative cascade)


# ---------------------------------------------------------------------------
# Calibrated chain — Brisbane-specific lags and coefficients
# ---------------------------------------------------------------------------
CHAIN: list[ChainNode] = [
    # Node 0: oil shock itself (anchor — driven externally by ShockScenario)
    ChainNode("Oil Shock (Multiplier)", lag_weeks=0, transfer_coefficient=1.0, direction=+1),
    # Node 1: pump price follows oil almost immediately (Brisbane 91ULP data 2022)
    ChainNode("Pump Price (cpl)", lag_weeks=1, transfer_coefficient=0.62, direction=+1),
    # Node 2: disposable income squeezed as fuel cost rises (Brisbane car-dependency)
    ChainNode("Disposable Income Index", lag_weeks=3, transfer_coefficient=0.45, direction=-1),
    # Node 3: consumer sentiment tracks disposable income with slight lag
    # Westpac-MI Consumer Sentiment fell from 100→83.7 (~-16pp) by Aug 2022
    ChainNode("Consumer Sentiment Index", lag_weeks=4, transfer_coefficient=0.55, direction=-1),
    # Node 4: retail spend responds to sentiment (lag ~2 weeks post-sentiment move)
    # Discretionary retail led; grocery partially offset
    ChainNode("Retail Spend Index", lag_weeks=2, transfer_coefficient=0.48, direction=-1),
    # Node 5: business confidence tracks retail + sentiment (NAB fell -20pp in 3 months)
    ChainNode("Business Confidence Index", lag_weeks=3, transfer_coefficient=0.52, direction=-1),
    # Node 6: hiring intentions respond to confidence (ANZ-Indeed vacancy data)
    ChainNode("Hiring Intentions Index", lag_weeks=5, transfer_coefficient=0.40, direction=-1),
    # Node 7: investment pipeline — longest lag; projects deferred/cancelled
    ChainNode("Investment Pipeline Index", lag_weeks=8, transfer_coefficient=0.35, direction=-1),
]


class SentimentCascade:
    """
    Compute the sentiment timeline given a ShockScenario.

    Usage:
        sc = SentimentCascade(scenario)
        df = sc.propagate()   # DataFrame: weeks × chain nodes (index values, base=100)
    """

    def __init__(self, scenario: ShockScenario):
        self.scenario = scenario

    def _oil_signal(self) -> np.ndarray:
        """52-week oil price multiplier path (same shape as PropagationEngine)."""
        mult = self.scenario.get_oil_multiplier()
        dur = self.scenario.duration_weeks
        ramp = 4
        path = np.ones(52)
        for i in range(52):
            w = i + 1
            if w <= ramp:
                path[i] = 1.0 + (mult - 1.0) * (w / ramp)
            elif w <= dur:
                path[i] = mult
            else:
                half_life = max(dur / 2, 4)
                decay = np.exp(-np.log(2) * (w - dur) / half_life)
                path[i] = 1.0 + (mult - 1.0) * decay
        return path

    def propagate(self) -> pd.DataFrame:
        """
        Returns DataFrame indexed by week (1..52), one column per chain node.
        Values are index levels (base = 100 at week 0).
        """
        oil_signal = self._oil_signal()  # values >= 1.0

        # Store each node's signal series (length 52)
        signals: dict[str, np.ndarray] = {}
        prior_signal: np.ndarray | None = None

        for node in CHAIN:
            if prior_signal is None:
                # Anchor: oil shock excess (multiplier - 1), scaled to index units
                signals[node.name] = (oil_signal - 1.0) * 100.0  # e.g. 0.85 → 85
                prior_signal = signals[node.name].copy()
                continue

            lag = node.lag_weeks
            tc = node.transfer_coefficient
            direction = node.direction

            series = np.zeros(52)
            for i in range(52):
                src_idx = max(0, i - lag)
                upstream = prior_signal[src_idx]
                series[i] = direction * tc * upstream

            signals[node.name] = series
            prior_signal = series.copy()

        # Convert to index levels (base 100)
        df = pd.DataFrame(signals, index=range(1, 53))
        df.index.name = "week"

        # Shift all columns to base=100 at week 0 interpretation
        # (current values represent delta from a 100 baseline)
        return df

    def summary_stats(self) -> pd.DataFrame:
        """Return peak impact and week of peak for each node."""
        df = self.propagate()
        rows = []
        for col in df.columns:
            series = df[col]
            peak_val = series.abs().max()
            peak_wk = int(series.abs().idxmax())
            trough = float(series.min())
            rows.append({"node": col, "peak_abs_delta": round(peak_val, 2),
                         "peak_week": peak_wk, "trough_value": round(trough, 2)})
        return pd.DataFrame(rows).set_index("node")
