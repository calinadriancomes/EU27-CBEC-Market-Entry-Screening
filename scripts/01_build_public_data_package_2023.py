# -*- coding: utf-8 -*-
"""saved from .ipynb file
"""

# @title
# -*- coding: utf-8 -*-
"""
EU-27 CBEC Manuscript: Data Extraction and Package Builder

This script fetches and processes the raw data from Eurostat and the World Bank.
It automatically constructs the clean dataset required for the manuscript's
screening model, and ensures the Market Potential uses the age-consistent 16-74 population.

All final datasets are saved and bundled into a single archive:
- CBEC_EU27_revised_data_package_2023.zip
"""

from __future__ import annotations

import os
import sys
import subprocess
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def install_deps() -> None:
    """Install lightweight data-package dependencies when missing, Colab-friendly."""
    pkgs = ["pandas", "numpy", "eurostat", "openpyxl"]
    for pkg in pkgs:
        try:
            __import__(pkg)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


install_deps()

import numpy as np
import pandas as pd
import eurostat


# ==============================================================================
# 1. CONSTANTS
# ==============================================================================
TARGET_YEAR = 2023
PACKAGE_PREFIX = "CBEC_EU27_revised"
PACKAGE_VERSION = "revised_candidate_2023_mp16_74"
FALLBACK_POP16_FILE = "CBEC_EU27_population_16_74_2023.csv"

EU27: List[str] = [
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES",
    "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",
]

EU27_NAMES: Dict[str, str] = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus",
    "CZ": "Czechia", "DE": "Germany", "DK": "Denmark", "EE": "Estonia",
    "EL": "Greece", "ES": "Spain", "FI": "Finland", "FR": "France",
    "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta",
    "NL": "Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia",
}

# Official 2023 World Bank LPI values as transcribed into the project package.
OFFICIAL_LPI_2023: Dict[str, float] = {
    "AT": 4.0, "BE": 4.0, "BG": 3.2, "CY": 3.2, "CZ": 3.3, "DE": 4.1, "DK": 4.1,
    "EE": 3.4, "EL": 3.4, "ES": 3.9, "FI": 4.0, "FR": 3.9, "HR": 3.3, "HU": 3.3,
    "IE": 3.3, "IT": 3.7, "LT": 3.4, "LU": 3.4, "LV": 3.4, "MT": 3.2, "NL": 4.0,
    "PL": 3.4, "PT": 3.3, "RO": 3.2, "SE": 4.0, "SI": 3.3, "SK": 3.3,
}

AGE_16_74: List[str] = [f"Y{i}" for i in range(16, 75)]
AUDIT_LOG: List[Dict[str, object]] = []


# ==============================================================================
# 2. UTILITY FUNCTIONS
# ==============================================================================
def status_from_count(count: int, total: int = 27) -> str:
    if count == total:
        return "COMPLETE"
    if count == 0:
        return "FAILED"
    return "PARTIAL"


def log_audit(
    variable: str,
    dataset: str,
    code: str,
    year: int,
    filters: object,
    usable_count: int,
    missing: List[str],
    status: str,
    notes: str,
) -> None:
    AUDIT_LOG.append({
        "variable": variable,
        "dataset": dataset,
        "code": code,
        "year_requested": year,
        "year_obtained": year,
        "filters": str(filters),
        "usable_count": int(usable_count),
        "usable_share": round(float(usable_count) / len(EU27), 4),
        "missing_countries": ", ".join(missing) if missing else "None",
        "status": status,
        "notes": notes,
    })


def find_geo_col(df: pd.DataFrame) -> str:
    candidates = ["geo\\TIME_PERIOD", "geo", "geo_time"]
    for col in candidates:
        if col in df.columns:
            return col
    geo_like = [c for c in df.columns if "geo" in str(c).lower()]
    if not geo_like:
        raise KeyError("No geo-like column found in Eurostat dataframe.")
    return geo_like[0]


def find_year_col(df: pd.DataFrame, year: int) -> object:
    if str(year) in df.columns:
        return str(year)
    if year in df.columns:
        return year
    raise KeyError(f"Year {year} not found in dataframe columns.")


def filter_exact_eu27(df: pd.DataFrame, country_col: Optional[str] = None) -> pd.DataFrame:
    if country_col is None:
        country_col = find_geo_col(df)
    dff = df[df[country_col].isin(EU27)].copy()
    if country_col != "region_code":
        dff = dff.rename(columns={country_col: "region_code"})
    return dff.sort_values("region_code").reset_index(drop=True)


