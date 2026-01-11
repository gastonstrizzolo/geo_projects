# 🗺️ City Boundary Intelligence Dashboard

**Urban Spatial Analysis with GeoPandas & OpenStreetMap**

## Overview

The **City Boundary Intelligence Dashboard** is a geospatial analysis project designed to explore how land use, infrastructure, and population are distributed within official administrative city boundaries.

Using **OpenStreetMap** as the primary data source and **GeoPandas** for spatial analysis, the project builds a **reproducible pipeline** to extract, validate, analyze, and visualize urban spatial indicators at the city and neighborhood scale.

The initial case study focuses on **Córdoba, Argentina**, but the architecture is designed to be easily extended to other cities.

### Quick start

```
source geo/bin/activate
python3 src/pipeline.py              # default: Córdoba, EPSG:32720, 500m square grid
# customize grid size (meters)
python3 -c "from src.pipeline import run; run(grid_size_m=300)"
```

Generated outputs (after running the pipeline):

- data/outputs/boundary_metadata.json
- data/outputs/cordoba_boundary.png
- data/outputs/landuse_summary.csv
- data/outputs/landuse_overview.png
- data/outputs/poi_summary.csv
- data/outputs/poi_overview.png
- data/outputs/poi_grid_summary.csv
- data/outputs/poi_grid.png
- data/processed/landuse.gpkg
- data/processed/pois.gpkg
- data/processed/poi_grid.gpkg

---

## Objectives

* Retrieve authoritative city boundaries from OpenStreetMap using relation IDs
* Integrate land-use, infrastructure, and (optionally) demographic data
* Compute spatial indicators such as:

  * Land-use composition
  * Infrastructure density
  * Service accessibility
* Produce maps and tabular outputs suitable for analysis, reporting, or dashboards
* Explicitly document spatial assumptions, limitations, and data quality issues

---

## Research Questions

1. How is land use distributed within the city boundary?
2. How evenly are public services and infrastructure distributed?
3. Which areas show potential under-service or imbalance?
4. How sensitive are results to CRS choice and boundary definitions?

---

## Geographic Scope

**Primary case study**

* City: **Córdoba, Argentina**
* Administrative boundary:

  * OpenStreetMap relation **5167559**
  * `boundary=administrative`
  * `admin_level=8` (city)

The project can be extended to:

* Other Argentine cities
* Provincial boundaries (`admin_level=4`)
* Cross-city comparisons

---

## Data Sources

### OpenStreetMap (via OSMnx / Overpass)

* Administrative boundaries
* Land-use polygons
* Buildings
* Points of Interest (POIs):

  * Schools
  * Hospitals
  * Parks
  * Pharmacies

Key OSM tags used:

* `boundary=administrative`
* `landuse=*`
* `amenity=*`
* `building=*`

### Optional Official Data

* **INDEC (Argentina)**: population and census data
* **IGN Argentina**: CRS definitions and reference layers

---

## Tech Stack

* Python 3.11+
* GeoPandas
* Shapely
* PyProj
* OSMnx
* Pandas
* Matplotlib / Folium

Optional:

* DuckDB / Parquet for performance
* Jupyter Notebooks for exploration

---

## Coordinate Reference System (CRS) Strategy

* **Data ingestion:** WGS84 (`EPSG:4326`)
* **Analysis CRS (current default):** WGS84 / UTM zone 20S (`EPSG:32720`)
* **Future option:** POSGAR / Gauss-Krüger zone covering Córdoba

> ⚠️ All area, distance, and density calculations are performed in a **projected CRS**, never in latitude/longitude.

---

## Project Structure

```
city-boundary-dashboard/
├── data/
│   ├── raw/            # Unmodified source data
│   ├── processed/      # Cleaned and projected layers
│   └── outputs/        # Final tables and spatial outputs
├── notebooks/
│   ├── 01_exploration.ipynb
│   ├── 02_validation.ipynb
│   └── 03_analysis.ipynb
├── src/
│   ├── osm.py          # OSM data acquisition
│   ├── boundaries.py  # Boundary handling & validation
│   ├── landuse.py     # Land-use processing
│   ├── indicators.py  # Spatial metrics & indicators
│   └── visualization.py
├── README.md
└── environment.yml
```

---

## Analysis Pipeline

### 1. Boundary Acquisition & Validation

* Fetch city boundary using OSM relation ID
* Validate geometry (self-intersections, holes)
* Simplify geometry **only for visualization**

**Outputs**

* Clean city polygon
* Metadata summary (area, CRS, source)

---

### 2. Land-Use Analysis

* Download land-use polygons
* Clip to city boundary
* Dissolve by land-use category
* Compute:

  * Area (km²)
  * Percentage of total city area

**Indicators**

* Built-up vs non-built land
* Green space coverage

---

### 3. Infrastructure & Services Density

* Extract POIs by category
* Compute:

  * Count per spatial unit
  * Density per km²
* Spatial units:

  * Neighborhoods (if available)
  * Or a regular grid (square, default 500 m)

Optional:

* Distance to nearest service

---

### 4. Demographic Overlay (Optional)

* Spatially join census tracts
* Compute:

  * Population density
  * Services per 10,000 inhabitants

---

## Outputs

### Maps

* Administrative boundary overview
* Land-use distribution
* Infrastructure density
* Population-weighted accessibility

### Tables

* Land-use breakdown
* POI counts per area
* Ranked underserved zones

### Reproducible Artifacts

* GeoPackage / Parquet layers
* Fully scriptable pipeline

---

## Validation & Limitations

This project explicitly documents:

* OpenStreetMap completeness bias
* Tagging inconsistencies
* Boundary definition assumptions
* CRS distortion effects
* Missing or under-mapped infrastructure

This transparency is intentional and essential for responsible spatial analysis.

---

## Stretch Goals

* Historical comparison using OSM snapshots
* Multi-city comparison
* Interactive dashboard (Folium / Panel)
* Export indicators as open datasets

---

## Evaluation Checklist

* [x] Correct CRS usage
* [x] No area calculations in EPSG:4326
* [x] Geometry validation performed
* [x] Clear methodological assumptions
* [x] Reproducible workflow

---

## How This Project Can Be Used

* Urban analysis & planning
* Civic tech initiatives
* Academic research
* Geospatial portfolio projects


## Data Sources

### Neighborhoods Boundaries
Download the official Córdoba neighborhoods KML from:
- Source: [Municipalidad de Córdoba - Datos Abiertos]
- Save to: `data/raw/neighborhoods.kml`
- Or direct link: [https://gobiernoabierto.cordoba.gob.ar/data/datos-abiertos/categoria/geografia-y-mapas/barrios-de-la-ciudad/118]
---

## Author

**Gaston Strizzolo**
Urban spatial analysis using Python, GeoPandas & OpenStreetMap

---

## License

This project is released under the MIT License.
OpenStreetMap data © OpenStreetMap contributors.