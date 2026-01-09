from __future__ import annotations

from typing import Tuple, Dict

import geopandas as gpd
import osmnx as ox
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

from .utils import PROJECTED_CRS


def fetch_boundary(osm_id: str = "R5167559", fallback_query: str = "Córdoba, Córdoba, Argentina") -> gpd.GeoDataFrame:
    """Fetch administrative boundary by OSM id (string like "R5167559").

    Returns GeoDataFrame in EPSG:4326.
    """
    try:
        gdf = ox.geocode_to_gdf(str(osm_id), by_osmid=True)
    except Exception:
        gdf = ox.geocode_to_gdf(fallback_query)
    # Normalize to polygons only
    gdf = gdf.explode(index_parts=False).reset_index(drop=True)
    return gdf.to_crs(4326)


def boundary_polygon_wgs84(boundary_gdf: gpd.GeoDataFrame) -> Polygon:
    """Return a single Polygon in EPSG:4326 representing the boundary.
    If multipolygon, pick the largest piece.
    """
    b = boundary_gdf.to_crs(4326)
    geom = unary_union(b.geometry.values)
    if isinstance(geom, MultiPolygon):
        parts = list(geom.geoms)
        return max(parts, key=lambda p: p.area)
    if isinstance(geom, Polygon):
        return geom
    raise ValueError(f"Boundary geometry not polygonal: {geom.geom_type}")


def validate_boundary(boundary_gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Dict]:
    """Validate and clean boundary geometry.

    - Fix self-intersections via buffer(0)
    - Remove empty/invalid parts
    - Return cleaned GeoDataFrame and a small validation report
    """
    gdf = boundary_gdf.copy()
    gdf["is_valid_before"] = gdf.is_valid

    # Attempt to fix invalid polygons
    gdf["geometry"] = gdf.geometry.buffer(0)
    gdf = gdf[gdf.geometry.notnull()].copy()
    gdf["is_valid_after"] = gdf.is_valid

    # Basic hole count estimation (per polygon interiors)
    def hole_count(geom):
        if isinstance(geom, Polygon):
            return len(geom.interiors)
        if isinstance(geom, MultiPolygon):
            return sum(len(p.interiors) for p in geom.geoms)
        return 0

    gdf["holes"] = gdf.geometry.apply(hole_count)

    report = {
        "valid_before": bool(gdf["is_valid_before"].all()) if len(gdf) else None,
        "valid_after": bool(gdf["is_valid_after"].all()) if len(gdf) else None,
        "total_holes": int(gdf["holes"].sum()) if len(gdf) else 0,
        "features": int(len(gdf)),
    }
    return gdf.drop(columns=["is_valid_before", "is_valid_after"]), report


def simplify_for_viz(boundary_gdf: gpd.GeoDataFrame, tolerance_m: float = 10.0) -> gpd.GeoDataFrame:
    """Simplify geometry for visualization only.
    The operation is done in projected CRS then returned to EPSG:4326.
    """
    gdf_proj = boundary_gdf.to_crs(PROJECTED_CRS)
    gdf_proj["geometry"] = gdf_proj.geometry.simplify(tolerance_m, preserve_topology=True)
    return gdf_proj.to_crs(4326)


def boundary_metadata(boundary_gdf: gpd.GeoDataFrame, projected_crs: int = PROJECTED_CRS) -> Dict:
    """Compute boundary metadata: area (km^2), CRS, and basic source fields if present."""
    proj = boundary_gdf.to_crs(projected_crs)
    area_km2 = float(proj.geometry.area.sum() / 1e6)
    md = {
        "crs_ingest": "EPSG:4326",
        "crs_analysis": f"EPSG:{projected_crs}",
        "area_km2": area_km2,
        "source": str(boundary_gdf.attrs.get("source", "OSM / OSMnx")),
    }
    return md
