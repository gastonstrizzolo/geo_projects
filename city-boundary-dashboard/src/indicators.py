from __future__ import annotations

from typing import Dict, List, Tuple

import geopandas as gpd
import osmnx as ox
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, box

from .utils import PROJECTED_CRS


DEFAULT_POI_TAGS: Dict[str, object] = {
    "amenity": ["school", "hospital", "pharmacy", "restaurant", "cafe", 
                "bank", "post_office", "library", "police", "fire_station",
                "clinic", "dentist", "fuel", "parking", "place_of_worship"],
    "leisure": ["park", "playground", "sports_centre"],
    "shop": ["supermarket", "convenience", "bakery", "clothes"],
}


def fetch_pois_within_boundary(polygon_wgs84: Polygon, tags: Dict[str, object] | None = None) -> gpd.GeoDataFrame:
    """Fetch POIs (points) from OSM within the polygon in WGS84."""
    tags = tags or DEFAULT_POI_TAGS
    gdf = ox.features_from_polygon(polygon_wgs84, tags=tags)
    if gdf.empty:
        return gdf
    # Keep points only
    return gdf[gdf.geometry.type.isin(["Point", "MultiPoint"])].copy()


def categorize_pois(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Assign category string from amenity/leisure tags."""
    if gdf.empty:
        return gdf
    preferred = ["amenity", "leisure"]

    def pick(row):
        for k in preferred:
            v = row.get(k)
            if pd.notna(v):
                return f"{k}:{v}" if v is not True else k
        return "unknown"

    gdf = gdf.copy()
    gdf["category"] = gdf.apply(pick, axis=1)
    return gdf


def compute_poi_density(pois_gdf: gpd.GeoDataFrame, boundary_gdf: gpd.GeoDataFrame, projected_crs: int = PROJECTED_CRS) -> pd.DataFrame:
    """Compute counts and density (per km^2) per category."""
    if pois_gdf.empty:
        return pd.DataFrame(columns=["category", "count", "density_per_km2"])

    boundary_area_km2 = float(boundary_gdf.to_crs(projected_crs).geometry.area.sum() / 1e6)
    counts = pois_gdf.groupby("category").size().reset_index(name="count")
    counts["density_per_km2"] = counts["count"] / boundary_area_km2 if boundary_area_km2 > 0 else 0
    return counts.sort_values("count", ascending=False)


def make_square_grid(boundary_gdf: gpd.GeoDataFrame, cell_size_m: float = 500.0, projected_crs: int = PROJECTED_CRS) -> gpd.GeoDataFrame:
    """Generate a square grid covering the boundary, clipped to the boundary."""
    boundary_proj = boundary_gdf.to_crs(projected_crs)
    minx, miny, maxx, maxy = boundary_proj.total_bounds

    full_cell_area_km2 = (cell_size_m * cell_size_m) / 1e6  # area of full square cell before clipping

    squares = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            squares.append(box(x, y, x + cell_size_m, y + cell_size_m))
            y += cell_size_m
        x += cell_size_m

    grid = gpd.GeoDataFrame(geometry=squares, crs=projected_crs)
    grid = gpd.overlay(grid, boundary_proj, how="intersection")
    grid["area_km2"] = grid.geometry.area / 1e6
    grid["cell_area_km2_full"] = full_cell_area_km2
    grid["coverage_ratio"] = grid["area_km2"] / grid["cell_area_km2_full"]
    grid = grid[grid["area_km2"] > 0].reset_index(drop=True)
    grid["cell_id"] = grid.index.astype(int)
    return grid


def aggregate_pois_to_grid(
    pois_gdf: gpd.GeoDataFrame,
    grid_gdf: gpd.GeoDataFrame,
    projected_crs: int = PROJECTED_CRS,
) -> gpd.GeoDataFrame:
    """Aggregate POI counts to grid cells and compute density per km^2."""
    if pois_gdf.empty or grid_gdf.empty:
        return gpd.GeoDataFrame(columns=["cell_id", "count", "density_per_km2", "geometry"], crs=grid_gdf.crs)

    pois_proj = pois_gdf.to_crs(projected_crs)
    grid_proj = grid_gdf.to_crs(projected_crs)

    joined = gpd.sjoin(pois_proj, grid_proj[["cell_id", "geometry"]], how="inner", predicate="within")
    counts = joined.groupby("cell_id").size().reset_index(name="count")
    grid_proj = grid_proj.merge(counts, on="cell_id", how="left")
    grid_proj["count"] = grid_proj["count"].fillna(0).astype(int)
    grid_proj["density_per_km2"] = grid_proj["count"] / grid_proj["cell_area_km2_full"]
    return grid_proj


def fetch_street_network(polygon_wgs84: Polygon, network_type: str = "walk"):
    """Fetch street network graph from OSM within polygon (WGS84).
    
    Parameters:
        polygon_wgs84: boundary polygon in EPSG:4326
        network_type: 'walk', 'bike', 'drive', 'drive_service', 'all'
    
    Returns NetworkX MultiDiGraph from OSMnx.
    """
    return ox.graph_from_polygon(polygon_wgs84, network_type=network_type)


def fetch_buildings_within_boundary(polygon_wgs84: Polygon) -> gpd.GeoDataFrame:
    """Fetch building footprints from OSM within polygon (WGS84)."""
    import logging
    log = logging.getLogger(__name__)
    
    tags = {"building": True}
    gdf = ox.features_from_polygon(polygon_wgs84, tags=tags)
    
    # Debug inspection
    if not gdf.empty:
        log.info("=== BUILDING GDF DEBUG ===")
        log.info(f"Shape: {gdf.shape}")
        log.info(f"CRS: {gdf.crs}")
        log.info(f"Columns ({len(gdf.columns)}): {list(gdf.columns)}")
        log.info(f"Geometry types: {gdf.geometry.type.value_counts().to_dict()}")
        log.info(f"Building tag sample: {gdf['building'].value_counts().head(10).to_dict()}")
        log.info(f"Columns with colons: {[c for c in gdf.columns if ':' in str(c)]}")
        log.info("=== END DEBUG ===")
    
    if gdf.empty:
        return gdf
    # Keep only polygonal geometries
    return gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()


def aggregate_buildings_to_grid(
    buildings_gdf: gpd.GeoDataFrame,
    grid_gdf: gpd.GeoDataFrame,
    projected_crs: int = PROJECTED_CRS,
) -> gpd.GeoDataFrame:
    """Aggregate building footprints to grid cells.
    
    Computes:
    - building_count: number of buildings per cell
    - building_area_km2: total building footprint area in km²
    - building_density: buildings per km² of cell area
    - footprint_coverage: % of cell area covered by buildings
    """
    if buildings_gdf.empty or grid_gdf.empty:
        grid_out = grid_gdf.copy()
        grid_out["building_count"] = 0
        grid_out["building_area_km2"] = 0.0
        grid_out["building_density"] = 0.0
        grid_out["footprint_coverage"] = 0.0
        return grid_out

    buildings_proj = buildings_gdf.to_crs(projected_crs)
    grid_proj = grid_gdf.to_crs(projected_crs)

    # Compute building areas
    buildings_proj["building_area_km2"] = buildings_proj.geometry.area / 1e6

    # Use building centroids for cell assignment (one building = one cell)
    # to avoid double-counting buildings that cross cell boundaries
    buildings_centroids = buildings_proj.copy()
    buildings_centroids['geometry'] = buildings_proj.geometry.centroid
    
    # Spatial join building centroids to grid (each building assigned to exactly one cell)
    joined = gpd.sjoin(buildings_centroids, grid_proj[["cell_id", "geometry"]], how="inner", predicate="within")
    
    # Aggregate by cell
    agg = joined.groupby("cell_id").agg({
        "building_area_km2": "sum",
        "geometry": "count"  # count buildings
    }).rename(columns={"geometry": "building_count"}).reset_index()

    grid_proj = grid_proj.merge(agg, on="cell_id", how="left")
    grid_proj["building_count"] = grid_proj["building_count"].fillna(0).astype(int)
    grid_proj["building_area_km2"] = grid_proj["building_area_km2"].fillna(0.0)
    # Use full cell area (pre-clip) to avoid inflated densities on sliver cells
    if "cell_area_km2_full" in grid_proj.columns:
        denom_area = grid_proj["cell_area_km2_full"]
    else:
        denom_area = grid_proj["area_km2"]

    grid_proj["building_density"] = grid_proj["building_count"] / denom_area.replace(0, np.nan)
    grid_proj["building_density"] = grid_proj["building_density"].fillna(0)

    grid_proj["footprint_coverage"] = (grid_proj["building_area_km2"] / denom_area * 100).fillna(0)
    
    return grid_proj
