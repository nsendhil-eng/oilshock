"""
Build three GeoJSON FeatureCollections for Kepler.gl:

1. sa4_impact.geojson  — Brisbane SA4 regions with impact scores at weeks 4/13/26/52
2. route_arcs.geojson  — BNE → [NRT, ICN, SIN, HKG, PVG, LAX, AKL] arcs
3. freight_corridors.geojson — Brisbane freight road/rail corridors
"""
from __future__ import annotations

import json
from pathlib import Path

from geo.fetch_boundaries import fetch_sa4_boundaries, get_polygon_for_sa4

import pandas as pd

# ---------------------------------------------------------------------------
# SA4 region definitions (approximate centroids + bounding polygons)
# Brisbane SA4 regions as defined by ABS SA4 2021
# Using simplified bounding boxes for choropleth display
# ---------------------------------------------------------------------------

SA4_REGIONS = [
    {
        "sa4_code": "301",
        "sa4_name": "Brisbane - East",
        "centroid": [153.115, -27.475],
        "polygon": [
            [153.03, -27.40], [153.20, -27.40], [153.20, -27.60], [153.03, -27.60], [153.03, -27.40]
        ],
        # Category impact weights (higher = more exposed to Hormuz oil shock)
        "weights": {
            "Aviation & Connectivity": 0.85,
            "Domestic Travel": 0.80,
            "Visitor Economy": 0.90,
            "Consumer Cost of Living": 0.95,
            "Retail & Consumer Spending": 0.80,
            "Labour Market": 0.75,
            "Housing & Real Estate": 0.70,
        },
    },
    {
        "sa4_code": "302",
        "sa4_name": "Brisbane - North",
        "centroid": [152.985, -27.355],
        "polygon": [
            [152.90, -27.28], [153.08, -27.28], [153.08, -27.43], [152.90, -27.43], [152.90, -27.28]
        ],
        "weights": {
            "Aviation & Connectivity": 0.95,  # Near BNE airport
            "Domestic Travel": 0.92,           # Airport workers, travel-linked employment
            "Visitor Economy": 0.85,
            "Consumer Cost of Living": 0.90,
            "Retail & Consumer Spending": 0.82,
            "Labour Market": 0.78,
            "Housing & Real Estate": 0.72,
        },
    },
    {
        "sa4_code": "303",
        "sa4_name": "Brisbane - South",
        "centroid": [153.020, -27.590],
        "polygon": [
            [152.94, -27.52], [153.10, -27.52], [153.10, -27.66], [152.94, -27.66], [152.94, -27.52]
        ],
        "weights": {
            "Aviation & Connectivity": 0.70,
            "Domestic Travel": 0.72,
            "Visitor Economy": 0.75,
            "Consumer Cost of Living": 1.00,  # High car-dependency
            "Retail & Consumer Spending": 0.88,
            "Labour Market": 0.80,
            "Housing & Real Estate": 0.85,
        },
    },
    {
        "sa4_code": "304",
        "sa4_name": "Brisbane - West",
        "centroid": [152.850, -27.530],
        "polygon": [
            [152.77, -27.46], [152.93, -27.46], [152.93, -27.60], [152.77, -27.60], [152.77, -27.46]
        ],
        "weights": {
            "Aviation & Connectivity": 0.65,
            "Domestic Travel": 0.68,
            "Visitor Economy": 0.70,
            "Consumer Cost of Living": 1.05,  # Very high car-dependency, longer commutes
            "Retail & Consumer Spending": 0.85,
            "Labour Market": 0.76,
            "Housing & Real Estate": 0.82,
        },
    },
    {
        "sa4_code": "305",
        "sa4_name": "Brisbane Inner City",
        "centroid": [153.025, -27.468],
        "polygon": [
            [152.97, -27.43], [153.08, -27.43], [153.08, -27.51], [152.97, -27.51], [152.97, -27.43]
        ],
        "weights": {
            "Aviation & Connectivity": 0.90,
            "Domestic Travel": 0.95,           # CBD hotels/hospitality depend on domestic business travel
            "Visitor Economy": 1.00,            # CBD — highest visitor economy exposure
            "Consumer Cost of Living": 0.75,    # More transit usage, lower car-dependency
            "Retail & Consumer Spending": 0.92,
            "Labour Market": 0.88,
            "Housing & Real Estate": 0.80,
        },
    },
    {
        "sa4_code": "310",
        "sa4_name": "Ipswich",
        "centroid": [152.755, -27.615],
        "polygon": [
            [152.67, -27.54], [152.84, -27.54], [152.84, -27.69], [152.67, -27.69], [152.67, -27.54]
        ],
        "weights": {
            "Aviation & Connectivity": 0.55,
            "Domestic Travel": 0.50,
            "Visitor Economy": 0.50,
            "Consumer Cost of Living": 1.10,  # Highest car-dependency, logistics hub
            "Retail & Consumer Spending": 0.78,
            "Labour Market": 0.85,
            "Housing & Real Estate": 0.76,
        },
    },
    {
        "sa4_code": "311",
        "sa4_name": "Logan - Beaudesert",
        "centroid": [153.025, -27.700],
        "polygon": [
            [152.95, -27.63], [153.10, -27.63], [153.10, -27.77], [152.95, -27.77], [152.95, -27.63]
        ],
        "weights": {
            "Aviation & Connectivity": 0.50,
            "Domestic Travel": 0.48,
            "Visitor Economy": 0.55,
            "Consumer Cost of Living": 1.08,
            "Retail & Consumer Spending": 0.80,
            "Labour Market": 0.82,
            "Housing & Real Estate": 0.78,
        },
    },
    {
        "sa4_code": "313",
        "sa4_name": "Moreton Bay - North",
        "centroid": [152.960, -27.250],
        "polygon": [
            [152.88, -27.18], [153.04, -27.18], [153.04, -27.32], [152.88, -27.32], [152.88, -27.18]
        ],
        "weights": {
            "Aviation & Connectivity": 0.60,
            "Domestic Travel": 0.58,
            "Visitor Economy": 0.60,
            "Consumer Cost of Living": 1.02,
            "Retail & Consumer Spending": 0.76,
            "Labour Market": 0.74,
            "Housing & Real Estate": 0.74,
        },
    },
    {
        "sa4_code": "314",
        "sa4_name": "Moreton Bay - South",
        "centroid": [152.940, -27.320],
        "polygon": [
            [152.86, -27.26], [153.02, -27.26], [153.02, -27.38], [152.86, -27.38], [152.86, -27.26]
        ],
        "weights": {
            "Aviation & Connectivity": 0.68,
            "Domestic Travel": 0.65,
            "Visitor Economy": 0.65,
            "Consumer Cost of Living": 0.98,
            "Retail & Consumer Spending": 0.78,
            "Labour Market": 0.76,
            "Housing & Real Estate": 0.73,
        },
    },
]