def ensure_eu27_base(df: Optional[pd.DataFrame], value_cols: List[str]) -> pd.DataFrame:
    base = pd.DataFrame({"region_code": EU27})
    if df is None or df.empty:
        for col in value_cols:
            base[col] = np.nan
        return base
    out = base.merge(df, on="region_code", how="left")
    return out


def assert_exact_eu27(df: pd.DataFrame, name: str) -> None:
    if "region_code" not in df.columns:
        raise ValueError(f"{name}: missing required column region_code.")
    codes = df["region_code"].tolist()
    if len(codes) != len(EU27):
        raise ValueError(f"{name}: expected 27 rows, found {len(codes)}.")
    if sorted(codes) != sorted(EU27):
        missing = sorted(set(EU27) - set(codes))
        extra = sorted(set(codes) - set(EU27))
        raise ValueError(f"{name}: EU-27 mismatch. Missing={missing}; Extra={extra}.")
    if df["region_code"].duplicated().any():
        dupes = df.loc[df["region_code"].duplicated(), "region_code"].tolist()
        raise ValueError(f"{name}: duplicate region_code rows found: {dupes}.")


def require_complete(df: pd.DataFrame, cols: List[str], name: str) -> None:
    assert_exact_eu27(df, name)
    for col in cols:
        if col not in df.columns:
            raise ValueError(f"{name}: missing required column {col}.")
        missing = df.loc[df[col].isna(), "region_code"].tolist()
        if missing:
            raise ValueError(f"{name}: column {col} incomplete for countries: {missing}.")


