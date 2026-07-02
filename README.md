# Bangka Island 1930s Historical Topographic Map Dataset (176 Sheets) & Georeferencing Pipeline

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Dataset Size](https://img.shields.io/badge/Dataset-176%20Sheets-brightgreen.svg)
![GIS](https://img.shields.io/badge/GIS-QGIS%20%7C%20GDAL-orange.svg)

> **Note:** This documentation was prepared with AI assistance (Claude). All technical
> claims and measurements have been independently verified against disk files.

## Overview / Proje Hakkında

This repository contains the metadata, calibration pipeline, Python GIS automation
scripts, and technical documentation for georeferencing the **1930s Dutch Colonial
Topographic Map Series of Bangka Island (KK 083-04-01 / 085-04-10)**.

The pipeline transforms 176 unreferenced historical scanned map sheets into a
**georeferenced spatial dataset (WGS 84 / EPSG:4326)** intended as a ground-truth base
layer for **deep-learning / computer-vision** analysis of historical land use and
long-term deforestation.

> **Documentation note:** all metrics below were re-verified directly against the files
> on disk. The authoritative, verified write-up is
> [`METHODOLOGY_REVISED_EN.md`](METHODOLOGY_REVISED_EN.md); the Turkish report is
> [`bangka_georeferans_raporu.md`](bangka_georeferans_raporu.md).

## Dataset Composition

- **164 single-cell sheets** — one 5′ × 5′ graticule cell each.
- **12 composite sheets** — printed across two adjacent cells (9 vertical 5′ × 10′,
  3 horizontal 10′ × 5′) to capture coastlines where a full cell would be mostly sea.

## Key Results (verified)

1. **Exact single-cell tiling.** Back-computing the grid origin from all 164 single-cell
   outputs gives a scatter of **σ = 0.0000′** in both latitude and longitude — the 164
   sheets tile with no residual gap or overlap.
2. **Consistent pixel scale.** Measured mean **0.00001904 °/px** vs. the nominal
   0.00001920 °/px (5′ ÷ 4341 px) — a **−0.85 %** deviation (σ ≈ 0.007 %), i.e. no
   significant shrinkage.
3. **Systematic offset (theoretical grid → real world).** A single, highly consistent
   shift maps the theoretical Dutch graticule onto the OSM-verified real-world position:
   **+0.14083° (+8.450′) East** and **+0.00012° (+0.007′) North**, σ = 0.0000′. A
   sub-arc-minute term (Batavia → WGS 84 datum + paper drift, order tens of metres) sits
   on top of this base.
4. **Composite anchoring rule.** For every one of the 12 composites, the **first letter
   of the sub-code names the land cell**, and the sheet is anchored to that cell
   (12 / 12). Codes are order-sensitive (`ni` = land in lower cell, `in` = land in upper
   cell). There are **zero cell overlaps**; each composite's companion (sea) cell is
   intentionally empty.

## Repository Structure / Klasör Yapısı

```text
bangka-historical-gis-dataset/
├── README.md                      # This file
├── METHODOLOGY_REVISED_EN.md      # Verified English methodology
├── bangka_georeferans_raporu.md   # Turkish technical report
├── bangka_dataset_v2.csv          # Master metadata & pixel dimensions (176 sheets)
├── bangka_dataset.csv             # Earlier metadata revision
├── .gitignore                     # Excludes heavy raw scans & GeoTIFF outputs
└── *.py                           # Pipeline & diagnostic scripts
                                   #   georef_grid.py, duzeltilmis_geo.py,
                                   #   grid_tespit_teshis.py, osm_hizalama_kontrol.py, ...
```

## Downloading the Full Map Dataset (GeoTIFFs)

Due to GitHub size limits (100 MB per file; large repos discouraged), the georeferenced
GeoTIFF archives (`GEOREF_FINAL_STANDART_164/`, `GEOREF_FINAL_BIRLESIK_12/`) and the raw
scans (`main maps/`, `kurtarilmis_haritalar/`) are **not** tracked here and should be
hosted externally (e.g. Hugging Face / Zenodo). See `.gitignore`.

## Requirements & Installation

```bash
pip install numpy pandas gdal
# example: run the grid-based georeferencing pipeline
python georef_grid.py
```

## Known Limitations

- The "seamless" claim is quantified for the 164 single-cell sheets (σ = 0.0000′). A
  per-sheet accuracy figure for the 12 composites (e.g. OSM overlay or neatline residual)
  is a recommended next step; automated neatline detection was attempted but the printed
  frame lines on these scans proved too faint for reliable measurement.