# ---------------------------------------------------------------------------
# Route arcs: BNE → major international hubs
# ---------------------------------------------------------------------------
BNE = {"lon": 153.117, "lat": -27.384}

ROUTE_DESTINATIONS = [
    {
        "code": "NRT", "name": "Tokyo Narita", "lon": 140.386, "lat": 35.764,
        "arc_weight": 0.85, "disruption_level": "HIGH",
        "reasoning": (
            "Japan imports ~90% of its oil via Hormuz. A closure triggers immediate "
            "fuel rationing and airline cost spikes. Japan is Brisbane's largest inbound "
            "tourism market by spend, so load factor and yield on BNE–NRT drop sharply "
            "as fares rise and Japanese outbound travel contracts."
        ),
    },
    {
        "code": "ICN", "name": "Seoul Incheon", "lon": 126.451, "lat": 37.469,
        "arc_weight": 0.78, "disruption_level": "HIGH",
        "reasoning": (
            "South Korea sources ~70% of crude via Hormuz. Korean carriers (Korean Air, "
            "Asiana) face severe jet fuel cost pressure, reducing BNE capacity. South Korea "
            "is a key source of international students and business visitors to Brisbane — "
            "both discretionary segments sensitive to fare increases."
        ),
    },
    {
        "code": "SIN", "name": "Singapore Changi", "lon": 103.989, "lat": 1.359,
        "arc_weight": 0.92, "disruption_level": "CRITICAL",
        "reasoning": (
            "Singapore sits at the intersection of Hormuz and Malacca chokepoints. "
            "Jurong Island refines ~1.5M bbl/day — much of Asia's jet fuel supply — "
            "using Hormuz crude. BNE sources jet fuel contracts priced off Singapore spot. "
            "SIN is also Brisbane's primary hub connection to the Middle East, India, and "
            "Europe, meaning a disruption here cascades across multiple onward routes. "
            "Cargo freight to/from BNE is also heavily SIN-routed."
        ),
    },
    {
        "code": "HKG", "name": "Hong Kong", "lon": 113.915, "lat": 22.308,
        "arc_weight": 0.82, "disruption_level": "HIGH",
        "reasoning": (
            "Hong Kong is a major re-export and transit hub for goods moving between "
            "Brisbane and mainland China. Cathay Pacific — the dominant BNE–HKG carrier — "
            "hedges jet fuel but remains exposed to sustained price spikes. Hong Kong's "
            "role as a financial hub means business travel demand is sensitive to broader "
            "economic shock from an oil crisis."
        ),
    },
    {
        "code": "PVG", "name": "Shanghai Pudong", "lon": 121.805, "lat": 31.143,
        "arc_weight": 0.75, "disruption_level": "MODERATE",
        "reasoning": (
            "China has ~90 days of strategic petroleum reserves and significant "
            "alternative supply from Russia via pipeline, partially insulating it from "
            "a short-to-medium Hormuz closure. Chinese carriers are state-backed and "
            "absorb fuel cost increases longer before passing them on. BNE–PVG sees "
            "moderate disruption: fares rise and some capacity is cut, but the route "
            "is unlikely to suspend."
        ),
    },
    {
        "code": "LAX", "name": "Los Angeles", "lon": -118.408, "lat": 33.943,
        "arc_weight": 0.60, "disruption_level": "LOW",
        "reasoning": (
            "The US sources less than 10% of crude from the Gulf region and has large "
            "strategic reserves. The BNE–LAX route is a Pacific crossing with no "
            "refuelling dependency on Hormuz-linked supply chains. US carriers price "
            "fuel off WTI (less Gulf-exposed than Brent/Singapore). Fares will rise "
            "modestly as global oil prices increase, but route operations are unaffected."
        ),
    },
    {
        "code": "AKL", "name": "Auckland", "lon": 174.792, "lat": -37.008,
        "arc_weight": 0.70, "disruption_level": "LOW",
        "reasoning": (
            "BNE–AKL is a short-haul trans-Tasman route where fuel is a smaller share "
            "of ticket cost. Both Air NZ and Qantas price jet fuel off Singapore spot, "
            "so fares will rise with a Hormuz shock, but the route itself is unlikely "
            "to see capacity cuts — demand is resilient and the crossing is efficient. "
            "Could be upgraded to MODERATE if fare pass-through materially suppresses "
            "leisure travel volumes, which matters to Brisbane's visitor economy."
        ),
    },
]