def read_csv_strict(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8-sig")


# ==============================================================================
# 3. EUROSTAT EXTRACTION FUNCTIONS
# ==============================================================================
def extract_single_series(
    ds: str,
    filters: Dict[str, str],
    year: int,
    out_col: str,
    variable: str,
    code: str,
    notes: str,
) -> pd.DataFrame:
    try:
        df = eurostat.get_data_df(ds)
        if df is None or df.empty:
            raise ValueError(f"Dataset {ds} is empty or unreachable.")
        for key, value in filters.items():
            if key not in df.columns:
                raise KeyError(f"Column {key} not found in {ds}.")
            df = df[df[key] == value]
        dff = filter_exact_eu27(df)
        year_col = find_year_col(dff, year)
        out = dff[["region_code", year_col]].rename(columns={year_col: out_col})
        out[out_col] = pd.to_numeric(out[out_col], errors="coerce")
        out = ensure_eu27_base(out, [out_col])
        missing = out.loc[out[out_col].isna(), "region_code"].tolist()
        usable = len(EU27) - len(missing)
        log_audit(variable, ds, code, year, filters, usable, missing, status_from_count(usable), notes)
        return out
    except Exception as exc:
        log_audit(variable, ds, code, year, filters, 0, EU27.copy(), "FAILED", str(exc))
        return ensure_eu27_base(None, [out_col])


def fetch_esp(year: int) -> pd.DataFrame:
    return extract_single_series(
        ds="isoc_ec_esels",
        filters={
            "freq": "A",
            "size_emp": "GE10",
            "nace_r2": "C10-S951_X_K",
            "indic_is": "E_AESELL",
            "unit": "PC_ENT",
        },
        year=year,
        out_col="esp_pct",
        variable="ESP",
        code="E_AESELL",
        notes="Enterprise e-sales penetration; country-level enterprise digital-sales proxy.",
    )


def fetch_dfp(year: int) -> pd.DataFrame:
    return extract_single_series(
        ds="tin00099",
        filters={"freq": "A", "indic_is": "I_IUBK", "unit": "PC_IND", "ind_type": "IND_TOTAL"},
        year=year,
        out_col="dfp_pct",
        variable="DFP",
        code="I_IUBK",
        notes="Digital financial participation proxy; not direct enterprise payment-gateway readiness.",
    )


def fetch_lpi(year: int) -> pd.DataFrame:
    df = pd.DataFrame({"region_code": list(OFFICIAL_LPI_2023.keys()), "lpi_score": list(OFFICIAL_LPI_2023.values())})
    df = ensure_eu27_base(df, ["lpi_score"])
    missing = df.loc[df["lpi_score"].isna(), "region_code"].tolist()
    usable = len(EU27) - len(missing)
    log_audit(
        "LPI",
        "World_Bank_LPI_2023",
        "LPI.OVRL.XQ",
        year,
        {},
        usable,
        missing,
        status_from_count(usable),
        "Official 2023 LPI values embedded for stable reproducibility.",
    )
    return df


def fetch_cbo(year: int) -> pd.DataFrame:
    return extract_single_series(
        ds="isoc_ec_ibos",
        filters={"freq": "A", "ind_type": "IND_TOTAL", "indic_is": "I_BPG_EU", "unit": "PC_IND_BUY3"},
        year=year,
        out_col="cbo_pct",
        variable="CBO",
        code="I_BPG_EU",
        notes="Cross-border buying openness overlay.",
    )


def fetch_online_shopping_incidence(year: int) -> pd.DataFrame:
    return extract_single_series(
        ds="tin00096",
        filters={"freq": "A", "indic_is": "I_BLT12", "unit": "PC_IND", "ind_type": "IND_TOTAL"},
        year=year,
        out_col="mp_online_shopping_pct",
        variable="MP_INC",
        code="I_BLT12",
        notes="Online-shopping incidence used for MP overlay.",
    )


def construct_population_16_74_from_demo_pjan(demo_df: pd.DataFrame, year: int) -> pd.DataFrame:
    required_filter_cols = ["freq", "sex", "unit", "age"]
    for col in required_filter_cols:
        if col not in demo_df.columns:
            raise KeyError(f"Column {col} not found in demo_pjan dataframe.")
    year_col = find_year_col(demo_df, year)

    dff = demo_df.copy()
    dff = dff[(dff["freq"] == "A") & (dff["sex"] == "T") & (dff["unit"] == "NR") & (dff["age"].isin(AGE_16_74))]
    dff = filter_exact_eu27(dff)
    if dff.empty:
        raise ValueError("No EU-27 rows found for demo_pjan ages Y16-Y74, sex=T, unit=NR.")

    dff["value"] = pd.to_numeric(dff[year_col], errors="coerce")
    nonmissing = dff.dropna(subset=["value"])
    age_counts = nonmissing.groupby("region_code")["age"].nunique()
    incomplete = [iso for iso in EU27 if int(age_counts.get(iso, 0)) != len(AGE_16_74)]
    if incomplete:
        raise ValueError(
            "Incomplete single-year age coverage for MP population Y16-Y74: "
            + ", ".join(incomplete)
        )

    pop = nonmissing.groupby("region_code", as_index=False)["value"].sum()
    pop = pop.rename(columns={"value": "mp_population_16_74"})
    pop["mp_population_16_74"] = pd.to_numeric(pop["mp_population_16_74"], errors="coerce")
    pop = ensure_eu27_base(pop, ["mp_population_16_74"])
    return pop


def construct_total_population_from_demo_pjan(demo_df: pd.DataFrame, year: int) -> pd.DataFrame:
    try:
        year_col = find_year_col(demo_df, year)
        for col in ["freq", "sex", "unit", "age"]:
            if col not in demo_df.columns:
                raise KeyError(f"Column {col} not found in demo_pjan dataframe.")
        dff = demo_df.copy()
        dff = dff[(dff["freq"] == "A") & (dff["sex"] == "T") & (dff["unit"] == "NR") & (dff["age"] == "TOTAL")]
        dff = filter_exact_eu27(dff)
        out = dff[["region_code", year_col]].rename(columns={year_col: "mp_population_total"})
        out["mp_population_total"] = pd.to_numeric(out["mp_population_total"], errors="coerce")
        out = ensure_eu27_base(out, ["mp_population_total"])
        missing = out.loc[out["mp_population_total"].isna(), "region_code"].tolist()
        usable = len(EU27) - len(missing)
        log_audit(
            "MP_POP_TOTAL_OPTIONAL",
            "demo_pjan",
            "TOTAL",
            year,
            {"freq": "A", "sex": "T", "unit": "NR", "age": "TOTAL"},
            usable,
            missing,
            status_from_count(usable),
            "Total-population denominator retained only for optional MP rank-stability comparison.",
        )
        return out
    except Exception as exc:
        log_audit(
            "MP_POP_TOTAL_OPTIONAL",
            "demo_pjan",
            "TOTAL",
            year,
            {"freq": "A", "sex": "T", "unit": "NR", "age": "TOTAL"},
            0,
            EU27.copy(),
            "FAILED",
            f"Optional total-population MP comparison unavailable: {exc}",
        )
        return ensure_eu27_base(None, ["mp_population_total"])


def load_population_16_74_fallback() -> pd.DataFrame:
    """Load optional local fallback CSV, prompting upload when running in Colab."""
    path = Path(FALLBACK_POP16_FILE)
    if not path.exists():
        try:
            from google.colab import files  # type: ignore
            print(
                "Eurostat MP population 16-74 could not be constructed. "
                f"Please upload {FALLBACK_POP16_FILE} with columns region_code, mp_population_16_74."
            )
            uploaded = files.upload()
            if FALLBACK_POP16_FILE not in uploaded and not Path(FALLBACK_POP16_FILE).exists():
                raise FileNotFoundError(
                    f"Uploaded files did not include required fallback file: {FALLBACK_POP16_FILE}"
                )
        except ImportError as exc:
            raise FileNotFoundError(
                f"Fallback file {FALLBACK_POP16_FILE} not found and this is not a Colab upload environment."
            ) from exc

    fallback = read_csv_strict(path)
    required = {"region_code", "mp_population_16_74"}
    missing_cols = required - set(fallback.columns)
    if missing_cols:
        raise ValueError(f"Fallback population file missing required columns: {sorted(missing_cols)}")

    fallback = fallback[["region_code", "mp_population_16_74"]].copy()
    fallback["region_code"] = fallback["region_code"].astype(str).str.strip()
    fallback["mp_population_16_74"] = pd.to_numeric(fallback["mp_population_16_74"], errors="coerce")
    fallback = ensure_eu27_base(fallback, ["mp_population_16_74"])
    require_complete(fallback, ["mp_population_16_74"], "fallback MP population 16-74")
    return fallback


def fetch_mp_population_16_74_and_total(year: int) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """Return age-consistent MP population and optional total population support."""
    try:
        demo_df = eurostat.get_data_df("demo_pjan")
        if demo_df is None or demo_df.empty:
            raise ValueError("Dataset demo_pjan is empty or unreachable.")
        pop16 = construct_population_16_74_from_demo_pjan(demo_df, year)
        missing = pop16.loc[pop16["mp_population_16_74"].isna(), "region_code"].tolist()
        usable = len(EU27) - len(missing)
        log_audit(
            "MP_POP_16_74",
            "demo_pjan",
            "Y16-Y74_SUM",
            year,
            {"freq": "A", "sex": "T", "unit": "NR", "age": "Y16...Y74 summed"},
            usable,
            missing,
            status_from_count(usable),
            "Population denominator constructed by summing Eurostat demo_pjan single-year ages Y16 through Y74.",
        )
        total = construct_total_population_from_demo_pjan(demo_df, year)
        return pop16, total, "Eurostat demo_pjan Y16-Y74 single-year sum"
    except Exception as exc:
        log_audit(
            "MP_POP_16_74",
            "demo_pjan",
            "Y16-Y74_SUM",
            year,
            {"freq": "A", "sex": "T", "unit": "NR", "age": "Y16...Y74 summed"},
            0,
            EU27.copy(),
            "FAILED",
            f"Eurostat construction failed; attempting local fallback. Error: {exc}",
        )
        pop16 = load_population_16_74_fallback()
        log_audit(
            "MP_POP_16_74",
            "local_fallback_csv",
            FALLBACK_POP16_FILE,
            year,
            {"required_columns": "region_code, mp_population_16_74"},
            len(EU27),
            [],
            "COMPLETE",
            "Population denominator loaded from local fallback file after Eurostat access/construction failure.",
        )
        total = ensure_eu27_base(None, ["mp_population_total"])
        return pop16, total, f"local fallback file {FALLBACK_POP16_FILE}"


def fetch_mp(year: int) -> pd.DataFrame:
    pop16, pop_total, pop_source = fetch_mp_population_16_74_and_total(year)
    inc = fetch_online_shopping_incidence(year)

    require_complete(pop16, ["mp_population_16_74"], "MP population 16-74")
    require_complete(inc, ["mp_online_shopping_pct"], "MP online-shopping incidence")

    mp = ensure_eu27_base(None, [])
    mp = mp.merge(pop16, on="region_code", how="left")
    mp = mp.merge(inc, on="region_code", how="left")
    mp = mp.merge(pop_total, on="region_code", how="left")

    mp["mp_estimated_eshoppers_16_74"] = (
        mp["mp_population_16_74"] * mp["mp_online_shopping_pct"] / 100.0
    )

    if "mp_population_total" in mp.columns and mp["mp_population_total"].notna().all():
        mp["mp_estimated_eshoppers_total_optional"] = (
            mp["mp_population_total"] * mp["mp_online_shopping_pct"] / 100.0
        )
        mp["mp_rank_total_optional"] = mp["mp_estimated_eshoppers_total_optional"].rank(
            ascending=False, method="min"
        ).astype("Int64")
    else:
        mp["mp_estimated_eshoppers_total_optional"] = np.nan
        mp["mp_rank_total_optional"] = pd.Series([pd.NA] * len(mp), dtype="Int64")

    mp["mp_rank_16_74"] = mp["mp_estimated_eshoppers_16_74"].rank(ascending=False, method="min").astype("Int64")
    if mp["mp_rank_total_optional"].notna().all():
        mp["mp_rank_shift_16_74_vs_total_optional"] = (
            mp["mp_rank_16_74"].astype(int) - mp["mp_rank_total_optional"].astype(int)
        )
    else:
        mp["mp_rank_shift_16_74_vs_total_optional"] = pd.Series([pd.NA] * len(mp), dtype="Int64")

    mp["mp_formula_label"] = "population_Y16_Y74_SUM * online_shopping_incidence / 100"
    mp["mp_population_age_used"] = "Y16_Y74_SUM"

    # Critical formula and completeness checks.
    require_complete(
        mp,
        ["mp_population_16_74", "mp_online_shopping_pct", "mp_estimated_eshoppers_16_74"],
        "MP 16-74 construction",
    )
    recomputed = mp["mp_population_16_74"] * mp["mp_online_shopping_pct"] / 100.0
    if not np.allclose(mp["mp_estimated_eshoppers_16_74"], recomputed, rtol=0, atol=1e-6):
        raise ValueError("MP formula verification failed for mp_estimated_eshoppers_16_74.")
    if set(mp["mp_population_age_used"].unique()) != {"Y16_Y74_SUM"}:
        raise ValueError("MP age-used marker must be exactly Y16_Y74_SUM for all countries.")

    missing = mp.loc[mp["mp_estimated_eshoppers_16_74"].isna(), "region_code"].tolist()
    usable = len(EU27) - len(missing)
    log_audit(
        "MP",
        "demo_pjan + tin00096",
        "Y16-Y74_SUM + I_BLT12",
        year,
        {"population_source": pop_source, "incidence_code": "I_BLT12"},
        usable,
        missing,
        status_from_count(usable),
        "Main manuscript MP uses age-consistent population 16-74. Total-population MP retained only as optional rank-stability support.",
    )

    ordered_cols = [
        "region_code",
        "mp_population_16_74",
        "mp_online_shopping_pct",
        "mp_estimated_eshoppers_16_74",
        "mp_population_total",
        "mp_estimated_eshoppers_total_optional",
        "mp_rank_16_74",
        "mp_rank_total_optional",
        "mp_rank_shift_16_74_vs_total_optional",
        "mp_formula_label",
        "mp_population_age_used",
    ]
    return mp[ordered_cols]


def fetch_eti(year: int) -> pd.DataFrame:
    ds = "isoc_ec_evals"
    ind = "E_AWSVAL"
    base_filters = {"freq": "A", "size_emp": "GE10", "nace_r2": "C10-S951_X_K", "indic_is": ind}
    base = ensure_eu27_base(None, ["eti_pct"])
    base["eti_dataset_code"] = "FAILED"
    base["eti_status_or_note"] = "Unavailable"

    try:
        df = eurostat.get_data_df(ds)
        if df is None or df.empty:
            raise ValueError(f"Dataset {ds} is empty or unreachable.")

        def extract_unit(unit_name: str) -> Optional[pd.DataFrame]:
            filters = base_filters.copy()
            filters["unit"] = unit_name
            dff = df.copy()
            for key, value in filters.items():
                if key not in dff.columns:
                    return None
                dff = dff[dff[key] == value]
            if dff.empty:
                return None
            dff = filter_exact_eu27(dff)
            year_col = find_year_col(dff, year)
            out = dff[["region_code", year_col]].rename(columns={year_col: "eti_pct"})
            out["eti_pct"] = pd.to_numeric(out["eti_pct"], errors="coerce")
            out = ensure_eu27_base(out, ["eti_pct"])
            out["eti_dataset_code"] = f"{ds} ({unit_name})"
            return out

        primary = extract_unit("PC_TURN")
        result = primary.copy() if primary is not None else base[["region_code", "eti_pct", "eti_dataset_code"]].copy()

        fallback = extract_unit("PC_ETURN")
        if fallback is not None:
            mask = result["eti_pct"].isna()
            fill_map = fallback.set_index("region_code")["eti_pct"]
            result.loc[mask, "eti_pct"] = result.loc[mask, "region_code"].map(fill_map)
            result.loc[mask, "eti_dataset_code"] = f"{ds} (PC_ETURN fallback)"

        result["eti_status_or_note"] = np.where(
            result["eti_pct"].notna(),
            "usable for criterion-consistency check",
            "missing/confidential/unavailable in retained route",
        )
        missing = result.loc[result["eti_pct"].isna(), "region_code"].tolist()
        usable = len(EU27) - len(missing)
        log_audit(
            "ETI",
            ds,
            ind,
            year,
            {"base": base_filters, "primary_unit": "PC_TURN", "fallback_unit": "PC_ETURN"},
            usable,
            missing,
            status_from_count(usable),
            "Enterprise-side criterion-consistency route; partial coverage is acceptable and must be disclosed.",
        )
        return result
    except Exception as exc:
        log_audit("ETI", ds, ind, year, base_filters, 0, EU27.copy(), "FAILED", str(exc))
        return base


def fetch_gdp_pps(year: int) -> pd.DataFrame:
    return extract_single_series(
        ds="tec00114",
        filters={"freq": "A", "indic_ppp": "VI_PPS_EU27_2020_HAB", "ppp_cat18": "GDP"},
        year=year,
        out_col="gdp_pps_index",
        variable="GDP_PPS",
        code="VI_PPS_EU27_2020_HAB",
        notes="Prosperity association / rank-difference diagnostic; not proof of conceptual independence.",
    )


# ==============================================================================
# 4. BUILD, VALIDATE, EXPORT
# ==============================================================================
def run_builder(year: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    global AUDIT_LOG
    AUDIT_LOG = []

    base_df = pd.DataFrame({
        "region_code": EU27,
        "country": [EU27_NAMES[c] for c in EU27],
        "source_year": year,
        "package_version": PACKAGE_VERSION,
    })

    print("Fetching ESP...")
    esp = fetch_esp(year)
    print("Fetching DFP...")
    dfp = fetch_dfp(year)
    print("Preparing LPI...")
    lpi = fetch_lpi(year)
    print("Fetching CBO...")
    cbo = fetch_cbo(year)
    print("Constructing MP with age-consistent 16-74 denominator...")
    mp = fetch_mp(year)
    print("Fetching ETI...")
    eti = fetch_eti(year)
    print("Fetching GDP_PPS...")
    gdp = fetch_gdp_pps(year)

    df_backbone = base_df.merge(esp, on="region_code").merge(dfp, on="region_code").merge(lpi, on="region_code")
    df_overlays = base_df.merge(cbo, on="region_code").merge(mp, on="region_code")
    df_validation = base_df.merge(eti, on="region_code")
    df_robustness = base_df.merge(gdp, on="region_code")
    df_audit = pd.DataFrame(AUDIT_LOG)

    validate_revised_data_package(df_backbone, df_overlays, df_validation, df_robustness)
    return df_backbone, df_overlays, df_validation, df_robustness, df_audit


def validate_revised_data_package(
    df_backbone: pd.DataFrame,
    df_overlays: pd.DataFrame,
    df_validation: pd.DataFrame,
    df_robustness: pd.DataFrame,
) -> None:
    require_complete(df_backbone, ["esp_pct", "dfp_pct", "lpi_score"], "backbone")
    require_complete(
        df_overlays,
        ["cbo_pct", "mp_population_16_74", "mp_online_shopping_pct", "mp_estimated_eshoppers_16_74"],
        "overlays",
    )
    assert_exact_eu27(df_validation, "validation")
    require_complete(df_robustness, ["gdp_pps_index"], "robustness")

    if not (df_overlays["mp_population_age_used"] == "Y16_Y74_SUM").all():
        raise ValueError("overlays: MP population age marker must be Y16_Y74_SUM for every country.")
    expected_mp = df_overlays["mp_population_16_74"] * df_overlays["mp_online_shopping_pct"] / 100.0
    if not np.allclose(df_overlays["mp_estimated_eshoppers_16_74"], expected_mp, rtol=0, atol=1e-6):
        raise ValueError("overlays: MP 16-74 formula check failed.")

    if "mp_estimated_eshoppers" in df_overlays.columns:
        raise ValueError(
            "overlays: ambiguous legacy column mp_estimated_eshoppers should not be present. "
            "Use mp_estimated_eshoppers_16_74 as the main MP field."
        )


def export_outputs(
    df_backbone: pd.DataFrame,
    df_overlays: pd.DataFrame,
    df_validation: pd.DataFrame,
    df_robustness: pd.DataFrame,
    df_audit: pd.DataFrame,
    year: int,
) -> List[str]:
    files = [
        f"{PACKAGE_PREFIX}_backbone_{year}.csv",
        f"{PACKAGE_PREFIX}_overlays_{year}.csv",
        f"{PACKAGE_PREFIX}_validation_{year}.csv",
        f"{PACKAGE_PREFIX}_robustness_{year}.csv",
        f"{PACKAGE_PREFIX}_extraction_audit_{year}.csv",
        f"{PACKAGE_PREFIX}_master_{year}.xlsx",
        f"{PACKAGE_PREFIX}_metadata_{year}.xlsx",
    ]

    df_backbone.to_csv(files[0], index=False, encoding="utf-8-sig")
    df_overlays.to_csv(files[1], index=False, encoding="utf-8-sig")
    df_validation.to_csv(files[2], index=False, encoding="utf-8-sig")
    df_robustness.to_csv(files[3], index=False, encoding="utf-8-sig")
    df_audit.to_csv(files[4], index=False, encoding="utf-8-sig")

    merged = (
        df_backbone
        .merge(df_overlays.drop(columns=["country", "source_year", "package_version"]), on="region_code")
        .merge(df_validation.drop(columns=["country", "source_year", "package_version"]), on="region_code")
        .merge(df_robustness.drop(columns=["country", "source_year", "package_version"]), on="region_code")
    )

    with pd.ExcelWriter(files[5], engine="openpyxl") as writer:
        df_backbone.to_excel(writer, sheet_name="backbone", index=False)
        df_overlays.to_excel(writer, sheet_name="overlays", index=False)
        df_validation.to_excel(writer, sheet_name="validation", index=False)
        df_robustness.to_excel(writer, sheet_name="robustness", index=False)
        merged.to_excel(writer, sheet_name="merged_all", index=False)
        df_audit.to_excel(writer, sheet_name="audit", index=False)

    variable_dictionary = pd.DataFrame([
        {"abbr": "ESP", "column": "esp_pct", "role": "Backbone", "definition": "Enterprise e-sales penetration; enterprise digital-sales proxy."},
        {"abbr": "DFP", "column": "dfp_pct", "role": "Backbone", "definition": "Digital financial participation proxy; not direct enterprise payment-gateway readiness."},
        {"abbr": "LPI", "column": "lpi_score", "role": "Backbone", "definition": "World Bank Logistics Performance Index, 2023 overall score."},
        {"abbr": "CBO", "column": "cbo_pct", "role": "Overlay", "definition": "Cross-border buying openness."},
        {"abbr": "MP", "column": "mp_estimated_eshoppers_16_74", "role": "Overlay", "definition": "Market potential using age-consistent population 16-74 denominator."},
        {"abbr": "ETI", "column": "eti_pct", "role": "Criterion-consistency", "definition": "Enterprise-side e-commerce turnover intensity; criterion-consistency only, not external validation."},
        {"abbr": "GDP_PPS", "column": "gdp_pps_index", "role": "Diagnostic", "definition": "GDP per capita in purchasing power standards; prosperity association/rank-difference diagnostic."},
        {"abbr": "PC1_EF", "column": "derived_in_script_02", "role": "Derived screening axis", "definition": "PCA-derived execution-condition screening axis, derived downstream in Script 02."},
    ])

    source_dictionary = pd.DataFrame([
        {"variable": "ESP", "dataset": "Eurostat isoc_ec_esels", "code": "E_AESELL", "filters": "freq=A; size_emp=GE10; nace_r2=C10-S951_X_K; unit=PC_ENT"},
        {"variable": "DFP", "dataset": "Eurostat tin00099", "code": "I_IUBK", "filters": "freq=A; ind_type=IND_TOTAL; unit=PC_IND"},
        {"variable": "LPI", "dataset": "World Bank LPI 2023", "code": "LPI.OVRL.XQ", "filters": "embedded official 2023 EU-27 values for reproducibility"},
        {"variable": "CBO", "dataset": "Eurostat isoc_ec_ibos", "code": "I_BPG_EU", "filters": "freq=A; ind_type=IND_TOTAL; unit=PC_IND_BUY3"},
        {"variable": "MP population", "dataset": "Eurostat demo_pjan", "code": "Y16-Y74_SUM", "filters": "freq=A; sex=T; unit=NR; age=Y16 through Y74 summed"},
        {"variable": "MP incidence", "dataset": "Eurostat tin00096", "code": "I_BLT12", "filters": "freq=A; ind_type=IND_TOTAL; unit=PC_IND"},
        {"variable": "ETI", "dataset": "Eurostat isoc_ec_evals", "code": "E_AWSVAL", "filters": "freq=A; size_emp=GE10; nace_r2=C10-S951_X_K; unit=PC_TURN primary, PC_ETURN fallback"},
        {"variable": "GDP_PPS", "dataset": "Eurostat tec00114", "code": "VI_PPS_EU27_2020_HAB", "filters": "freq=A; ppp_cat18=GDP"},
    ])

    role_definition = pd.DataFrame([
        {"block": "Backbone", "definition": "Primary inputs for the downstream PCA-derived execution-condition screening axis."},
        {"block": "Overlays", "definition": "Market scale and cross-border openness kept outside the PCA backbone."},
        {"block": "Criterion-consistency", "definition": "Partial enterprise-side check; does not imply external validation."},
        {"block": "Diagnostic", "definition": "Prosperity association/rank-difference context only."},
    ])

    formula_notes = pd.DataFrame([
        {"item": "MP main", "definition": "mp_estimated_eshoppers_16_74 = mp_population_16_74 * mp_online_shopping_pct / 100"},
        {"item": "MP population denominator", "definition": "mp_population_16_74 = sum of Eurostat demo_pjan ages Y16 through Y74, sex=T, unit=NR, time=2023"},
        {"item": "MP optional total comparison", "definition": "Total-population MP retained only as optional rank-stability support, not as manuscript MP."},
        {"item": "LPI", "definition": "Embedded official 2023 values used for stable reproducibility."},
    ])

    audit_summary = df_audit[["variable", "dataset", "code", "filters", "usable_count", "usable_share", "status", "notes"]].copy()

    version_log = pd.DataFrame([
        {
            "package_version": PACKAGE_VERSION,
            "package_prefix": PACKAGE_PREFIX,
            "year": year,
            "architecture": "Revised candidate public-data package; v47 logic retained where appropriate; MP revised to age-consistent 16-74 denominator.",
            "note": "No internal revision-control artifacts generated.",
        }
    ])

    with pd.ExcelWriter(files[6], engine="openpyxl") as writer:
        variable_dictionary.to_excel(writer, sheet_name="variable_dictionary", index=False)
        source_dictionary.to_excel(writer, sheet_name="source_dictionary", index=False)
        formula_notes.to_excel(writer, sheet_name="formula_notes", index=False)
        role_definition.to_excel(writer, sheet_name="role_definition", index=False)
        audit_summary.to_excel(writer, sheet_name="audit_summary", index=False)
        version_log.to_excel(writer, sheet_name="version_log", index=False)

    return files


def render_console_summary(
    df_backbone: pd.DataFrame,
    df_overlays: pd.DataFrame,
    df_validation: pd.DataFrame,
    df_robustness: pd.DataFrame,
    files: List[str],
) -> None:
    eti_count = int(df_validation["eti_pct"].notna().sum())
    print("\n=== Revised data package build complete ===")
    print(f"Backbone coverage: {len(df_backbone)}/27 complete for ESP, DFP, LPI")
    print(f"Overlay coverage: {len(df_overlays)}/27 complete for CBO and MP 16-74")
    print(f"ETI usable observations: {eti_count}/27 (partial coverage is allowed and must be disclosed)")
    print(f"GDP_PPS coverage: {len(df_robustness)}/27 complete")
    print("\nGenerated files:")
    for file in files:
        print(f"- {file}")
    print("\nMain MP field for manuscript use: mp_estimated_eshoppers_16_74")
    print("Old total-population MP, when available, is retained only in optional comparison columns.")


def main() -> None:
    # Humanized introductory prints
    print("\n" + "="*70)
    print("Starting Data Collection for EU27 CBEC Market Entry Screening...")
    print("Compiling the revised public-data package for manuscript review.")
    print("Please hold on while the extractions run...")
    print("="*70 + "\n")

    df_backbone, df_overlays, df_validation, df_robustness, df_audit = run_builder(TARGET_YEAR)
    files = export_outputs(df_backbone, df_overlays, df_validation, df_robustness, df_audit, TARGET_YEAR)
    render_console_summary(df_backbone, df_overlays, df_validation, df_robustness, files)

    # -------------------------------------------------------------------------
    # NEW ZIP AND COLAB DOWNLOAD LOGIC
    # -------------------------------------------------------------------------
    zip_filename = f"{PACKAGE_PREFIX}_data_package_{TARGET_YEAR}.zip"

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            zipf.write(file)

    print(f"\n[Success] All generated files have been archived into: {zip_filename}")

    try:
        from google.colab import files as colab_files
        print("Google Colab detected. Initiating automatic download of the ZIP archive...")
        colab_files.download(zip_filename)
    except ImportError:
        print("Run complete. You can find the ZIP archive in your local execution folder.")


if __name__ == "__main__":
    main()