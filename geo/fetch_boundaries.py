"""
Fetch and cache real ABS SA4 boundary polygons for Brisbane.

Downloads from the ABS ASGS 2021 ArcGIS REST service, simplifies the polygons
to reduce vertex count for pydeck rendering, and caches to geo/sa4_brisbane.geojson.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

CACHE_PATH = Path(__file__).parent / "sa4_brisbane.geojson"

BRISBANE_SA4_CODES = [
    "301", "302", "303", "304", "305",
    "310", "311", "313", "314",
]

# ABS ASGS 2021 ArcGIS REST endpoint for SA4 boundaries
_CODES_SQL = ",".join(f"'{c}'" for c in BRISBANE_SA4_CODES)
ABS_URL = (
    "https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/SA4/MapServer/0/query"
    f"?where=SA4_CODE_2021+IN+({_CODES_SQL})"
    "&outFields=SA4_CODE_2021,SA4_NAME_2021"
    "&f=geojson"
    "&outSR=4326"
)

# Simplification tolerance in degrees (~200m at Brisbane latitude)
SIMPLIFY_TOLERANCE = 0.002


def fetch_sa4_boundaries(force: bool = False) -> dict | None:
    """
    Return a GeoJSON FeatureCollection keyed by SA4 code → polygon coordinates.

    Returns None if the download fails (callers fall back to rectangles).
    Uses a local cache at geo/sa4_brisbane.geojson to avoid repeat downloads.
    """
    if CACHE_PATH.exists() and not force:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    try:
        resp = requests.get(ABS_URL, timeout=30)
        resp.raise_for_status()
        raw = resp.json()
    except Exception as exc:
        print(f"[fetch_boundaries] download failed: {exc}")
        return None

    # Simplify each polygon and rebuild as a clean FeatureCollection
    features = []
    for feat in raw.get("features", []):
        props = feat.get("properties", {})
        code = str(props.get("sa4_code_2021") or props.get("SA4_CODE_2021", "")).zfill(3)
        name = props.get("sa4_name_2021") or props.get("SA4_NAME_2021", "")
        geom = feat.get("geometry")
        if not geom or code not in BRISBANE_SA4_CODES:
            continue

        try:
            shp = shape(geom)
            simplified = shp.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
            features.append({
                "type": "Feature",
                "geometry": mapping(simplified),
                "properties": {"sa4_code": code, "sa4_name": name},
            })
        except Exception as exc:
            print(f"[fetch_boundaries] simplify failed for {code}: {exc}")
            continue

    if not features:
        print("[fetch_boundaries] no features returned from ABS API")
        return None

    result = {"type": "FeatureCollection", "features": features}
    CACHE_PATH.write_text(json.dumps(result), encoding="utf-8")
    print(f"[fetch_boundaries] cached {len(features)} SA4 boundaries to {CACHE_PATH}")
    return result


def get_polygon_for_sa4(boundaries: dict, sa4_code: str) -> list | None:
    """
    Return the polygon coordinate ring(s) for a given SA4 code.
    Handles both Polygon and MultiPolygon geometry types.
    Returns a list of rings suitable for pydeck PolygonLayer.
    """
    for feat in boundaries.get("features", []):
        if feat["properties"]["sa4_code"] == sa4_code:
            geom = feat["geometry"]
            if geom["type"] == "Polygon":
                return geom["coordinates"]
            elif geom["type"] == "MultiPolygon":
                # Return the largest polygon ring
                rings = [part for part in geom["coordinates"]]
                largest = max(rings, key=lambda r: len(r[0]))
                return largest
    return None