# ---------------------------------------------------------------------------
# Freight corridors
# ---------------------------------------------------------------------------
FREIGHT_CORRIDORS = [
    {
        "name": "Bruce Highway (North)",
        "type": "road",
        "fuel_intensity": "HIGH",
        "coordinates": [
            [153.025, -27.465], [153.058, -27.380], [153.070, -27.300],
            [152.980, -27.180], [152.900, -27.080],
        ],
    },
    {
        "name": "Pacific Motorway (South)",
        "type": "road",
        "fuel_intensity": "HIGH",
        "coordinates": [
            [153.025, -27.465], [153.032, -27.540], [153.020, -27.620],
            [153.010, -27.700], [153.020, -27.800],
        ],
    },
    {
        "name": "Ipswich Motorway (West)",
        "type": "road",
        "fuel_intensity": "HIGH",
        "coordinates": [
            [153.025, -27.465], [152.960, -27.490], [152.880, -27.530],
            [152.800, -27.570], [152.760, -27.620],
        ],
    },
    {
        "name": "Freight Rail to Rocklea",
        "type": "rail",
        "fuel_intensity": "MEDIUM",
        "coordinates": [
            [153.025, -27.465], [152.990, -27.520], [152.960, -27.540],
            [152.940, -27.560],
        ],
    },
    {
        "name": "Port of Brisbane Access",
        "type": "road",
        "fuel_intensity": "CRITICAL",
        "coordinates": [
            [153.025, -27.465], [153.100, -27.440], [153.140, -27.420],
            [153.170, -27.380],
        ],
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_sa4_impact(
    propagation_df: pd.DataFrame,
    baseline: dict,
    output_path: str | Path | None = None,
) -> dict:
    """
    Generate sa4_impact GeoJSON.

    propagation_df: output of PropagationEngine.propagate()
                    (index=week, columns=indicator names, values=deltas from baseline)
    baseline:       output of load_baseline() — used to normalise deltas to % change
    impact_score:   0–100 index where each point = 1% average deviation from baseline,
                    weighted by regional exposure. Capped at 100.
    """
    snapshot_weeks = [4, 13, 26, 52]

    CATEGORY_INDICATORS = {
        "Aviation & Connectivity": [
            "Jet fuel price - Singapore Kerosene (USD/bbl)",
            "International weekly seat capacity BNE (000s, est.)",
            "International visitor arrivals Queensland (000s)",
            "Brisbane Airport total passengers (m)",
        ],
        "Domestic Travel": [
            "Domestic weekly seat capacity BNE (000s)",
            "Average domestic airfare BNE–SYD/MEL (AUD)",
            "Domestic visitors to Brisbane (000s, quarterly)",
        ],
        "Visitor Economy": [
            "Brisbane CBD hotel occupancy rate (%)",
            "Brisbane CBD RevPAR (AUD)",
            "Queensland domestic overnight visitor spend ($B)",
        ],
        "Consumer Cost of Living": [
            "Brisbane CPI - all groups (YoY %)",
            "RACQ 91 ULP Brisbane - annual average (cpl)",
            "RACQ Diesel Brisbane - Q4 average (cpl)",
        ],
        "Retail & Consumer Spending": [
            "Queensland retail trade turnover (monthly, $B)",
            "Westpac-Melbourne Institute Consumer Sentiment Index",
        ],
        "Labour Market": [
            "Unemployment rate - Brisbane SA4 (combined, %)",
            "Internet Vacancy Index - Queensland (SEEK / ANZ-Indeed proxy)",
        ],
        "Housing & Real Estate": [
            "Brisbane median house price - CoreLogic (AUD)",
            "New dwelling approvals - Queensland (no.)",
        ],
    }

    # Flat lookup: indicator → baseline current_value
    flat_baseline: dict[str, float] = {}
    for cat_data in baseline.values():
        for ind, vals in cat_data.items():
            cv = vals.get("current_value")
            if isinstance(cv, (int, float)) and cv != 0:
                flat_baseline[ind] = float(cv)

    # Try to load real ABS SA4 boundary polygons; fall back to rectangles
    real_boundaries = fetch_sa4_boundaries()

    features = []
    for region in SA4_REGIONS:
        props = {
            "sa4_code": region["sa4_code"],
            "sa4_name": region["sa4_name"],
        }

        for wk in snapshot_weeks:
            actual_wk = min(wk, len(propagation_df))

            composite = 0.0
            weight_sum = 0.0
            for cat, indicators in CATEGORY_INDICATORS.items():
                cat_weight = region["weights"].get(cat, 0.70)
                available_cols = [c for c in indicators if c in propagation_df.columns]
                if not available_cols:
                    continue

                pct_changes = []
                for ind in available_cols:
                    delta = propagation_df.loc[actual_wk, ind]
                    bv = flat_baseline.get(ind)
                    if bv and abs(bv) > 0:
                        pct_changes.append(abs(delta / bv) * 100)

                if not pct_changes:
                    continue

                cat_score = sum(pct_changes) / len(pct_changes)
                composite += cat_score * cat_weight
                weight_sum += cat_weight

            raw_score = (composite / weight_sum) if weight_sum > 0 else 0.0
            props[f"impact_score_wk{wk}"] = round(min(raw_score, 100.0), 1)

        # Use real ABS boundary if available, otherwise fall back to rectangle
        if real_boundaries:
            coords = get_polygon_for_sa4(real_boundaries, region["sa4_code"])
        else:
            coords = None
        if not coords:
            coords = [region["polygon"]]

        feature = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": coords},
            "properties": props,
        }
        features.append(feature)

    geojson = {"type": "FeatureCollection", "features": features}

    if output_path:
        Path(output_path).write_text(json.dumps(geojson, indent=2), encoding="utf-8")

    return geojson


_DISRUPTION_TIERS = ["LOW", "MODERATE", "HIGH", "CRITICAL"]


def _scale_disruption(base_level: str, oil_multiplier: float) -> str:
    """
    Shift disruption level up or down based on severity.
      PARTIAL  (<=1.25): -1 tier  (e.g. CRITICAL→HIGH, HIGH→MODERATE)
      MODERATE (<=1.55):  0       (base calibration)
      SEVERE   (<=1.85): +1 tier
      EXTREME  (> 1.85): +2 tiers
    """
    idx = _DISRUPTION_TIERS.index(base_level)
    if oil_multiplier <= 1.25:
        adj = -1
    elif oil_multiplier <= 1.55:
        adj = 0
    elif oil_multiplier <= 1.85:
        adj = +1
    else:
        adj = +2
    return _DISRUPTION_TIERS[max(0, min(3, idx + adj))]


def build_route_arcs(oil_multiplier: float, output_path: str | Path | None = None) -> dict:
    """Generate route_arcs GeoJSON for BNE → international hubs."""
    features = []
    for dest in ROUTE_DESTINATIONS:
        scaled_weight = dest["arc_weight"] * oil_multiplier
        disruption_level = _scale_disruption(dest["disruption_level"], oil_multiplier)

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [BNE["lon"], BNE["lat"]],
                    [dest["lon"], dest["lat"]],
                ],
            },
            "properties": {
                "origin": "BNE",
                "destination": dest["code"],
                "destination_name": dest["name"],
                "arc_weight": round(scaled_weight, 3),
                "base_arc_weight": dest["arc_weight"],
                "base_disruption_level": dest["disruption_level"],
                "disruption_level": disruption_level,
                "oil_multiplier": round(oil_multiplier, 3),
                "reasoning": dest["reasoning"],
            },
        }
        features.append(feature)

    geojson = {"type": "FeatureCollection", "features": features}

    if output_path:
        Path(output_path).write_text(json.dumps(geojson, indent=2), encoding="utf-8")

    return geojson


