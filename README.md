# A Portfolio-First Public-Data Framework for EU-27 Cross-Border E-Commerce Market-Entry Screening

Supplementary material for a manuscript on first-stage market-entry screening in EU-27 cross-border e-commerce.

## Overview

This repository contains the reproducible analytical material for a 2023 EU-27 country-level study of cross-border e-commerce market-entry screening. The study uses a portfolio-first design rather than a single country ranking. It estimates an execution-feasibility factor from enterprise e-sales penetration, a digital financial participation proxy and the World Bank Logistics Performance Index. Market potential and cross-border buying openness are retained as separate overlays.

## Study design

- Reference year: 2023
- Unit of analysis: EU-27 countries
- Design: public-data, country-level and cross-sectional
- Analytical logic: portfolio-first screening
- Backbone variables: ESP, DFP and LPI
- Latent factor: PC1_EF, estimated by PCA from z-standardized ESP, DFP and LPI
- Overlays: MP and CBO
- Enterprise-side check: ETI, used as a constrained criterion-consistency check on the usable N = 25 sample
- Robustness guardrail: GDP_PPS, used to assess non-redundancy with national prosperity
- Downstream tiering: rank-aware LPI gate family

## Repository structure

```text
data/
  processed/
    CBEC_EU27_v47_backbone_2023.csv
    CBEC_EU27_v47_overlays_2023.csv
    CBEC_EU27_v47_validation_2023.csv
    CBEC_EU27_v47_robustness_2023.csv

  results/
    CBEC_EU27_v47_routeA_analysis_2023.csv
    CBEC_EU27_v47_routeA_results_2023.xlsx

notebooks/
  01_build_public_data_package_v47.ipynb
  02_reproduce_screening_outputs_v47.ipynb

scripts/
  01_build_public_data_package_v47.py
  02_reproduce_screening_outputs_v47.py

figures/

docs/
  DATA_DICTIONARY.md
  ENVIRONMENT.md

README.md
requirements.txt
.gitignore
```

## Notebooks

### `notebooks/01_build_public_data_package_v47.ipynb`

Builds the 2023 EU-27 public-data package used in the study. It assembles the backbone, overlay, enterprise-side consistency and robustness files.

### `notebooks/02_reproduce_screening_outputs_v47.ipynb`

Reproduces the reported screening workflow from the prepared 2023 package. It estimates PC1_EF, assigns rank-aware LPI-gated tiers, performs the ETI criterion-consistency check, computes the GDP_PPS non-redundancy guardrail and evaluates stability across the LPI gate family.

## Open in Colab

[Open Notebook 1 in Colab](https://colab.research.google.com/github/calinadriancomes/EU27-CBEC-Market-Entry-Screening/blob/main/notebooks/01_build_public_data_package_v47.ipynb)

[Open Notebook 2 in Colab](https://colab.research.google.com/github/calinadriancomes/EU27-CBEC-Market-Entry-Screening/blob/main/notebooks/02_reproduce_screening_outputs_v47.ipynb)

## Data sources

The workflow uses public data from Eurostat and the World Bank:

- Eurostat `isoc_ec_esels`, indicator `E_AESELL`: enterprise e-sales penetration
- Eurostat `tin00099`, indicator `I_IUBK`: internet banking, used as a digital financial participation proxy
- World Bank Logistics Performance Index 2023: logistics capability
- Eurostat `isoc_ec_ibos`, indicator `I_BPG_EU`: cross-border buying openness
- Eurostat `demo_pjan`: population base used in the market-potential overlay
- Eurostat `tin00096`, indicator `I_BLT12`: online-shopping incidence used in the market-potential overlay
- Eurostat `isoc_ec_evals`, with `PC_TURN` as primary unit and `PC_ETURN` fallback where required: e-commerce turnover intensity
- Eurostat `tec00114`, indicator `VI_PPS_EU27_2020_HAB`: GDP per capita in purchasing power standards

## Reproducibility

Two routes are available.

### Direct replication route

Use the prepared files in `data/processed/` and run:

```text
notebooks/02_reproduce_screening_outputs_v47.ipynb
```

This route reproduces the reported analysis from the prepared 2023 package.

### Package rebuild route

Run:

```text
notebooks/01_build_public_data_package_v47.ipynb
```

Then run:

```text
notebooks/02_reproduce_screening_outputs_v47.ipynb
```

This route rebuilds the public-data package first and then reproduces the screening analysis. Rebuilding from public sources may depend on live Eurostat access and later changes in public metadata.

## Main outputs

The workflow produces:

- PCA diagnostics for the execution-feasibility backbone
- EU-27 screening portfolio data
- downstream tier assignments
- ETI criterion-consistency diagnostics
- CBO overlay diagnostic
- GDP_PPS non-redundancy diagnostics
- leave-one-out ETI jackknife results
- LPI gate-family stability results
- figures and tables used in the manuscript

## Scope note

The workflow is designed for first-stage market-entry screening under public-data constraints. The 2023 design is cross-sectional. ETI is available for 25 countries in the retained route, while Luxembourg is confidential and Romania is unavailable/low reliability. MP uses a documented total-population fallback. LPI is used both in the execution-feasibility backbone and in the downstream tier gate.

## Citation note

If you use this repository, please cite the associated manuscript once available.

## License

The code is released under the MIT License. The public source data remain subject to the terms of their original providers.
