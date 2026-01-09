from __future__ import annotations

import os
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


def plot_boundary(boundary_gdf: gpd.GeoDataFrame, output_path: str | Path, title: str = "Boundary") -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ax = boundary_gdf.plot()
    plt.title(title)
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_landuse_overview(
    landuse_gdf: gpd.GeoDataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    output_path: str | Path,
    title: str = "Landuse Overview",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    # landuse layer without built-in legend
    lu_wgs = landuse_gdf.to_crs(4326)
    lu_wgs.plot(column="category", legend=False, alpha=0.6, ax=ax, cmap="tab20")
    boundary_gdf.to_crs(4326).boundary.plot(ax=ax, color="black", linewidth=1)
    plt.title(title)

    # manual legend
    categories = sorted(lu_wgs["category"].unique())
    colors = plt.cm.tab20(range(len(categories)))
    legend_elements = [Patch(facecolor=colors[i], label=cat, alpha=0.6) for i, cat in enumerate(categories)]
    ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc="upper left", frameon=True)

    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_poi_overview(
    pois_gdf: gpd.GeoDataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    output_path: str | Path,
    title: str = "POIs Overview",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    pois_wgs = pois_gdf.to_crs(4326)

    # Scatter plot with categories
    categories = sorted(pois_wgs["category"].unique())
    colors = plt.cm.tab20(range(len(categories)))
    for i, cat in enumerate(categories):
        subset = pois_wgs[pois_wgs["category"] == cat]
        subset.plot(ax=ax, color=colors[i], markersize=10, label=cat, alpha=0.7)

    boundary_gdf.to_crs(4326).boundary.plot(ax=ax, color="black", linewidth=1)
    plt.title(title)

    # Manual legend outside
    from matplotlib.lines import Line2D

    legend_elements = [Line2D([0], [0], marker='o', color='w', label=cat,
                              markerfacecolor=colors[i], markersize=8, alpha=0.9)
                       for i, cat in enumerate(categories)]
    ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc="upper left", frameon=True)

    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_poi_grid_density(
    grid_gdf: gpd.GeoDataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    output_path: str | Path,
    title: str = "POI Density (per km²)",
    column: str = "density_per_km2",
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    grid_gdf.plot(column=column, cmap="OrRd", legend=True, ax=ax, edgecolor="none")
    boundary_gdf.to_crs(grid_gdf.crs).boundary.plot(ax=ax, color="black", linewidth=0.8)
    plt.title(title)

    # Adjust legend outside
    if ax.get_legend():
        ax.get_legend().set_bbox_to_anchor((1.05, 1))
        ax.get_legend()._loc = 2

    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_grid_with_streets(
    grid_gdf: gpd.GeoDataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    street_graph,
    output_path: str | Path,
    title: str = "POI Density with Street Network",
    column: str = "density_per_km2",
) -> None:
    """Plot grid density with street network as background context."""
    import osmnx as ox
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Convert graph to GeoDataFrame edges
    edges = ox.graph_to_gdfs(street_graph, nodes=False)
    # Use grid CRS as reference
    edges_proj = edges.to_crs(grid_gdf.crs)
    
    # 1. Street network background (darker, visible)
    edges_proj.plot(ax=ax, color="#555555", linewidth=0.8, zorder=1, alpha=0.6)
    
    # 2. Grid density overlay (semi-transparent)
    grid_gdf.plot(column=column, cmap="YlOrRd", legend=True, ax=ax, 
                  edgecolor="white", linewidth=0.1, alpha=0.6, zorder=2)
    
    # 3. Boundary outline (on top)
    boundary_gdf.to_crs(grid_gdf.crs).boundary.plot(ax=ax, color="black", linewidth=2, zorder=3)
    
    plt.title(title)
    
    # Adjust legend
    if ax.get_legend():
        ax.get_legend().set_bbox_to_anchor((1.05, 1))
        ax.get_legend()._loc = 2
    
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_building_density(
    grid_gdf: gpd.GeoDataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    output_path: str | Path,
    title: str = "Building Density (per km²)",
    column: str = "building_density",
) -> None:
    """Plot building density grid with boundary."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    grid_gdf.plot(column=column, cmap="Blues", legend=True, ax=ax, edgecolor="none")
    boundary_gdf.to_crs(grid_gdf.crs).boundary.plot(ax=ax, color="black", linewidth=0.8)
    plt.title(title)

    # Adjust legend outside
    if ax.get_legend():
        ax.get_legend().set_bbox_to_anchor((1.05, 1))
        ax.get_legend()._loc = 2

    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
