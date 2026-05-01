# Environment

This document describes the Python environment used to reproduce the EU-27 CBEC market-entry screening workflow.

## Recommended runtime

- Python 3.10 or later
- Google Colab can be used for the notebook workflow
- A local Python environment can also be used

## Installation

Install the required packages with:

```bash
pip install -r requirements.txt
```

## Required packages

The workflow uses:

```text
pandas
numpy
scipy
scikit-learn
matplotlib
openpyxl
eurostat
ipywidgets
adjustText
geopandas
shapely
```

`geopandas` and `shapely` are mainly needed for map-based figure generation. The core PCA, correlation, tiering and table outputs can be reproduced without geospatial plotting if the map step is skipped.

## Local workflow

```bash
git clone https://github.com/calinadriancomes/EU27-CBEC-Market-Entry-Screening.git
cd EU27-CBEC-Market-Entry-Screening
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Then run the notebooks or, if script versions are provided, the corresponding scripts in the `scripts/` folder.

## Colab workflow

Open the notebooks from the repository:

```text
notebooks/01_build_public_data_package_v47.ipynb
notebooks/02_reproduce_screening_outputs_v47.ipynb
```

The notebooks should use repository-relative paths and should not depend on local Windows directories.

## Reproducibility note

The prepared CSV files in `data/processed/` allow direct replication of the retained article-facing results even if public APIs change later. Rebuilding the package from public sources may depend on the availability and current structure of Eurostat endpoints.
