"""
PropagationEngine — propagates an oil price shock through Brisbane's economic indicators.

Transfer coefficients are calibrated from Russia-Ukraine 2022 data (the most recent
and best-documented oil/energy shock with Brisbane-specific outcomes).

Brisbane car-dependency multiplier (1.18) is applied to all fuel-linked indicators
to reflect ~80% private vehicle trip share vs ~65% national average.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.shock_params import ShockScenario

# ---------------------------------------------------------------------------
# Brisbane car-dependency multiplier (fuel-linked indicators)
# ---------------------------------------------------------------------------
BRISBANE_CAR_DEPENDENCY_MULT = 1.18

# ---------------------------------------------------------------------------
# Transfer coefficients: {indicator_name: TransferSpec}
#
# Each spec defines:
#   base_coeff   – fractional delta per unit oil price multiplier (above 1.0)
#                  e.g. 0.40 means a 2x oil price → -40% delta on the indicator
#   lag_weeks    – weeks before impact is fully felt (linear ramp)
#   direction    – +1 (rises with oil) or -1 (falls with oil)
#   fuel_linked  – apply Brisbane car-dependency multiplier
#
# Calibration sources:
#   – Russia-Ukraine 2022: jet fuel +143%, Brisbane 91ULP peak +63% (231.6 cpl)
#   – CPI food peak +7.6% YoY in Q3 2022 driven by fuel/logistics
#   – NAB Business Confidence: -20pp within 3 months
#   – Consumer Sentiment: fell to 83.7 by Aug 2022 (from 100.7 pre-war)
# ---------------------------------------------------------------------------

_T = dict  # type alias for readability


def _spec(base_coeff: float, lag_weeks: int, direction: int = -1, fuel_linked: bool = False) -> _T:
    return {
        "base_coeff": base_coeff,
        "lag_weeks": lag_weeks,
        "direction": direction,
        "fuel_linked": fuel_linked,
    }


TRANSFER_COEFFICIENTS: dict[str, _T] = {
    # ---- Aviation & Connectivity ----------------------------------------
    "Jet fuel price - Singapore Kerosene (USD/bbl)": _spec(0.95, 0, direction=+1, fuel_linked=True),
    "International weekly seat capacity BNE (000s, est.)": _spec(0.30, 6),
    "Brisbane Airport intl load factor (%) - July": _spec(0.18, 8),
    "International visitor arrivals Queensland (000s)": _spec(0.25, 10),
    "Brisbane Airport total passengers (m)": _spec(0.20, 8),
    # ---- Domestic Travel ------------------------------------------------
    # Jet fuel drives domestic airfares within 3-4 weeks; seat capacity cuts follow
    # Calibration: Brent +63% (2022) → Qantas/Virgin domestic fares +18–22% within 6 weeks
    "Domestic weekly seat capacity BNE (000s)": _spec(0.22, 4, fuel_linked=True),
    "Average domestic airfare BNE–SYD/MEL (AUD)": _spec(0.30, 3, direction=+1, fuel_linked=True),
    "Domestic visitors to Brisbane (000s, quarterly)": _spec(0.16, 8, fuel_linked=True),
    # ---- Visitor Economy ------------------------------------------------
    "Brisbane CBD hotel occupancy rate (%)": _spec(0.15, 10),
    "Brisbane CBD ADR - Average Daily Rate (AUD)": _spec(0.10, 12),
    "Brisbane CBD RevPAR (AUD)": _spec(0.18, 12),
    "Queensland domestic overnight visitor spend ($B)": _spec(0.12, 8),
    "BCEC event pipeline (forward bookings)": _spec(0.08, 16),
    "Cruise ship arrivals - Port of Brisbane (no. of calls)": _spec(0.10, 20),
    # ---- Consumer Cost of Living ----------------------------------------
    "Brisbane CPI - all groups (YoY %)": _spec(0.22, 4, direction=+1, fuel_linked=True),
    "Brisbane CPI - food subgroup (YoY %)": _spec(0.28, 6, direction=+1, fuel_linked=True),
    "RACQ 91 ULP Brisbane - annual average (cpl)": _spec(0.60, 1, direction=+1, fuel_linked=True),
    "RACQ Diesel Brisbane - Q4 average (cpl)": _spec(0.65, 1, direction=+1, fuel_linked=True),
    "Electricity retail tariff - Queensland (c/kWh, flat residential)": _spec(0.12, 8, direction=+1),
    "Brisbane median weekly rent - houses (AUD)": _spec(0.05, 20, direction=+1),
    # ---- Retail & Consumer Spending -------------------------------------
    "Queensland retail trade turnover (monthly, $B)": _spec(0.15, 6, fuel_linked=True),
    "Westpac-Melbourne Institute Consumer Sentiment Index": _spec(0.20, 4, fuel_linked=True),
    "Discretionary vs non-discretionary spend ratio - Queensland": _spec(0.22, 6, fuel_linked=True),
    # ---- Business Confidence --------------------------------------------
    "NAB Business Confidence Index - Queensland": _spec(0.25, 3),
    "CCIQ Pulse Survey - business conditions (net balance)": _spec(0.22, 4),
    "ACCI Investor Confidence Survey": _spec(0.20, 5),
    # ---- Labour Market --------------------------------------------------
    "Unemployment rate - Brisbane SA4 (combined, %)": _spec(0.12, 12, direction=+1),
    "Underemployment rate - Queensland (%)": _spec(0.10, 14, direction=+1),
    "Internet Vacancy Index - Queensland (SEEK / ANZ-Indeed proxy)": _spec(0.18, 10),
    "Wage Price Index - Queensland (YoY %)": _spec(0.05, 16, direction=+1),
    "Net interstate migration to Queensland (persons)": _spec(0.08, 26),
    # ---- Housing & Real Estate ------------------------------------------
    "Brisbane median house price - CoreLogic (AUD)": _spec(0.08, 20),
    "Brisbane median unit price (AUD)": _spec(0.07, 20),
    "Rental vacancy rate - Brisbane (%)": _spec(0.03, 16, direction=+1),
    "New dwelling approvals - Queensland (no.)": _spec(0.12, 16),
    "Mortgage stress - QLD mortgage holders 'at risk' (%)": _spec(0.10, 12, direction=+1),
    # ---- Construction & Infrastructure ----------------------------------
    "Queensland construction cost index (YoY %, Cordell CCCI)": _spec(0.15, 6, direction=+1, fuel_linked=True),
    "Residential building approvals - Brisbane (no., monthly avg)": _spec(0.12, 16),
    "Queensland Major Projects Pipeline - 5-year ($B)": _spec(0.06, 26),
    "QBCC insolvency-related complaints (no.)": _spec(0.12, 20, direction=+1),
    # ---- Inward Investment ----------------------------------------------
    "FIRB commercial approvals - no. (H1 FY24)": _spec(0.10, 16),
    "FIRB commercial approvals - value ($B, H1 FY24)": _spec(0.12, 16),
    "Queensland greenfield investment (announced, $B)": _spec(0.10, 20),
    "Brisbane CBD office vacancy rate (%, total)": _spec(0.06, 20, direction=+1),
    "Brisbane CBD net absorption (sqm)": _spec(0.10, 20),
    "Queensland new business registrations": _spec(0.08, 12),
    # ---- Agriculture & Supply Chain -------------------------------------
    "ABARES gross value of agricultural production (forecast, $B)": _spec(0.12, 8),
    "Lockyer Valley produce wholesale price proxy": _spec(0.18, 4, direction=+1, fuel_linked=True),
    "Brisbane fuel-linked freight cost indicator": _spec(0.50, 2, direction=+1, fuel_linked=True),
    # ---- Energy ---------------------------------------------------------
    "Queensland AEMO wholesale electricity spot price ($/MWh, Q4 avg)": _spec(0.20, 4, direction=+1),
    "Queensland solar penetration - % of generation mix (peak, distributed PV)": _spec(0.02, 52),
    "Domestic gas price - Queensland ($/GJ, east coast wholesale)": _spec(0.25, 3, direction=+1),
    # ---- Education & Int'l Students -------------------------------------
    "International student enrolments - Brisbane (all sectors)": _spec(0.10, 20),
    "Student visa grant rate - Australia (%)": _spec(0.03, 26),
    "TAFE/VET enrolments - Queensland (000s)": _spec(0.02, 16),
    # ---- Government Fiscal ----------------------------------------------
    "Queensland state budget surplus/deficit ($B)": _spec(0.10, 20),
    "Committed infrastructure pipeline - Queensland 2024-2032 ($B)": _spec(0.04, 26),
    "Queensland cost-of-living relief measures - total value ($B)": _spec(0.06, 16, direction=+1),
}


class PropagationEngine:
    """
    Propagates a ShockScenario through Brisbane's BEDA indicators over 52 weeks.

    Usage:
        engine = PropagationEngine(scenario, baseline)
        ts = engine.propagate()   # DataFrame: weeks × indicators (delta values)
    """

    def __init__(self, scenario: ShockScenario, baseline: dict):
        self.scenario = scenario
        self.baseline = baseline
        self._flat = self._flatten_baseline()

    # ------------------------------------------------------------------
    def _flatten_baseline(self) -> dict[str, float]:
        """Return {indicator_name: current_value_as_float} across all categories."""
        flat: dict[str, float] = {}
        for cat_data in self.baseline.values():
            for ind, vals in cat_data.items():
                cv = vals.get("current_value")
                if isinstance(cv, (int, float)):
                    flat[ind] = float(cv)
                else:
                    flat[ind] = 0.0  # text-only indicators get zero baseline
        return flat

    # ------------------------------------------------------------------
    def _oil_path(self) -> np.ndarray:
        """
        Build a 52-week oil price multiplier path.

        Shock rises linearly to peak over the first 4 weeks of the disruption,
        holds at peak for the duration, then decays exponentially back toward 1.0
        with a half-life of (duration_weeks / 2) weeks.
        """
        weeks = np.arange(1, 53)
        mult = self.scenario.get_oil_multiplier()
        dur = self.scenario.duration_weeks
        ramp = 4  # weeks to reach peak

        path = np.ones(52)
        for i, w in enumerate(weeks):
            if w <= ramp:
                path[i] = 1.0 + (mult - 1.0) * (w / ramp)
            elif w <= dur:
                path[i] = mult
            else:
                half_life = max(dur / 2, 4)
                decay = np.exp(-np.log(2) * (w - dur) / half_life)
                path[i] = 1.0 + (mult - 1.0) * decay

        return path

    # ------------------------------------------------------------------
    def propagate(self) -> pd.DataFrame:
        """
        Returns a DataFrame with:
            - index: week number (1..52)
            - columns: indicator names
            - values: DELTA from baseline (not absolute level)
        """
        oil_path = self._oil_path()
        oil_excess = oil_path - 1.0  # amount above baseline multiplier

        weeks = list(range(1, 53))
        results: dict[str, list[float]] = {}

        for ind, spec in TRANSFER_COEFFICIENTS.items():
            baseline_val = self._flat.get(ind, 0.0)
            coeff = spec["base_coeff"]
            lag = spec["lag_weeks"]
            direction = spec["direction"]
            car_mult = BRISBANE_CAR_DEPENDENCY_MULT if spec["fuel_linked"] else 1.0

            deltas = []
            for i in range(52):
                # Apply lag: use oil excess from (i - lag) weeks ago, clamped to 0
                oil_idx = max(0, i - lag)
                oe = oil_excess[oil_idx]

                # Raw impact as a fraction of baseline
                frac_impact = direction * coeff * car_mult * oe

                # Scale to actual units (fraction of baseline value)
                delta = frac_impact * abs(baseline_val) if baseline_val != 0.0 else frac_impact

                deltas.append(round(delta, 4))

            results[ind] = deltas

        df = pd.DataFrame(results, index=weeks)
        df.index.name = "week"
        return df

    # ------------------------------------------------------------------
    def oil_price_path(self) -> pd.Series:
        """Return the 52-week oil price multiplier series (for charting)."""
        return pd.Series(self._oil_path(), index=range(1, 53), name="oil_price_multiplier")
