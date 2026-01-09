from __future__ import annotations

from typing import Tuple, List, Dict

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry import Polygon

from .utils import PROJECTED_CRS


DEFAULT_LANDUSE_TAGS: Dict[str, object] = {
    "landuse": True,
    "natural": True,
    "leisure": ["park", "garden", "recreation_ground"],
    "landcover": True,
}


def fetch_landuse(polygon_wgs84: Polygon, tags: Dict[str, object] | None = None) -> gpd.GeoDataFrame:
    """Fetch landuse/landcover features from OSM within polygon (WGS84)."""
    tags = tags or DEFAULT_LANDUSE_TAGS
    gdf = ox.features_from_polygon(polygon_wgs84, tags=tags)
    if gdf.empty:
        return gdf
    # Keep only area-like geometries
    return gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()


def clip_and_project(gdf: gpd.GeoDataFrame, boundary_wgs84: gpd.GeoDataFrame, projected_crs: int = PROJECTED_CRS) -> gpd.GeoDataFrame:
    """Clip to boundary (in WGS84), then project for area computations."""
    if gdf.empty:
        return gdf
    clipped = gpd.clip(gdf.to_crs(4326), boundary_wgs84.to_crs(4326))
    if clipped.empty:
        return clipped
    proj = clipped.to_crs(projected_crs)
    proj["area_km2"] = proj.geometry.area / 1e6
    return proj


def classify_landuse(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Assign a simple category column from the first available tag."""
    if gdf.empty:
        return gdf
    preferred = ["landuse", "natural", "leisure", "landcover"]

    def pick(row):
        for k in preferred:
            v = row.get(k)
            if pd.notna(v):
                return f"{k}:{v}" if v is not True else k
        return "unknown"

    gdf = gdf.copy()
    gdf["category"] = gdf.apply(pick, axis=1)
    return gdf


def summarize_landuse(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Summarize area by category (expects projected gdf with area_km2)."""
    if gdf.empty:
        return pd.DataFrame(columns=["category", "area_km2"])  # empty
    return (
        gdf.groupby("category", dropna=False)["area_km2"].sum().reset_index().sort_values("area_km2", ascending=False)
    )
