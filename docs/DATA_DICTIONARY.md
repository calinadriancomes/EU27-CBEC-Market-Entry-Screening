# Data Dictionary

This document defines the main variables and output fields used in the EU-27 CBEC market-entry screening workflow.

## Country identifiers

| Field | Meaning |
|---|---|
| `region_code` | EU country code used in the analytical package |
| `country` | Country label or country code, depending on the output file |
| `source_year` | Reference year, fixed at 2023 when reported |
| `package_version` | Harmonized package version, e.g. `v47_final` |

## Backbone variables

These variables enter the execution-feasibility factor.

| Variable | File column | Source | Role | Interpretation |
|---|---|---|---|---|
| ESP | `esp_pct` | Eurostat `isoc_ec_esels`, indicator `E_AESELL` | Backbone input | Enterprise e-sales penetration among enterprises with 10 or more persons employed. Interpreted as a macro-level enterprise digital-sales penetration measure, not as a pure B2C web-retail variable. |
| DFP | `dfp_pct` | Eurostat `tin00099`, indicator `I_IUBK` | Backbone input | Digital financial participation proxy based on internet-banking use among individuals aged 16–74. It is a proxy for the broader digital-financial participation and institutional digital trust environment, not a direct measure of enterprise payment-gateway readiness. |
| LPI | `lpi_score` | World Bank Logistics Performance Index 2023 | Backbone input and downstream gate input | Macro-level logistics capability relevant to fulfillment and execution conditions. It is not a parcel-only delivery metric. |

## Latent execution-feasibility factor

| Variable | File column | Source / construction | Role | Interpretation |
|---|---|---|---|---|
| PC1_EF | `pc1_ef_score` | First principal component from z-standardized ESP, DFP and LPI | Main execution-feasibility axis | Higher values indicate stronger structural execution feasibility. The factor is used as the portfolio x-axis and as the structural signal in the ETI and GDP_PPS diagnostics. |

## Overlay variables

These variables are kept outside the PCA backbone.

| Variable | File column | Source | Role | Interpretation |
|---|---|---|---|---|
| CBO | `cbo_pct` | Eurostat `isoc_ec_ibos`, indicator `I_BPG_EU` | Overlay only | Cross-border buying openness, measured as the share of individuals purchasing online from sellers in other EU countries. |
| MP | `mp_estimated_eshoppers` | Eurostat `demo_pjan` × Eurostat `tin00096`, indicator `I_BLT12` | Overlay only | Market potential, expressed as an estimated absolute online consumer base. In the retained 2023 package, the population denominator uses the documented `TOTAL` fallback. |
| Population base | `mp_population_base` | Eurostat `demo_pjan` | MP component | Population base used to construct MP. |
| Online-shopping incidence | `mp_online_shopping_pct` | Eurostat `tin00096`, indicator `I_BLT12` | MP component | Share of individuals buying or ordering goods or services online. |
| MP population age used | `mp_population_age_used` | Derived audit field | MP construction note | Documents whether the MP denominator used the preferred age-bounded denominator or the `TOTAL` fallback. |

## Enterprise-side criterion-consistency variable

| Variable | File column | Source | Role | Interpretation |
|---|---|---|---|---|
| ETI | `eti_pct` | Eurostat `isoc_ec_evals`, with `PC_TURN` as primary unit and `PC_ETURN` fallback where required | Constrained enterprise-side criterion-consistency check | E-commerce turnover intensity. Usable for 25 countries in the retained 2023 route. Luxembourg is confidential and Romania is unavailable or low reliability. ETI is not a full external-validation variable. |
| ETI dataset code | `eti_dataset_code` | Derived audit field | ETI provenance | Records whether the observation came from the primary or fallback extraction unit. |

## Robustness guardrail

| Variable | File column | Source | Role | Interpretation |
|---|---|---|---|---|
| GDP_PPS | `gdp_pps_index` | Eurostat `tec00114`, indicator `VI_PPS_EU27_2020_HAB` | Non-redundancy guardrail | GDP per capita in purchasing power standards. Used only to assess whether PC1_EF collapses into a prosperity ranking. It does not enter the backbone, overlays or tier construction. |

## Tiering outputs

| Field | Meaning |
|---|---|
| `tier_baseline_rankaware` | Baseline downstream tier assignment under the retained rank-aware LPI gate |
| `Article_Tier` | Reader-facing label for the downstream tier, if included in the generated output |
| `lpi_gate_fraction` | LPI gate fraction tested in the gate-family stability check |
| `changed_countries` | Number of countries whose tier assignment changes compared with the baseline gate |
| `change_share` | Share of EU-27 countries whose tier assignment changes compared with the baseline gate |

## Diagnostics and robustness outputs

| Field | Meaning |
|---|---|
| `explained_variance_ratio_pc1` | Share of backbone variance explained by PC1_EF |
| `condition_number_standardized_backbone` | Condition number of the z-standardized backbone matrix |
| `loading_esp` | PCA loading for ESP |
| `loading_dfp` | PCA loading for DFP |
| `loading_lpi` | PCA loading for LPI |
| `pc1_ef_rank` | Rank of countries by PC1_EF, higher PC1_EF = better rank |
| `gdp_pps_rank` | Rank of countries by GDP_PPS, higher GDP_PPS = better rank |
| `rank_difference` | Difference between PC1_EF rank and GDP_PPS rank |
| `abs_rank_difference` | Absolute rank difference used to identify divergence cases |
| `excluded_region` | Country excluded in a leave-one-out ETI jackknife iteration |
| `rho` | Spearman rank correlation in an analytical check or jackknife iteration |
| `p_value` | p-value associated with the correlation test |
| `pass` | Logical indicator showing whether the retained criterion was met in a jackknife iteration |

## Interpretation note

The tier labels are downstream screening bands. They should not be interpreted as deterministic predictions of market-entry success or as a universal country ranking. The framework is designed for first-stage screening under public-data constraints.
