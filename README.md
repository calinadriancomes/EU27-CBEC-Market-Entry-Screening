# EU-27 CBEC Market-Entry Screening: reproducibility repository

This repository supports a manuscript on first-stage screening of EU-27 cross-border e-commerce (CBEC) markets, submitted to the JTAER journal. It stores the notebooks, Python counterparts, input package, generated tables, figures, and source-data files used for the 2023 country-level analysis.

The working route for this project was Google Colab. The notebooks in `notebooks/` are the recommended way to reproduce the workflow. The `.py` files in `scripts/` are plain-Python counterparts of the notebooks and are included for transparency, code review, optional adaptation.

## Run in Google Colab

1. Build the revised data package:

[Open notebook 01 in Colab](https://colab.research.google.com/github/calinadriancomes/EU27-CBEC-Market-Entry-Screening/blob/main/notebooks/01_build_public_data_package_2023.ipynb)

This notebook creates and downloads:

`CBEC_EU27_revised_data_package_2023.zip`

2. Reproduce the tables and figures:

[Open notebook 02 in Colab](https://colab.research.google.com/github/calinadriancomes/EU27-CBEC-Market-Entry-Screening/blob/main/notebooks/02_reproduce_screening_outputs_2023.ipynb)

When prompted, upload `CBEC_EU27_revised_data_package_2023.zip`. The notebook creates and downloads:

`CBEC_EU27_revised_publication_outputs_2023.zip`

The repository also includes the generated 2023 packages and extracted outputs, so the results can be inspected without rerunning the notebooks.

## Repository layout

```text
data/
  packages/        Generated input ZIP from notebook 01
  processed/       Extracted clean input tables
notebooks/         Colab notebooks
scripts/           Plain-Python counterparts of the notebooks
outputs/
  packages/        Generated output ZIP from notebook 02
  tables/          Main and appendix tables, plus analysis workbook
  figures/         Main and appendix figures in PNG/PDF/SVG where available
  source_data/     Source CSV files used for figures
  auxiliary/       Additional generated support files not presented as main tables
docs/              Environment notes, data dictionary, file manifest, reproducibility notes
```

## Main files

- `notebooks/01_build_public_data_package_2023.ipynb` builds the clean input package from public sources and embedded 2023 LPI values.
- `notebooks/02_reproduce_screening_outputs_2023.ipynb` reads the input package and generates the analysis table, diagnostics, figures, and output package.
- `data/packages/CBEC_EU27_revised_data_package_2023.zip` is the generated input archive.
- `outputs/packages/CBEC_EU27_revised_publication_outputs_2023.zip` is the generated archive of tables, figures, and support files.

## Notes on interpretation

The repository is intended for reproducibility. Some generated CSV/XLSX files include helper columns or intermediate diagnostics that are useful for audit and code tracing. The manuscript tables may use a selected subset of these fields.

The study uses public country-level data for 2023. ETI coverage is partial in the retained extraction, with 25 usable countries. Luxembourg and Romania are missing for that check and are disclosed as missing observations in the generated data.

## Requirements

The Colab notebooks install missing Python packages when needed. For users running the plain-Python counterparts locally, the main dependencies are listed in `requirements.txt`.

## Citation note

If you use this repository, please cite the associated manuscript once available.

## License

Code and documentation are released under the MIT License unless otherwise noted. Public statistical data remain subject to the terms of their original providers.
