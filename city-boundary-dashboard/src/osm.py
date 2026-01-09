import geopandas as gpd 
import osmnx as ox
import os as os 
import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
import pandas as pd

CORDOBA_OSMID = "R5167559"  # OSM relation id must be a string when by_osmid=True
PROJECTED_CRS = 32720  # WGS84 / UTM zone 20S (Argentina, Córdoba)

def fetch_cordoba_boundary():
    try:
        # Ensure we pass a string OSM id (e.g., "R5167559" for relation)
        gdf = ox.geocode_to_gdf(str(CORDOBA_OSMID), by_osmid=True)
    except Exception as e:
        print(f"Error al geocodificar Córdoba: {e}")
        gdf = ox.geocode_to_gdf(
            "Córdoba, Córdoba, Argentina"
        )
    return gdf

def _boundary_polygon_wgs84(boundary_gdf: gpd.GeoDataFrame):
    b_wgs = boundary_gdf.to_crs(4326)
    geom = b_wgs.union_all()
    if geom.geom_type == "MultiPolygon":
        parts = list(geom.geoms)
        polygon = max(parts, key=lambda p: p.area)
    elif geom.geom_type == "Polygon":
        polygon = geom
    else:
        raise ValueError(f"Boundary geometry not polygonal: {geom.geom_type}")
    return polygon

def fetch_landuse_within_boundary(boundary_gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    tags = {
        "landuse": True,          # any landuse value
        "natural": True,          # wood, grassland, scrub, etc.
        "leisure": ["park", "garden", "recreation_ground"],
        "landcover": True         # grass, trees, etc. (if present)
    }
    ox.settings.use_cache = True

    polygon = _boundary_polygon_wgs84(boundary_gdf)
    try:
        lu = ox.features_from_polygon(polygon, tags=tags)
    except Exception as e:
        print(f"Overpass error, retrying with alt endpoint: {e}")
        ox.settings.overpass_endpoint = "https://overpass.kumi.systems/api"
        lu = ox.features_from_polygon(polygon, tags=tags)
    if lu.empty:
        print("Sin resultados de landuse/natural/leisure en OSM para el polígono.")
        return lu, pd.DataFrame()
    
    print(f"Landuse features obtenidas: {len(lu)}")

    # Keep area features only
    lu = lu[lu.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    # Clip to boundary
    lu = gpd.clip(lu.to_crs(4326), boundary_gdf.to_crs(4326))

    # Project for area calculations
    lu_proj = lu.to_crs(PROJECTED_CRS)
    lu_proj["area_km2"] = lu_proj.area / 1_000_000.0

    # Simple classification from the first non-null tag
    def classify(row):
        for k in ["landuse", "natural", "leisure", "landcover"]:
            v = row.get(k)
            if pd.notna(v):
                return f"{k}:{v}" if v is not True else k
        return "unknown"
    lu_proj["category"] = lu_proj.apply(classify, axis=1)

    # Summary by category
    summary = (
        lu_proj.groupby("category", dropna=False)["area_km2"]
        .sum()
        .reset_index()
        .sort_values("area_km2", ascending=False)
    )
    return lu_proj, summary

def plot_boundary(boundary_gdf: gpd.GeoDataFrame, output_path: str, title: str = "Boundary"):
    """Plot and save boundary to file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ax = boundary_gdf.plot()
    plt.title(title)
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Plot guardado en: {output_path}")

def plot_landuse_overview(
    landuse_gdf: gpd.GeoDataFrame,
    boundary_gdf: gpd.GeoDataFrame,
    output_path: str,
    title: str = "Landuse Overview"
):
    """Plot landuse with boundary overlay and external legend."""
    from matplotlib.patches import Patch
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot landuse without legend
    landuse_gdf.to_crs(4326).plot(
        column="category",
        legend=False,
        alpha=0.6,
        ax=ax,
        cmap='tab20'
    )
    
    # Plot boundary
    boundary_gdf.to_crs(4326).boundary.plot(
        ax=ax,
        color="black",
        linewidth=1
    )
    
    plt.title(title)
    
    # Create manual legend with matching colors
    categories = sorted(landuse_gdf["category"].unique())
    colors = plt.cm.tab20(range(len(categories)))
    legend_elements = [
        Patch(facecolor=colors[i], label=cat, alpha=0.6)
        for i, cat in enumerate(categories)
    ]
    ax.legend(
        handles=legend_elements,
        bbox_to_anchor=(1.05, 1),
        loc='upper left',
        frameon=True
    )
    
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Plot guardado en: {output_path}")

# Main execution
gdf = fetch_cordoba_boundary()

# Plot boundary
plot_boundary(
    gdf,
    output_path="../data/outputs/cordoba_boundary.png",
    title="Córdoba Boundary (OSM)"
)

# Debug polygon info
polygon_wgs84 = _boundary_polygon_wgs84(gdf)
print("Polígono WGS84 obtenido:")
print(f"  Tipo: {polygon_wgs84.geom_type}")
print(f"  Área (grados²): {polygon_wgs84.area:.6f}")
print(f"  Vértices: {len(polygon_wgs84.exterior.coords)}")

# Landuse analysis
os.makedirs("../data/processed", exist_ok=True)
landuse_gdf, landuse_summary = fetch_landuse_within_boundary(gdf)

if not landuse_gdf.empty:
    # Save outputs
    gpkg_path = "../data/processed/landuse.gpkg"
    landuse_gdf.to_file(gpkg_path, layer="landuse", driver="GPKG")
    print(f"Landuse guardado en: {gpkg_path}")

    csv_path = "../data/outputs/landuse_summary.csv"
    landuse_summary.to_csv(csv_path, index=False)
    print(f"Resumen guardado en: {csv_path}")

    # Plot landuse overview
    plot_landuse_overview(
        landuse_gdf,
        gdf,
        output_path="../data/outputs/landuse_overview.png",
        title="Landuse dentro del límite de Córdoba (OSM)"
    )
else:
    print("No se generaron capas de landuse para exportar.")
