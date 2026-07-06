# Data dictionary

Key columns used in the generated input and output files.

| Abbreviation / column | Meaning | Role |
|---|---|---|
| `region_code` | EU country code | Identifier |
| `country` | Country name | Identifier |
| `esp_pct` | Enterprise e-sales penetration | Backbone input |
| `dfp_pct` | Digital financial participation proxy | Backbone input |
| `lpi_score` | Logistics Performance Index score | Backbone input and gate input |
| `pc1_ef_score` | PCA-derived execution-condition screening score | Derived score |
| `cbo_pct` | Cross-border buying openness | Overlay |
| `mp_estimated_eshoppers_16_74` | Estimated e-shoppers using population aged 16-74 and online-shopping incidence | Overlay |
| `eti_pct` | E-commerce turnover intensity | Criterion-consistency check |
| `gdp_pps_index` | GDP per capita in purchasing power standards index | Diagnostic |
| `screening_band` | Higher / Middle / Lower screening band | Rule-based summary |

The generated workbook `data/processed/CBEC_EU27_revised_metadata_2023.xlsx` contains additional source and formula notes.
