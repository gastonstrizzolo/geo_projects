from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

import geopandas as gpd
import osmnx as ox

# Allow running this file directly: python src/pipeline.py
# by adding the project root to sys.path for absolute imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils import PROJECTED_CRS, data_paths, ensure_dir, set_overpass, write_json
from src.boundaries import (
    fetch_boundary,
    validate_boundary,
    boundary_polygon_wgs84,
    simplify_for_viz,
    boundary_metadata,
)
from src.landuse import fetch_landuse, clip_and_project, classify_landuse, summarize_landuse
from src.indicators import (
    fetch_pois_within_boundary,
    categorize_pois,
    compute_poi_density,
    make_square_grid,
    aggregate_pois_to_grid,
    fetch_street_network,
    fetch_buildings_within_boundary,
    aggregate_buildings_to_grid,
)
from src.visualization import plot_boundary, plot_landuse_overview, plot_poi_overview, plot_poi_grid_density, plot_grid_with_streets, plot_building_density


def run(osm_id: str = "R5167559", grid_size_m: float = 500.0) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("pipeline")

    paths = data_paths()
    ensure_dir(paths["processed"])
    ensure_dir(paths["outputs"])

    # Configure OSMnx (cache; default endpoint)
    set_overpass(use_cache=True)
    log.info("Starting pipeline for OSM id %s", osm_id)

    # 1) Boundary
    log.info("Fetching boundary")
    boundary = fetch_boundary(osm_id=osm_id)
    boundary, val_report = validate_boundary(boundary)
    meta = boundary_metadata(boundary, projected_crs=PROJECTED_CRS)
    meta.update({"validation": val_report})
    log.info("Boundary fetched; valid_after=%s holes=%s", val_report.get("valid_after"), val_report.get("total_holes"))

    # Save boundary overview plot (simplified for viz)
    boundary_viz = simplify_for_viz(boundary, tolerance_m=10.0)
    plot_boundary(boundary_viz, paths["outputs"] / "cordoba_boundary.png", title="Córdoba Boundary (OSM)")
    log.info("Boundary plot saved to %s", paths["outputs"] / "cordoba_boundary.png")

    # Save metadata
    write_json(meta, paths["outputs"] / "boundary_metadata.json")
    log.info("Boundary metadata saved to %s", paths["outputs"] / "boundary_metadata.json")

    # 2) Landuse
    log.info("Fetching landuse features")
    polygon = boundary_polygon_wgs84(boundary)

    try:
        lu_raw = fetch_landuse(polygon)
    except Exception:
        # Switch endpoint and retry once if Overpass hiccups
        set_overpass(endpoint="https://overpass.kumi.systems/api", use_cache=True)
        lu_raw = fetch_landuse(polygon)

    if lu_raw.empty:
        log.warning("No landuse features returned by Overpass.")
        return

    lu = clip_and_project(lu_raw, boundary, projected_crs=PROJECTED_CRS)
    if lu.empty:
        log.warning("Landuse features clipped to empty set.")
        return

    # Filter to polygon geometries only (remove any linestrings)
    before_count = len(lu)
    lu = lu[lu.geom_type.isin(['Polygon', 'MultiPolygon'])].copy()
    if len(lu) < before_count:
        log.info("Filtered landuse: kept %d polygon features, dropped %d non-polygon features", len(lu), before_count - len(lu))

    lu = classify_landuse(lu)
    summary = summarize_landuse(lu)

    # Outputs
    gpkg_path = paths["processed"] / "landuse.gpkg"
    lu.to_file(gpkg_path, layer="landuse", driver="GPKG")
    log.info("Landuse written to %s", gpkg_path)

    csv_path = paths["outputs"] / "landuse_summary.csv"
    summary.to_csv(csv_path, index=False)
    log.info("Landuse summary written to %s", csv_path)

    plot_landuse_overview(lu, boundary, paths["outputs"] / "landuse_overview.png", title="Landuse dentro del límite de Córdoba (OSM)")
    log.info("Landuse plot saved to %s", paths["outputs"] / "landuse_overview.png")

    # 3) POIs (amenity/leisure)
    log.info("Fetching POIs (amenity/leisure)")
    try:
        pois_raw = fetch_pois_within_boundary(polygon)
    except Exception:
        set_overpass(endpoint="https://overpass.kumi.systems/api", use_cache=True)
        pois_raw = fetch_pois_within_boundary(polygon)

    if pois_raw.empty:
        log.warning("No POIs returned by Overpass for the given tags.")
        return

    pois = categorize_pois(pois_raw)
    # Convert to projected CRS
    pois = pois.to_crs(PROJECTED_CRS)
    log.info("POIs converted to CRS EPSG:%d", PROJECTED_CRS)
    
    # Keep only safe columns for GPKG export
    safe_cols = ["geometry", "category", "name"]
    existing_safe = [c for c in safe_cols if c in pois.columns]
    dropped = [c for c in pois.columns if c not in existing_safe]
    pois = pois[existing_safe].copy()
    if dropped:
        log.info("Dropped POI columns for export due to compatibility: %s", ", ".join(dropped))

    poi_summary = compute_poi_density(pois, boundary, projected_crs=PROJECTED_CRS)

    gpkg_pois = paths["processed"] / "pois.gpkg"
    pois.to_file(gpkg_pois, layer="pois", driver="GPKG")
    log.info("POIs written to %s", gpkg_pois)

    csv_pois = paths["outputs"] / "poi_summary.csv"
    poi_summary.to_csv(csv_pois, index=False)
    log.info("POI summary written to %s", csv_pois)

    plot_poi_overview(pois, boundary, paths["outputs"] / "poi_overview.png", title="POIs dentro del límite de Córdoba (OSM)")
    log.info("POI plot saved to %s", paths["outputs"] / "poi_overview.png")

    # 4) POI grid density (square)
    log.info("Building square grid (cell size %.0f m) and aggregating POI density", grid_size_m)
    grid = make_square_grid(boundary, cell_size_m=grid_size_m, projected_crs=PROJECTED_CRS)
    if grid.empty:
        log.warning("Hex grid construction returned empty.")
        return
    grid = aggregate_pois_to_grid(pois, grid, projected_crs=PROJECTED_CRS)

    gpkg_grid = paths["processed"] / "poi_grid.gpkg"
    grid.to_file(gpkg_grid, layer="poi_grid", driver="GPKG")
    log.info("POI grid written to %s", gpkg_grid)

    csv_grid = paths["outputs"] / "poi_grid_summary.csv"
    grid[["cell_id", "area_km2", "count", "density_per_km2"]].to_csv(csv_grid, index=False)
    log.info("POI grid summary written to %s", csv_grid)

    plot_poi_grid_density(grid, boundary, paths["outputs"] / "poi_grid.png", title="Densidad de POIs (por km²)")
    log.info("POI grid plot saved to %s", paths["outputs"] / "poi_grid.png")

    # 5) POI grid with street network
    log.info("Fetching street network and generating street-overlay plot")
    try:
        street_graph = fetch_street_network(polygon, network_type="walk")
        log.info("Street graph fetched: %d nodes, %d edges", street_graph.number_of_nodes(), street_graph.number_of_edges())
        
        # Save graph as GraphML (preserves topology)
        graphml_path = paths["processed"] / "street_network.graphml"
        ox.save_graphml(street_graph, graphml_path)
        log.info("Street network graph saved to %s", graphml_path)
        
        # Save edges and nodes as GeoPackage (easier for GIS inspection)
        nodes, edges = ox.graph_to_gdfs(street_graph)
        # Convert to projected CRS
        edges = edges.to_crs(PROJECTED_CRS)
        nodes = nodes.to_crs(PROJECTED_CRS)
        log.info("Street network converted to CRS EPSG:%d", PROJECTED_CRS)
        
        edges_path = paths["processed"] / "street_edges.gpkg"
        nodes_path = paths["processed"] / "street_nodes.gpkg"
        edges.to_file(edges_path, layer="edges", driver="GPKG")
        nodes.to_file(nodes_path, layer="nodes", driver="GPKG")
        log.info("Street edges saved to %s", edges_path)
        log.info("Street nodes saved to %s", nodes_path)
        
        plot_grid_with_streets(grid, boundary, street_graph, paths["outputs"] / "poi_grid_with_streets.png", title="Densidad de POIs con Red Vial")
        log.info("POI grid with streets plot saved to %s", paths["outputs"] / "poi_grid_with_streets.png")
    except Exception as e:
        log.warning("Failed to fetch street network or generate street overlay: %s", e)

    # 6) Buildings analysis
    log.info("Fetching building footprints")
    try:
        buildings_raw = fetch_buildings_within_boundary(polygon)
    except Exception:
        set_overpass(endpoint="https://overpass.kumi.systems/api", use_cache=True)
        buildings_raw = fetch_buildings_within_boundary(polygon)

    if buildings_raw.empty:
        log.warning("No building footprints returned by Overpass.")
    else:
        log.info("Fetched %d building footprints", len(buildings_raw))

        # Sanitize column names and keep a safe subset for GPKG export
        buildings_clean = buildings_raw.copy()
        renamed = {c: c.replace(":", "_") for c in buildings_clean.columns if ":" in c}
        if renamed:
            buildings_clean = buildings_clean.rename(columns=renamed)
            log.info("Renamed building columns for export: %s", ", ".join(f"{k}->{v}" for k, v in renamed.items()))

        safe_cols = [
            "geometry",
            "building",
            "name",
            "building_levels",
            "building_material",
            "addr_housenumber",
            "addr_street",
            "addr_city",
            "addr_postcode",
            "addr_suburb",
            "addr_province",
            "addr_country",
        ]
        existing_safe = [c for c in safe_cols if c in buildings_clean.columns]
        if not existing_safe:
            existing_safe = ["geometry"]
        dropped = [c for c in buildings_clean.columns if c not in existing_safe]
        if dropped:
            log.info("Dropping %d building columns not in safe list (e.g., %s)", len(dropped), dropped[:3])
        buildings_clean = buildings_clean[existing_safe].copy()
        
        # Convert to projected CRS
        buildings_clean = buildings_clean.to_crs(PROJECTED_CRS)
        log.info("Buildings converted to CRS EPSG:%d", PROJECTED_CRS)
        
        # Aggregate to grid
        building_grid = aggregate_buildings_to_grid(buildings_clean, grid, projected_crs=PROJECTED_CRS)
        
        # Save outputs
        gpkg_buildings = paths["processed"] / "buildings.gpkg"
        buildings_clean.to_file(gpkg_buildings, layer="buildings", driver="GPKG")
        log.info("Buildings saved to %s", gpkg_buildings)
        
        gpkg_building_grid = paths["processed"] / "building_grid.gpkg"
        building_grid.to_file(gpkg_building_grid, layer="building_grid", driver="GPKG")
        log.info("Building grid saved to %s", gpkg_building_grid)
        
        csv_building = paths["outputs"] / "building_summary.csv"
        building_grid[["cell_id", "area_km2", "building_count", "building_area_km2", "building_density", "footprint_coverage"]].to_csv(csv_building, index=False)
        log.info("Building summary written to %s", csv_building)
        
        plot_building_density(building_grid, boundary, paths["outputs"] / "building_density.png", title="Densidad de Edificios (por km²)")
        log.info("Building density plot saved to %s", paths["outputs"] / "building_density.png")


if __name__ == "__main__":
    run()
