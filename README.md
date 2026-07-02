# Bangka Island 1930s Historical Topographic Map Dataset (176 Sheets) & Georeferencing Pipeline

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Dataset Size](https://img.shields.io/badge/Dataset-176%20Sheets-brightgreen.svg)
![GIS](https://img.shields.io/badge/GIS-QGIS%20%7C%20GDAL-orange.svg)

## Overview / Proje Hakkında

This repository contains the metadata, calibration pipeline, Python GIS automation
scripts, and technical documentation for georeferencing the **1930s Dutch Colonial
Topographic Map Series of Bangka Island (KK 083-04-01 / 085-04-10)**.

The pipeline transforms 176 unreferenced historical scanned map sheets into a
**georeferenced spatial dataset (WGS 84 / EPSG:4326)** intended as a ground-truth base
layer for **deep-learning / computer-vision** analysis of historical land use and
long-term deforestation.

The authoritative English methodology write-up is [`METHODOLOGY_REVISED_EN.md`](METHODOLOGY_REVISED_EN.md); the full technical report is [`bangka_technical_report.md`](bangka_technical_report.md).

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
├── bangka_technical_report.md     # Full technical report
├── bangka_dataset_v2.csv          # Master metadata & pixel dimensions (176 sheets)
├── bangka_dataset.csv             # Earlier metadata revision
├── .gitignore                     # Excludes heavy raw scans & GeoTIFF outputs
│
├── Core pipeline (produces the published dataset):
│   ├── map_crop.py                # Crop raw scans → recovered_maps/ (Phase 1)
│   ├── recalc_margins.py          # Recompute margins → bangka_dataset_v2.csv (Phase 1)
│   ├── automated_georef.py        # Grid + offset georef → GEOREF_FINAL_STANDARD_164/ (Phase 3)
│   └── crop_margin_geo.py         # Margin correction against the OLD reference
│
├── QC / diagnostics:
│   ├── verify_georef.py           # Quick coordinate sanity check
│   ├── osm_alignment_check.py     # Manual OSM alignment helper (QGIS console)
│   └── calibration_comparison.py  # Derive the systematic offset from a manual reference
│
└── archive/                       # Experimental & superseded scripts (reference only)
    └── README.md                  #   georef_grid.py, corrected_georef.py, diagnose_georef.py, ...
```

## Downloading the Full Map Dataset (GeoTIFFs)

Due to GitHub size limits (100 MB per file; large repos discouraged), the georeferenced
GeoTIFF archives (`GEOREF_FINAL_STANDARD_164/`, `GEOREF_FINAL_COMPOSITE_12/`) and the raw
scans (`main maps/`, `recovered_maps/`) are **not** tracked here and should be
hosted externally (e.g. Hugging Face / Zenodo). See `.gitignore`.

## Using the Data (Quick Start)

The published outputs are plain **GeoTIFF** rasters in **WGS 84 (EPSG:4326)** — no
special tooling is needed, any GIS reads them directly.

1. **Get the rasters.** Download `GEOREF_FINAL_STANDARD_164/` (the 164 single-cell
   sheets) and, if you need the coastline sheets, `GEOREF_FINAL_COMPOSITE_12/` from the
   external host (see below). The scripts in this repo are only needed if you want to
   *reproduce* the georeferencing — not to *use* the maps.
2. **Open them.** In **QGIS**: `Layer → Add Layer → Add Raster Layer…`, select the
   `.tif` files (you can multi-select the whole folder). They land in their real-world
   position automatically. To start, open a few single-cell sheets from
   `GEOREF_FINAL_STANDARD_164/` — they tile seamlessly (σ = 0.0000′).
3. **Add a basemap for context** (optional): `XYZ Tiles → OpenStreetMap`, so the
   historical sheets overlay on modern geography.
4. **Composites:** each of the 12 composite sheets covers a land cell plus an
   (intentionally empty) sea cell; place them the same way — they will not overlap the
   single-cell sheets.
5. **Command-line check** (optional): to confirm a downloaded folder is correctly
   georeferenced, run `python verify_georef.py`, which prints the corner coordinates of
   the first few sheets. Inspect any single file with `gdalinfo <sheet>.tif`.

## Requirements & Installation

Only needed to **reproduce** the pipeline (not to view the data):

```bash
pip install numpy pandas gdal
# Reproduce the pipeline (run from the repository root, in order):
python map_crop.py          # 1. crop raw scans      → recovered_maps/
python recalc_margins.py    # 2. recompute margins   → bangka_dataset_v2.csv
python automated_georef.py  # 3. grid + offset georef → GEOREF_FINAL_STANDARD_164/
python crop_margin_geo.py   # 4. margin correction against the reference
```

## Known Limitations

- The "seamless" claim is quantified for the 164 single-cell sheets (σ = 0.0000′). A
  per-sheet accuracy figure for the 12 composites (e.g. OSM overlay or neatline residual)
  is a recommended next step; automated neatline detection was attempted but the printed
  frame lines on these scans proved too faint for reliable measurement.