def build_freight_corridors(oil_multiplier: float, output_path: str | Path | None = None) -> dict:
    """Generate freight_corridors GeoJSON."""
    FUEL_INTENSITY_MULTIPLIER = {
        "LOW": 0.5,
        "MEDIUM": 0.75,
        "HIGH": 1.0,
        "CRITICAL": 1.25,
    }

    features = []
    for corridor in FREIGHT_CORRIDORS:
        fi = corridor["fuel_intensity"]
        cost_impact = (oil_multiplier - 1.0) * FUEL_INTENSITY_MULTIPLIER[fi]

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": corridor["coordinates"],
            },
            "properties": {
                "name": corridor["name"],
                "type": corridor["type"],
                "fuel_intensity": fi,
                "cost_impact_pct": round(cost_impact * 100, 2),
                "oil_multiplier": round(oil_multiplier, 3),
            },
        }
        features.append(feature)

    geojson = {"type": "FeatureCollection", "features": features}

    if output_path:
        Path(output_path).write_text(json.dumps(geojson, indent=2), encoding="utf-8")

    return geojson


def build_all_layers(
    propagation_df: pd.DataFrame,
    oil_multiplier: float,
    baseline: dict,
    output_dir: str | Path | None = None,
) -> tuple[dict, dict, dict]:
    """Build all three GeoJSON layers and optionally write to output_dir."""
    od = Path(output_dir) if output_dir else None

    sa4 = build_sa4_impact(
        propagation_df,
        baseline,
        od / "sa4_impact.geojson" if od else None,
    )
    arcs = build_route_arcs(
        oil_multiplier,
        od / "route_arcs.geojson" if od else None,
    )
    freight = build_freight_corridors(
        oil_multiplier,
        od / "freight_corridors.geojson" if od else None,
    )
    return sa4, arcs, freight
