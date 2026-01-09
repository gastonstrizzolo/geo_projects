Perfect — let’s turn **City Boundary Intelligence Dashboard** into a **clean, professional project spec** you can actually build and later show in a portfolio or CV.

I’ll write this as if it were a **real-world GIS / data science project brief**, not a tutorial.

---

# 📍 Project Specification

## City Boundary Intelligence Dashboard

**Using GeoPandas, OpenStreetMap & Public Data**

---

## 1. Project Motivation

Urban decision-making relies on understanding **how land, population, and infrastructure are distributed within administrative boundaries**. However, raw geospatial data is fragmented, inconsistent, and often misaligned in projections and semantics.

This project builds a **reproducible spatial analysis pipeline** that:

* Retrieves authoritative city boundaries from OpenStreetMap
* Integrates land-use, infrastructure, and demographic data
* Produces quantitative indicators and visualizations at multiple spatial levels

---

## 2. Core Research Questions

1. How is land use distributed within the city boundary?
2. How do infrastructure and services vary across neighborhoods?
3. Which areas show spatial imbalance or potential under-service?
4. How sensitive are results to boundary definitions and CRS choice?

---

## 3. Geographic Scope

**Primary case study**

* City: **Córdoba, Argentina**
* Administrative boundary:

  * OSM relation **5167559**
  * `boundary=administrative`, `admin_level=8`

**Extensible to**

* Other Argentine cities
* Province-level comparison (`admin_level=4`)

---

## 4. Data Sources

### 4.1 OpenStreetMap (via OSMnx / Overpass)

**Layers**

* Administrative boundaries
* Land use polygons
* Buildings
* Points of interest (POIs):

  * Schools
  * Hospitals
  * Parks
  * Pharmacies

**Key tags**

* `boundary=administrative`
* `landuse=*`
* `amenity=*`
* `building=*`

---

### 4.2 Official Public Data (Optional but recommended)

* **INDEC**:

  * Population by census tract
* **IGN Argentina**:

  * CRS definitions
  * Reference layers (validation)

---

## 5. Technical Stack

* Python 3.11+
* GeoPandas
* Shapely
* PyProj
* OSMnx
* Pandas
* Matplotlib / Folium (visualization)

Optional:

* DuckDB / Parquet (performance)
* Jupyter + scripts (hybrid workflow)

---

## 6. Spatial Reference Strategy (Critical)

* Ingestion: WGS84 (`EPSG:4326`)
* Analysis CRS:

  * Argentina-appropriate projected CRS
  * e.g. **POSGAR / Gauss-Krüger** zone covering Córdoba

All area, distance, and density calculations **must be done in projected CRS**.

---

## 7. Project Architecture

```
city-boundary-dashboard/
├── data/
│   ├── raw/
│   ├── processed/
│   └── outputs/
├── notebooks/
│   ├── 01_exploration.ipynb
│   ├── 02_validation.ipynb
│   └── 03_analysis.ipynb
├── src/
│   ├── osm.py
│   ├── boundaries.py
│   ├── landuse.py
│   ├── indicators.py
│   └── visualization.py
├── README.md
└── environment.yml
```

---

## 8. Analysis Pipeline

### 8.1 Boundary Acquisition & Validation

* Fetch city boundary by **OSM relation ID**
* Validate geometry:

  * Self-intersections
  * Holes
* Simplify geometry for visualization only

**Deliverables**

* Clean city polygon
* Metadata report (area, CRS, source)

---

### 8.2 Land Use Analysis

**Steps**

1. Download land-use polygons
2. Clip to city boundary
3. Dissolve by land-use category
4. Compute:

   * Area (km²)
   * Percentage of total city area

**Indicators**

* Built-up vs non-built ratio
* Green space per km²

---

### 8.3 Infrastructure & Services Density

**Compute**

* Count of POIs per category
* Density per km²
* Distance to nearest service (optional)

**Spatial unit**

* Neighborhoods (if available)
* Otherwise:

  * Grid (e.g. hexagonal or square)

---

### 8.4 Demographic Overlay (Advanced)

* Spatial join census tracts to city boundary
* Compute:

  * Population density
  * Infrastructure per 10,000 inhabitants

---

## 9. Outputs

### 9.1 Maps

* City boundary overview
* Land-use choropleth
* Infrastructure density maps
* Population-weighted service access

### 9.2 Tables

* Land-use breakdown
* POI counts per spatial unit
* Ranked underserved areas

### 9.3 Reproducible Artifacts

* GeoPackage / Parquet outputs
* Scripts runnable end-to-end

---

## 10. Validation & Limitations

**Explicitly document**

* OSM completeness bias
* Boundary definition assumptions
* CRS distortion effects
* Missing or inconsistent tags

This section is **mandatory** and adds credibility.

---

## 11. Stretch Goals (Optional)

* Time comparison using historical OSM snapshots
* Compare Córdoba vs another city
* Interactive dashboard (Folium / Panel)
* Export indicators as open data

---

## 12. Evaluation Criteria (Self-check)

✔ Correct CRS usage
✔ No area calculations in lat/lon
✔ Clean geometry handling
✔ Transparent assumptions
✔ Reproducible pipeline

---

## 13. How This Looks on a CV

> **Urban Spatial Analysis Project – City Boundary Intelligence Dashboard**
> Designed and implemented a reproducible geospatial analysis pipeline using GeoPandas and OpenStreetMap to quantify land use, infrastructure density, and service accessibility within administrative city boundaries.

---

## 🚀 Next Step (recommended)

I can:

* Write the **exact Python skeleton** for `/src`
* Define **OSM queries** per layer
* Help choose **best CRS for Córdoba**
* Turn this into a **GitHub-ready README**

Tell me what you want to build next and we go hands-on.
