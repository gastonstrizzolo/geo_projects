from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import osmnx as ox


# Default projected CRS: WGS84 / UTM zone 20S (Córdoba)
PROJECTED_CRS = 32720


def project_root() -> Path:
    """Return the project root directory (city-boundary-dashboard)."""
    return Path(__file__).resolve().parents[1]


def data_paths() -> dict[str, Path]:
    root = project_root()
    data = root / "data"
    return {
        "root": data,
        "raw": data / "raw",
        "processed": data / "processed",
        "outputs": data / "outputs",
    }


def ensure_dir(path: Path | str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def set_overpass(endpoint: Optional[str] = None, use_cache: bool = True) -> None:
    """Configure OSMnx Overpass and cache settings.

    If endpoint is None, keep OSMnx default. If requests fail upstream,
    caller may switch to a public mirror like "https://overpass.kumi.systems/api".
    """
    ox.settings.use_cache = use_cache
    if endpoint:
        ox.settings.overpass_endpoint = endpoint


def write_json(obj: dict, path: Path | str) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_neighborhoods_from_kml(kml_path: str | Path) -> "gpd.GeoDataFrame":
    """Load neighborhood polygons from KML file.
    
    Parameters:
        kml_path: Path to KML file (e.g., data/raw/neighborhoods.kml)
    
    Returns:
        GeoDataFrame with neighborhood geometries in WGS84 (EPSG:4326)
    """
    import geopandas as gpd
    kml_path = Path(kml_path)
    if not kml_path.exists():
        raise FileNotFoundError(f"KML file not found: {kml_path}")
    
    gdf = gpd.read_file(kml_path, driver='KML')
    gdf = gdf.to_crs(4326)
    return gdf
