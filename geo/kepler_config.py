"""
Generate a complete Kepler.gl config dict for the three layers:
  1. SA4 choropleth (sequential purple) — impact scores
  2. Route arcs (blue → amber → red) — disruption level
  3. Freight corridors (orange heat) — cost impact
"""
from __future__ import annotations


def build_kepler_config(snapshot_week: int = 13) -> dict:
    """
    Return a Kepler.gl config dict.

    snapshot_week: which week's impact score column to display on the choropleth
                   (must be one of 4, 13, 26, 52)
    """
    week = snapshot_week if snapshot_week in (4, 13, 26, 52) else 13
    impact_field = f"impact_score_wk{week}"

    config = {
        "version": "v1",
        "config": {
            "visState": {
                "filters": [],
                "layers": [
                    # ----------------------------------------------------------
                    # Layer 1: SA4 choropleth — sequential purple
                    # ----------------------------------------------------------
                    {
                        "id": "sa4_impact_layer",
                        "type": "geojson",
                        "config": {
                            "dataId": "sa4_impact",
                            "label": "SA4 Impact Score",
                            "color": [108, 20, 138],
                            "columns": {"geojson": "_geojson"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.72,
                                "strokeOpacity": 0.8,
                                "thickness": 1.0,
                                "strokeColor": [255, 255, 255],
                                "colorRange": {
                                    "name": "Sequential Purple",
                                    "type": "sequential",
                                    "category": "Uber",
                                    "colors": [
                                        "#f2f0f7",
                                        "#dadaeb",
                                        "#bcbddc",
                                        "#9e9ac8",
                                        "#756bb1",
                                        "#54278f",
                                    ],
                                },
                                "strokeColorRange": {
                                    "name": "Global Warming",
                                    "type": "sequential",
                                    "category": "Uber",
                                    "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C",
                                               "#F1920E", "#FFC300"],
                                },
                                "radius": 10,
                                "sizeRange": [0, 10],
                                "radiusRange": [0, 50],
                                "heightRange": [0, 500],
                                "elevationScale": 5,
                                "enableElevationZoomFactor": True,
                                "stroked": True,
                                "filled": True,
                                "enable3d": False,
                                "wireframe": False,
                            },
                            "colorField": {"name": impact_field, "type": "real"},
                            "colorScale": "quantile",
                            "strokeColorField": None,
                            "strokeColorScale": "quantile",
                            "sizeField": None,
                            "sizeScale": "linear",
                            "heightField": None,
                            "heightScale": "linear",
                            "radiusField": None,
                            "radiusScale": "linear",
                        },
                        "visualChannels": {
                            "colorField": {"name": impact_field, "type": "real"},
                            "colorScale": "quantile",
                        },
                    },
                    # ----------------------------------------------------------
                    # Layer 2: Route arcs — blue → amber → red
                    # ----------------------------------------------------------
                    {
                        "id": "route_arcs_layer",
                        "type": "arc",
                        "config": {
                            "dataId": "route_arcs",
                            "label": "Flight Route Disruption",
                            "color": [183, 136, 94],
                            "columns": {
                                "lat0": "origin_lat",
                                "lng0": "origin_lng",
                                "lat1": "destination_lat",
                                "lng1": "destination_lng",
                            },
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.85,
                                "thickness": 3,
                                "colorRange": {
                                    "name": "Disruption Scale",
                                    "type": "diverging",
                                    "category": "Uber",
                                    "colors": [
                                        "#2196F3",  # blue — low disruption
                                        "#4CAF50",
                                        "#FFEB3B",
                                        "#FF9800",  # amber — moderate
                                        "#F44336",  # red — critical
                                    ],
                                },
                                "sizeRange": [1, 10],
                                "targetColor": [255, 69, 0],
                            },
                            "colorField": {"name": "arc_weight", "type": "real"},
                            "colorScale": "quantile",
                            "sizeField": {"name": "arc_weight", "type": "real"},
                            "sizeScale": "linear",
                        },
                        "visualChannels": {
                            "colorField": {"name": "arc_weight", "type": "real"},
                            "colorScale": "quantile",
                            "sizeField": {"name": "arc_weight", "type": "real"},
                            "sizeScale": "linear",
                        },
                    },
                    # ----------------------------------------------------------
                    # Layer 3: Freight corridors — orange heat
                    # ----------------------------------------------------------
                    {
                        "id": "freight_corridors_layer",
                        "type": "geojson",
                        "config": {
                            "dataId": "freight_corridors",
                            "label": "Freight Corridor Cost Impact",
                            "color": [255, 140, 0],
                            "columns": {"geojson": "_geojson"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.90,
                                "strokeOpacity": 1.0,
                                "thickness": 4.0,
                                "strokeColor": [255, 100, 0],
                                "colorRange": {
                                    "name": "Orange Heat",
                                    "type": "sequential",
                                    "category": "Uber",
                                    "colors": [
                                        "#FFECD2",
                                        "#FFD39B",
                                        "#FFB347",
                                        "#FF8C00",
                                        "#FF4500",
                                        "#B22222",
                                    ],
                                },
                                "stroked": True,
                                "filled": False,
                                "enable3d": False,
                            },
                            "colorField": {"name": "cost_impact_pct", "type": "real"},
                            "colorScale": "quantile",
                            "sizeField": {"name": "cost_impact_pct", "type": "real"},
                            "sizeScale": "linear",
                        },
                        "visualChannels": {
                            "colorField": {"name": "cost_impact_pct", "type": "real"},
                            "colorScale": "quantile",
                            "sizeField": {"name": "cost_impact_pct", "type": "real"},
                            "sizeScale": "linear",
                        },
                    },
                ],
                "interactionConfig": {
                    "tooltip": {
                        "fieldsToShow": {
                            "sa4_impact": [
                                {"name": "sa4_name", "format": None},
                                {"name": impact_field, "format": ".4f"},
                                {"name": "impact_score_wk4", "format": ".4f"},
                                {"name": "impact_score_wk26", "format": ".4f"},
                                {"name": "impact_score_wk52", "format": ".4f"},
                            ],
                            "route_arcs": [
                                {"name": "destination_name", "format": None},
                                {"name": "disruption_level", "format": None},
                                {"name": "arc_weight", "format": ".3f"},
                            ],
                            "freight_corridors": [
                                {"name": "name", "format": None},
                                {"name": "fuel_intensity", "format": None},
                                {"name": "cost_impact_pct", "format": ".2f"},
                            ],
                        },
                        "compareMode": False,
                        "compareType": "absolute",
                        "enabled": True,
                    },
                    "brush": {"size": 0.5, "enabled": False},
                    "geocoder": {"enabled": False},
                    "coordinate": {"enabled": True},
                },
                "layerBlending": "normal",
                "splitMaps": [],
                "animationConfig": {"currentTime": None, "speed": 1},
            },
            "mapState": {
                "bearing": 0,
                "dragRotate": False,
                "latitude": -27.47,
                "longitude": 153.02,
                "pitch": 0,
                "zoom": 9.5,
                "isSplit": False,
            },
            "mapStyle": {
                "styleType": "dark",
                "topLayerGroups": {},
                "visibleLayerGroups": {
                    "label": True,
                    "road": True,
                    "border": True,
                    "building": True,
                    "water": True,
                    "land": True,
                    "3d building": False,
                },
                "threeDBuildingColor": [9.665468314072013, 17.18305478057247, 31.1442867897876],
                "mapStyles": {},
            },
        },
    }
    return config


def get_snapshot_week_options() -> list[int]:
    return [4, 13, 26, 52]
