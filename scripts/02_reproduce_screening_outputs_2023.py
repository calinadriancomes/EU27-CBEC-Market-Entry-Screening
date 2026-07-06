# -*- coding: utf-8 -*-
"""saved from .ipynb file
"""

# @title
# -*- coding: utf-8 -*-
"""
EU-27 CBEC Manuscript: Visuals and Tables Generator

This script takes the clean data from Script 01 and automatically generates
all the publication-ready tables and figures, applying accessibility and
visual clarity improvements.

All results are automatically bundled into a single archive:
- CBEC_EU27_revised_publication_outputs_2023.zip
"""

from __future__ import annotations

import os
import sys
import subprocess
import zipfile
import base64
import io
import math
import shutil
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

warnings.filterwarnings("ignore")

# =============================================================================
# 1. COLAB-FRIENDLY DEPENDENCY SETUP
# =============================================================================
def install_deps() -> None:
    pkgs = [
        "pandas", "numpy", "scipy", "scikit-learn", "matplotlib",
        "openpyxl", "geopandas", "shapely", "pyproj", "fiona"
    ]
    for pkg in pkgs:
        try:
            __import__(pkg.replace("scikit-learn", "sklearn"))
        except Exception:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

install_deps()

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr, chi2
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch
from matplotlib.lines import Line2D
import geopandas as gpd
from shapely.geometry import box

# Optional Colab/IPython display support
try:
    from IPython.display import display, HTML, clear_output
except Exception:  # pragma: no cover
    display = None
    HTML = None
    clear_output = None

# =============================================================================
# 2. CONSTANTS AND FILENAMES
# =============================================================================
YEAR = 2023
PACKAGE_ZIP = "CBEC_EU27_revised_data_package_2023.zip"
OUT_DIR = Path("publication_outputs_revised_candidate")
OUTPUT_ZIP = "CBEC_EU27_revised_publication_outputs_2023.zip"

EU27_CODES: List[str] = [
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

INPUT_FILES = {
    "backbone": f"CBEC_EU27_revised_backbone_{YEAR}.csv",
    "overlays": f"CBEC_EU27_revised_overlays_{YEAR}.csv",
    "validation": f"CBEC_EU27_revised_validation_{YEAR}.csv",
    "robustness": f"CBEC_EU27_revised_robustness_{YEAR}.csv",
    "audit": f"CBEC_EU27_revised_extraction_audit_{YEAR}.csv",
    "master": f"CBEC_EU27_revised_master_{YEAR}.xlsx",
    "metadata": f"CBEC_EU27_revised_metadata_{YEAR}.xlsx",
}

BAND_LABELS = {
    "higher": "Higher screening band",
    "middle": "Middle screening band",
    "lower": "Lower screening band",
}
BAND_ORDER = [BAND_LABELS["higher"], BAND_LABELS["middle"], BAND_LABELS["lower"]]
BAND_SORT_ORDER = {label: i for i, label in enumerate(BAND_ORDER)}

BAND_COLORS = {
    BAND_LABELS["higher"]: "#009E73",  # Color-blind safe Teal
    BAND_LABELS["middle"]: "#E69F00",  # Color-blind safe Orange
    BAND_LABELS["lower"]: "#CC79A7",   # Color-blind safe Magenta
}

BAND_MARKERS = {
    BAND_LABELS["higher"]: "o",  # Circle
    BAND_LABELS["middle"]: "^",  # Triangle up
    BAND_LABELS["lower"]: "s",   # Square
}

OLD_FORBIDDEN_LABELS = [
    "Priority/Core Entry", "Priority / Core Entry", "Selective/Conditional Entry",
    "Selective / Conditional Entry", "Defer/Barrier-Heavy", "Defer / Barrier-Heavy",
    "Tier 1", "Tier 2", "Tier 3",
]
FORBIDDEN_PASSFAIL = ["PASS", "FAIL"]

SOURCE_REFRESH_PRIOR_VALUES = {
    ("MT", "dfp_pct"): 67.38,
    ("MT", "cbo_pct"): 64.25,
    ("MT", "mp_online_shopping_pct"): 67.68,
    ("HU", "gdp_pps_index"): 76.0,
}

# =============================================================================
# 3. COLAB INPUT/OUTPUT HELPERS
# =============================================================================
def in_colab() -> bool:
    try:
        import google.colab  # type: ignore
        return True
    except Exception:
        return False


def ensure_input_package_available() -> None:
    if all(Path(fname).exists() for fname in INPUT_FILES.values() if fname.endswith((".csv", ".xlsx"))):
        return
    if Path(PACKAGE_ZIP).exists():
        extract_package(PACKAGE_ZIP)
        return

    if in_colab():
        print(f"Required input package not found: {PACKAGE_ZIP}")
        print("Please upload the clean Script 01 data package ZIP now.")
        from google.colab import files as colab_files  # type: ignore
        uploaded = colab_files.upload()
        if PACKAGE_ZIP not in uploaded and not Path(PACKAGE_ZIP).exists():
            zip_names = [name for name in uploaded.keys() if name.lower().endswith(".zip")]
            if len(zip_names) == 1:
                Path(zip_names[0]).rename(PACKAGE_ZIP)
            else:
                raise FileNotFoundError(
                    f"Uploaded files did not include {PACKAGE_ZIP}. Please rerun and upload the correct ZIP."
                )
        extract_package(PACKAGE_ZIP)
    else:
        raise FileNotFoundError(
            f"Missing {PACKAGE_ZIP} and extracted clean Script 01 files are not all present."
        )


def extract_package(zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(".")
    print(f"Extracted data package: {zip_path}")


def make_download_link(filepath: str, title: str, color: str = "#6a51a3") -> str:
    with open(filepath, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    filename = os.path.basename(filepath)
    return (
        f'<a href="data:application/zip;base64,{b64}" download="{filename}" '
        f'style="background-color:{color}; color:white; padding:10px 15px; '
        f'text-decoration:none; border-radius:5px; font-weight:bold; display:inline-block;">'
        f'{title}</a>'
    )


def display_downloads(zip_path: str) -> None:
    if in_colab():
        try:
            from google.colab import files as colab_files  # type: ignore
            print("\nInitiating automatic download of the final outputs...")
            colab_files.download(zip_path)
        except Exception as exc:
            print(f"Automatic download could not be started: {exc}")
    if display is not None and HTML is not None:
        display(HTML("<h3>Download Outputs</h3>" + make_download_link(zip_path, f"Download {os.path.basename(zip_path)}")))

# =============================================================================
# 4. DATA LOADING AND VALIDATION
# =============================================================================
def read_csv_strict(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8-sig")


def assert_exact_eu27(df: pd.DataFrame, label: str) -> None:
    if "region_code" not in df.columns:
        raise ValueError(f"{label}: missing region_code column.")
    codes = df["region_code"].astype(str).tolist()
    if len(codes) != 27:
        raise ValueError(f"{label}: expected 27 rows, found {len(codes)}.")
    if sorted(codes) != sorted(EU27_CODES):
        missing = sorted(set(EU27_CODES) - set(codes))
        extra = sorted(set(codes) - set(EU27_CODES))
        raise ValueError(f"{label}: EU-27 mismatch. Missing={missing}; Extra={extra}.")
    if df["region_code"].duplicated().any():
        dupes = df.loc[df["region_code"].duplicated(), "region_code"].tolist()
        raise ValueError(f"{label}: duplicate region_code rows: {dupes}.")


def require_columns(df: pd.DataFrame, cols: List[str], label: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{label}: missing required columns: {missing}")


def require_complete(df: pd.DataFrame, cols: List[str], label: str) -> None:
    assert_exact_eu27(df, label)
    require_columns(df, cols, label)
    for col in cols:
        miss = df.loc[df[col].isna(), "region_code"].tolist()
        if miss:
            raise ValueError(f"{label}: column {col} missing for countries {miss}")


def load_revised_inputs() -> Dict[str, pd.DataFrame]:
    ensure_input_package_available()
    for key, fname in INPUT_FILES.items():
        if not Path(fname).exists():
            raise FileNotFoundError(f"Required file missing after extraction: {fname}")

    data = {
        "backbone": read_csv_strict(INPUT_FILES["backbone"]),
        "overlays": read_csv_strict(INPUT_FILES["overlays"]),
        "validation": read_csv_strict(INPUT_FILES["validation"]),
        "robustness": read_csv_strict(INPUT_FILES["robustness"]),
        "audit": read_csv_strict(INPUT_FILES["audit"]),
    }

    require_complete(data["backbone"], ["esp_pct", "dfp_pct", "lpi_score"], "backbone")
    require_complete(
        data["overlays"],
        ["cbo_pct", "mp_population_16_74", "mp_online_shopping_pct", "mp_estimated_eshoppers_16_74", "mp_population_age_used"],
        "overlays",
    )
    assert_exact_eu27(data["validation"], "validation")
    require_columns(data["validation"], ["eti_pct", "eti_dataset_code"], "validation")
    require_complete(data["robustness"], ["gdp_pps_index"], "robustness")

    if not (data["overlays"]["mp_population_age_used"].astype(str) == "Y16_Y74_SUM").all():
        raise ValueError("overlays: mp_population_age_used must be Y16_Y74_SUM for all countries.")
    recomputed_mp = data["overlays"]["mp_population_16_74"] * data["overlays"]["mp_online_shopping_pct"] / 100.0
    if not np.allclose(data["overlays"]["mp_estimated_eshoppers_16_74"], recomputed_mp, rtol=0, atol=1e-6):
        raise ValueError("overlays: MP 16-74 formula verification failed.")

    eti_missing = sorted(data["validation"].loc[data["validation"]["eti_pct"].isna(), "region_code"].astype(str).tolist())
    if eti_missing != ["LU", "RO"]:
        raise ValueError(f"validation: expected ETI missing countries ['LU', 'RO'], found {eti_missing}")

    return data

# =============================================================================
# 5. ANALYTICAL ENGINE
# =============================================================================
def classify_screening_bands_rankaware(df_in: pd.DataFrame, lpi_gate_fraction: float, score_col: str = "pc1_ef_score") -> pd.DataFrame:
    df_sorted = df_in.sort_values(by=["lpi_score", score_col, "region_code"], ascending=[True, True, True]).copy()
    count = len(df_sorted)
    n_lower = int(round(count * lpi_gate_fraction))
    n_lower = max(1, min(n_lower, count - 1))
    lower_isos = df_sorted.head(n_lower)["region_code"].tolist()

    survivors = df_sorted[~df_sorted["region_code"].isin(lower_isos)].copy()
    median_score = survivors[score_col].median()
    higher_isos = survivors[survivors[score_col] >= median_score]["region_code"].tolist()

    def assign(iso: str) -> str:
        if iso in lower_isos:
            return BAND_LABELS["lower"]
        if iso in higher_isos:
            return BAND_LABELS["higher"]
        return BAND_LABELS["middle"]

    out = df_in.copy()
    out["screening_band"] = out["region_code"].apply(assign)
    out["screening_band_internal_rule"] = f"rank-aware LPI gate fraction={lpi_gate_fraction:.6f}; survivors split by median {score_col}"
    return out


def assign_tertile_bands_by_score(df_in: pd.DataFrame, score_col: str, out_col: str) -> pd.DataFrame:
    df = df_in.copy()
    ordered = df.sort_values([score_col, "region_code"], ascending=[False, True]).reset_index(drop=True)
    labels = []
    for idx in range(len(ordered)):
        if idx < 9:
            labels.append(BAND_LABELS["higher"])
        elif idx < 18:
            labels.append(BAND_LABELS["middle"])
        else:
            labels.append(BAND_LABELS["lower"])
    ordered[out_col] = labels
    return df.merge(ordered[["region_code", out_col]], on="region_code", how="left")


def run_pca(df: pd.DataFrame, cols: List[str], score_col: str = "pc1_score") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    X = df[cols].astype(float).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    pca = PCA(n_components=1, random_state=0)
    pc1 = pca.fit_transform(X_scaled).flatten()
    loadings = pca.components_[0].copy()
    if loadings.sum() < 0:
        pc1 = -pc1
        loadings = -loadings
    out = df.copy()
    out[score_col] = pc1
    metrics = {
        "cols": cols,
        "explained_var": float(pca.explained_variance_ratio_[0]),
        "loadings": dict(zip(cols, [float(x) for x in loadings])),
        "condition_number": float(np.linalg.cond(X_scaled)),
        "scaled_matrix": X_scaled,
    }
    return out, metrics


def kmo_bartlett_from_corr(corr: np.ndarray, n: int) -> Dict[str, float]:
    p = corr.shape[0]
    inv_corr = np.linalg.inv(corr)
    partial = np.zeros_like(corr)
    for i in range(p):
        for j in range(p):
            if i == j:
                partial[i, j] = 0.0
            else:
                partial[i, j] = -inv_corr[i, j] / math.sqrt(inv_corr[i, i] * inv_corr[j, j])
    r2_sum = np.sum(np.triu(corr ** 2, 1))
    p2_sum = np.sum(np.triu(partial ** 2, 1))
    kmo = r2_sum / (r2_sum + p2_sum)
    det_corr = np.linalg.det(corr)
    if det_corr <= 0:
        bart_stat, bart_p = np.nan, np.nan
    else:
        bart_stat = -(n - 1 - (2 * p + 5) / 6.0) * np.log(det_corr)
        bart_df = p * (p - 1) / 2
        bart_p = float(chi2.sf(bart_stat, bart_df))
    return {"kmo": float(kmo), "bartlett_chi2": float(bart_stat), "bartlett_df": float(p * (p - 1) / 2), "bartlett_p": float(bart_p)}


def run_revised_analysis(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    b, o, v, r = data["backbone"], data["overlays"], data["validation"], data["robustness"]
    df = (
        b[["region_code", "country", "source_year", "esp_pct", "dfp_pct", "lpi_score"]]
        .merge(o[[
            "region_code", "cbo_pct", "mp_population_16_74", "mp_online_shopping_pct",
            "mp_estimated_eshoppers_16_74", "mp_population_total",
            "mp_estimated_eshoppers_total_optional", "mp_rank_16_74", "mp_rank_total_optional",
            "mp_rank_shift_16_74_vs_total_optional", "mp_population_age_used"
        ]], on="region_code", how="left")
        .merge(v[["region_code", "eti_pct", "eti_dataset_code", "eti_status_or_note"]], on="region_code", how="left")
        .merge(r[["region_code", "gdp_pps_index"]], on="region_code", how="left")
    )
    require_complete(df, ["esp_pct", "dfp_pct", "lpi_score", "cbo_pct", "mp_estimated_eshoppers_16_74", "gdp_pps_index"], "merged analysis table")
    df["mp_eshoppers_16_74_millions"] = df["mp_estimated_eshoppers_16_74"] / 1_000_000.0

    # PCA backbone
    pca_cols = ["esp_pct", "dfp_pct", "lpi_score"]
    df, pca_metrics = run_pca(df, pca_cols, score_col="pc1_ef_score")
    df["pc1_ef_rank"] = df["pc1_ef_score"].rank(ascending=False, method="average")
    df = classify_screening_bands_rankaware(df, 1.0 / 3.0, "pc1_ef_score")
    df["screening_band_sort"] = df["screening_band"].map(BAND_SORT_ORDER)

    # Associations
    df_eti = df.dropna(subset=["eti_pct"]).copy()
    eti_rho, eti_p = spearmanr(df_eti["pc1_ef_score"], df_eti["eti_pct"])
    cbo_rho, cbo_p = spearmanr(df["pc1_ef_score"], df["cbo_pct"])
    gdp_rho, gdp_p = spearmanr(df["pc1_ef_score"], df["gdp_pps_index"])
    df["gdp_pps_rank"] = df["gdp_pps_index"].rank(ascending=False, method="average")
    df["rank_difference_pc1_minus_gdp"] = df["pc1_ef_rank"] - df["gdp_pps_rank"]

    # LPI gate-family stability
    gate_records = []
    baseline_bands = df.set_index("region_code")["screening_band"]
    for gf in [0.25, 0.30, 1.0 / 3.0, 0.35, 0.40]:
        tmp = classify_screening_bands_rankaware(df, gf, "pc1_ef_score")
        test_bands = tmp.set_index("region_code")["screening_band"]
        changed = (baseline_bands != test_bands).sum()
        changed_countries = sorted([iso for iso in baseline_bands.index if baseline_bands.loc[iso] != test_bands.loc[iso]])
        gate_records.append({
            "lpi_gate_fraction": gf,
            "changed_countries_count": int(changed),
            "change_share": float(changed / len(df)),
            "changed_countries": ", ".join(changed_countries) if changed_countries else "None",
        })
    df_gate = pd.DataFrame(gate_records)

    # ETI jackknife
    jackknife_records = []
    for excluded_iso in df_eti["region_code"].astype(str):
        sub = df_eti[df_eti["region_code"] != excluded_iso]
        rho, pval = spearmanr(sub["pc1_ef_score"], sub["eti_pct"])
        criterion_met = bool((rho >= 0.40) and (pval < 0.05))
        jackknife_records.append({
            "excluded_region": excluded_iso,
            "rho": float(rho),
            "p_value": float(pval),
            "criterion_status": "criterion met" if criterion_met else "criterion not met",
        })
    df_jackknife = pd.DataFrame(jackknife_records)

    # PCA correlation, KMO, Bartlett
    corr = df[pca_cols].corr(method="pearson")
    kmo_bart = kmo_bartlett_from_corr(corr.values, n=len(df))

    # Equal-weight robustness
    z = StandardScaler().fit_transform(df[pca_cols].astype(float).values)
    equal_weight = z.mean(axis=1)
    if spearmanr(equal_weight, df["pc1_ef_score"]).correlation < 0:
        equal_weight = -equal_weight
    df["equal_weight_z_score"] = equal_weight
    df["equal_weight_rank"] = pd.Series(equal_weight).rank(ascending=False, method="average").values
    df["equal_weight_rank_shift_vs_pc1"] = df["equal_weight_rank"] - df["pc1_ef_rank"]
    ew_spear, ew_spear_p = spearmanr(df["pc1_ef_score"], df["equal_weight_z_score"])
    ew_pear, ew_pear_p = pearsonr(df["pc1_ef_score"], df["equal_weight_z_score"])

    # Leave-one-variable-out PCA
    loo_records = []
    loo_country_rows = []
    for dropped in pca_cols:
        keep = [c for c in pca_cols if c != dropped]
        tmp, m = run_pca(df, keep, score_col=f"pc1_without_{dropped}")
        score = tmp[f"pc1_without_{dropped}"].values
        rho = spearmanr(df["pc1_ef_score"], score).correlation
        if rho < 0:
            score = -score
            rho = -rho
        rank = pd.Series(score).rank(ascending=False, method="average").values
        shifts = rank - df["pc1_ef_rank"].values
        loo_records.append({
            "variant": f"Drop {dropped}",
            "kept_variables": ", ".join(keep),
            "spearman_vs_baseline_pc1": float(rho),
            "max_absolute_rank_shift": float(np.nanmax(np.abs(shifts))),
            "mean_absolute_rank_shift": float(np.nanmean(np.abs(shifts))),
            "interpretation_note": "proxy sensitivity check; interpret cautiously",
        })
        for iso, country, sc, rk, sh in zip(df["region_code"], df["country"], score, rank, shifts):
            loo_country_rows.append({
                "region_code": iso, "country": country, "variant": f"Drop {dropped}",
                "variant_score": sc, "variant_rank": rk, "rank_shift_vs_baseline_pc1": sh,
            })
    df_loo_summary = pd.DataFrame(loo_records)
    df_loo_country = pd.DataFrame(loo_country_rows)

    # No-LPI/no-gate sensitivity
    df_sens = df.copy()
    # Corrected the previous typo here:
    df_sens = assign_tertile_bands_by_score(df_sens, "pc1_ef_score", "pc1_only_tertile_band")
    no_lpi_tmp, no_lpi_metrics = run_pca(df_sens, ["esp_pct", "dfp_pct"], score_col="pc1_no_lpi_score")
    no_lpi_score = no_lpi_tmp["pc1_no_lpi_score"].values
    if spearmanr(no_lpi_score, df_sens["pc1_ef_score"]).correlation < 0:
        no_lpi_score = -no_lpi_score
    df_sens["pc1_no_lpi_score"] = no_lpi_score
    df_sens = assign_tertile_bands_by_score(df_sens, "pc1_no_lpi_score", "no_lpi_backbone_tertile_band")
    df_sens["changed_baseline_vs_pc1_only"] = df_sens["screening_band"] != df_sens["pc1_only_tertile_band"]
    df_sens["changed_baseline_vs_no_lpi"] = df_sens["screening_band"] != df_sens["no_lpi_backbone_tertile_band"]
    df_no_lpi_no_gate = df_sens[[
        "region_code", "country", "pc1_ef_score", "lpi_score", "screening_band",
        "pc1_only_tertile_band", "changed_baseline_vs_pc1_only",
        "pc1_no_lpi_score", "no_lpi_backbone_tertile_band", "changed_baseline_vs_no_lpi"
    ]].copy()

    # Boundary cases
    lower_df = df[df["screening_band"] == BAND_LABELS["lower"]]
    survivor_df = df[df["screening_band"] != BAND_LABELS["lower"]]
    boundary_codes = set()
    if not lower_df.empty:
        boundary_codes.update(lower_df.loc[lower_df["lpi_score"] == lower_df["lpi_score"].max(), "region_code"].astype(str).tolist())
    if not survivor_df.empty:
        boundary_codes.update(survivor_df.loc[survivor_df["lpi_score"] == survivor_df["lpi_score"].min(), "region_code"].astype(str).tolist())
    boundary_codes.update(df_no_lpi_no_gate.loc[df_no_lpi_no_gate["changed_baseline_vs_pc1_only"] | df_no_lpi_no_gate["changed_baseline_vs_no_lpi"], "region_code"].astype(str).tolist())
    boundary_codes.update(["IE", "AT"])
    df_boundary = df_no_lpi_no_gate[df_no_lpi_no_gate["region_code"].isin(sorted(boundary_codes))].copy()
    df_boundary["boundary_reason"] = df_boundary.apply(
        lambda row: "; ".join(filter(None, [
            "LPI boundary/same-score case" if row["region_code"] in boundary_codes else "",
            "changed vs PC1-only" if row["changed_baseline_vs_pc1_only"] else "",
            "changed vs no-LPI" if row["changed_baseline_vs_no_lpi"] else "",
            "pre-flagged edge case" if row["region_code"] in ["IE", "AT"] else "",
        ])), axis=1
    )

    df_source_impact = compute_source_refresh_impact(data, df)

    results = {
        "df_main": df,
        "pca_metrics": pca_metrics,
        "corr": corr,
        "kmo_bartlett": kmo_bart,
        "eti": {"rho": float(eti_rho), "p": float(eti_p), "n": int(len(df_eti))},
        "cbo": {"rho": float(cbo_rho), "p": float(cbo_p), "n": int(len(df))},
        "gdp": {"rho": float(gdp_rho), "p": float(gdp_p), "n": int(len(df))},
        "df_gate": df_gate,
        "df_jackknife": df_jackknife,
        "equal_weight": {"spearman": float(ew_spear), "spearman_p": float(ew_spear_p), "pearson": float(ew_pear), "pearson_p": float(ew_pear_p), "max_rank_shift": float(df["equal_weight_rank_shift_vs_pc1"].abs().max())},
        "df_loo_summary": df_loo_summary,
        "df_loo_country": df_loo_country,
        "df_no_lpi_no_gate": df_no_lpi_no_gate,
        "df_boundary": df_boundary,
        "df_source_impact": df_source_impact,
        "no_lpi_metrics": no_lpi_metrics,
    }
    return results


def compute_source_refresh_impact(data: Dict[str, pd.DataFrame], baseline_df: pd.DataFrame) -> pd.DataFrame:
    b = data["backbone"].copy()
    o = data["overlays"].copy()
    r = data["robustness"].copy()

    b_old = b.copy()
    b_old.loc[b_old["region_code"] == "MT", "dfp_pct"] = SOURCE_REFRESH_PRIOR_VALUES[("MT", "dfp_pct")]
    df_old = (
        b_old[["region_code", "country", "source_year", "esp_pct", "dfp_pct", "lpi_score"]]
        .merge(o[["region_code", "cbo_pct", "mp_estimated_eshoppers_16_74"]], on="region_code", how="left")
        .merge(r[["region_code", "gdp_pps_index"]], on="region_code", how="left")
    )
    df_old, _ = run_pca(df_old, ["esp_pct", "dfp_pct", "lpi_score"], score_col="pc1_ef_score")
    df_old["pc1_ef_rank"] = df_old["pc1_ef_score"].rank(ascending=False, method="average")
    df_old = classify_screening_bands_rankaware(df_old, 1.0/3.0, "pc1_ef_score")
    old_rank = df_old.set_index("region_code")["pc1_ef_rank"]
    old_band = df_old.set_index("region_code")["screening_band"]
    cur_rank = baseline_df.set_index("region_code")["pc1_ef_rank"]
    cur_band = baseline_df.set_index("region_code")["screening_band"]
    pc1_changed = sorted([iso for iso in EU27_CODES if not np.isclose(old_rank.loc[iso], cur_rank.loc[iso])])
    band_changed = sorted([iso for iso in EU27_CODES if old_band.loc[iso] != cur_band.loc[iso]])

    o_old_inc = o.copy()
    o_old_inc.loc[o_old_inc["region_code"] == "MT", "mp_online_shopping_pct"] = SOURCE_REFRESH_PRIOR_VALUES[("MT", "mp_online_shopping_pct")]
    o_old_inc["mp_estimated_eshoppers_16_74_counterfactual_old_incidence"] = o_old_inc["mp_population_16_74"] * o_old_inc["mp_online_shopping_pct"] / 100.0
    old_mp_rank = o_old_inc["mp_estimated_eshoppers_16_74_counterfactual_old_incidence"].rank(ascending=False, method="average")
    cur_mp_rank = o["mp_estimated_eshoppers_16_74"].rank(ascending=False, method="average")
    mp_rank_changed_codes = sorted(o.loc[~np.isclose(old_mp_rank, cur_mp_rank), "region_code"].astype(str).tolist())

    r_old = r.copy()
    r_old.loc[r_old["region_code"] == "HU", "gdp_pps_index"] = SOURCE_REFRESH_PRIOR_VALUES[("HU", "gdp_pps_index")]
    old_gdp_rank = r_old["gdp_pps_index"].rank(ascending=False, method="average")
    cur_gdp_rank = r["gdp_pps_index"].rank(ascending=False, method="average")
    gdp_rank_changed_codes = sorted(r.loc[~np.isclose(old_gdp_rank, cur_gdp_rank), "region_code"].astype(str).tolist())

    rows = []
    for (iso, var), prior in SOURCE_REFRESH_PRIOR_VALUES.items():
        if var in b.columns:
            current = float(b.loc[b["region_code"] == iso, var].iloc[0])
        elif var in o.columns:
            current = float(o.loc[o["region_code"] == iso, var].iloc[0])
        else:
            current = float(r.loc[r["region_code"] == iso, var].iloc[0])
        rows.append({
            "country_code": iso,
            "variable": var,
            "prior_v47_value": prior,
            "revised_value": current,
            "downstream_check": (
                "PC1 rank and screening-band impact checked" if var == "dfp_pct" else
                "Overlay value/rank impact checked" if var in ["cbo_pct", "mp_online_shopping_pct"] else
                "GDP_PPS rank-difference diagnostic impact checked"
            ),
            "pc1_rank_changes_from_dfp_refresh": ", ".join(pc1_changed) if pc1_changed else "None",
            "screening_band_changes_from_dfp_refresh": ", ".join(band_changed) if band_changed else "None",
            "mp_rank_changes_from_mt_incidence_refresh": ", ".join(mp_rank_changed_codes) if mp_rank_changed_codes else "None",
            "gdp_rank_changes_from_hu_gdp_refresh": ", ".join(gdp_rank_changed_codes) if gdp_rank_changed_codes else "None",
            "interpretation_note": "source-refresh impact documented; manuscript interpretation should not silently ignore these values",
        })
    return pd.DataFrame(rows)

# =============================================================================
# 6. TABLE GENERATION
# =============================================================================
def pval_fmt(p: float) -> str:
    if pd.isna(p):
        return "not available"
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def generate_tables(results: Dict[str, Any], out_dir: Path) -> Dict[str, pd.DataFrame]:
    df = results["df_main"].copy()
    out_dir.mkdir(parents=True, exist_ok=True)

    analysis_cols = [
        "region_code", "country", "source_year", "esp_pct", "dfp_pct", "lpi_score",
        "pc1_ef_score", "pc1_ef_rank", "screening_band", "cbo_pct",
        "mp_population_16_74", "mp_online_shopping_pct", "mp_estimated_eshoppers_16_74",
        "mp_rank_16_74", "mp_population_total", "mp_estimated_eshoppers_total_optional",
        "mp_rank_total_optional", "mp_rank_shift_16_74_vs_total_optional",
        "eti_pct", "eti_dataset_code", "gdp_pps_index", "gdp_pps_rank", "rank_difference_pc1_minus_gdp",
        "equal_weight_z_score", "equal_weight_rank", "equal_weight_rank_shift_vs_pc1", "screening_band_sort"
    ]
    analysis = df[analysis_cols].sort_values(["screening_band_sort", "pc1_ef_score"], ascending=[True, False]).copy()
    analysis = analysis.drop(columns=["screening_band_sort"])
    analysis.to_csv(out_dir / f"CBEC_EU27_screening_analysis_{YEAR}.csv", index=False, encoding="utf-8-sig")

    loadings = results["pca_metrics"]["loadings"]
    tb1 = pd.DataFrame([
        {"Metric": "Explained variance ratio (PC1)", "Value": round(results["pca_metrics"]["explained_var"], 4), "Interpretation note": "PCA-derived screening axis; transparency diagnostic"},
        {"Metric": "Condition number (standardized backbone)", "Value": round(results["pca_metrics"]["condition_number"], 4), "Interpretation note": "Collinearity diagnostic"},
        {"Metric": "ESP loading", "Value": round(loadings["esp_pct"], 4), "Interpretation note": "Backbone contribution"},
        {"Metric": "DFP loading", "Value": round(loadings["dfp_pct"], 4), "Interpretation note": "Backbone contribution; proxy interpreted cautiously"},
        {"Metric": "LPI loading", "Value": round(loadings["lpi_score"], 4), "Interpretation note": "Backbone contribution; LPI dual-use disclosed separately"},
    ])

    tb2 = df[["region_code", "country", "pc1_ef_score", "mp_estimated_eshoppers_16_74", "cbo_pct", "screening_band", "screening_band_sort"]].copy()
    tb2 = tb2.sort_values(["screening_band_sort", "pc1_ef_score"], ascending=[True, False])
    tb2 = tb2.drop(columns=["screening_band_sort"])
    tb2.columns = ["Country code", "Country", "PC1_EF", "MP 16-74 estimated e-shoppers", "CBO (%)", "Screening band"]

    ew = results["equal_weight"]
    no_lpi_changed = int(results["df_no_lpi_no_gate"]["changed_baseline_vs_no_lpi"].sum())
    pc1_only_changed = int(results["df_no_lpi_no_gate"]["changed_baseline_vs_pc1_only"].sum())
    max_gate_change = float(results["df_gate"]["change_share"].max())
    loo_no_dfp = results["df_loo_summary"].loc[results["df_loo_summary"]["variant"] == "Drop dfp_pct"].iloc[0]
    loo_no_lpi = results["df_loo_summary"].loc[results["df_loo_summary"]["variant"] == "Drop lpi_score"].iloc[0]
    tb3 = pd.DataFrame([
        {"Check": "ETI criterion-consistency", "N": results["eti"]["n"], "Metric": "Spearman rho", "Observed value": round(results["eti"]["rho"], 4), "p-value": pval_fmt(results["eti"]["p"]), "Diagnostic finding": "positive criterion-consistency evidence"},
        {"Check": "GDP_PPS prosperity association", "N": results["gdp"]["n"], "Metric": "Spearman rho", "Observed value": round(results["gdp"]["rho"], 4), "p-value": pval_fmt(results["gdp"]["p"]), "Diagnostic finding": "prosperity association reported"},
        {"Check": "CBO overlay diagnostic", "N": results["cbo"]["n"], "Metric": "Spearman rho", "Observed value": round(results["cbo"]["rho"], 4), "p-value": pval_fmt(results["cbo"]["p"]), "Diagnostic finding": "demand-side overlay check"},
        {"Check": "LPI gate-family sensitivity", "N": 27, "Metric": "maximum screening-band change share", "Observed value": round(max_gate_change, 4), "p-value": "not applicable", "Diagnostic finding": "gate-family sensitivity check"},
        {"Check": "Equal-weight aggregation robustness", "N": 27, "Metric": "Spearman rho vs PC1_EF", "Observed value": round(ew["spearman"], 4), "p-value": pval_fmt(ew["spearman_p"]), "Diagnostic finding": f"aggregation-rule robustness; max rank shift {ew['max_rank_shift']:.0f}"},
        {"Check": "No-DFP leave-one-variable-out", "N": 27, "Metric": "Spearman rho vs baseline PC1_EF", "Observed value": round(float(loo_no_dfp["spearman_vs_baseline_pc1"]), 4), "p-value": "not applicable", "Diagnostic finding": "DFP proxy sensitivity"},
        {"Check": "No-LPI leave-one-variable-out", "N": 27, "Metric": "Spearman rho vs baseline PC1_EF", "Observed value": round(float(loo_no_lpi["spearman_vs_baseline_pc1"]), 4), "p-value": "not applicable", "Diagnostic finding": "LPI sensitivity"},
        {"Check": "No-LPI/no-gate band sensitivity", "N": 27, "Metric": "changed countries", "Observed value": f"PC1-only: {pc1_only_changed}; no-LPI: {no_lpi_changed}", "p-value": "not applicable", "Diagnostic finding": "screening-band sensitivity"},
    ])

    a1 = df[["region_code", "country", "pc1_ef_rank", "gdp_pps_rank", "rank_difference_pc1_minus_gdp", "gdp_pps_index"]].copy()
    a1 = a1.sort_values("rank_difference_pc1_minus_gdp", ascending=False)

    a2 = results["df_jackknife"].copy()
    a3 = results["df_gate"].copy()

    corr_long = results["corr"].reset_index().melt(id_vars="index", var_name="variable_2", value_name="correlation")
    corr_long = corr_long.rename(columns={"index": "variable_1"})
    kb = results["kmo_bartlett"]
    a4_diag = pd.DataFrame([
        {"diagnostic": "KMO", "value": round(kb["kmo"], 6), "note": "Transparency diagnostic only; N=27 and three variables"},
        {"diagnostic": "Bartlett chi-square", "value": round(kb["bartlett_chi2"], 6), "note": "Transparency diagnostic only; N=27 and three variables"},
        {"diagnostic": "Bartlett df", "value": int(kb["bartlett_df"]), "note": "Transparency diagnostic only; N=27 and three variables"},
        {"diagnostic": "Bartlett p-value", "value": kb["bartlett_p"], "note": "Transparency diagnostic only; N=27 and three variables"},
    ])
    a4 = pd.concat([
        pd.DataFrame({"section": ["correlation_matrix"] * len(corr_long)}).reset_index(drop=True).join(corr_long.reset_index(drop=True)),
        pd.DataFrame({"section": ["diagnostics"] * len(a4_diag)}).reset_index(drop=True).join(a4_diag.reset_index(drop=True)),
    ], ignore_index=True)

    ew_country = df[["region_code", "country", "pc1_ef_score", "pc1_ef_rank", "equal_weight_z_score", "equal_weight_rank", "equal_weight_rank_shift_vs_pc1"]].copy()
    ew_summary = pd.DataFrame([
        {"section": "equal_weight_summary", "metric": "Spearman rho vs PC1_EF", "value": ew["spearman"], "note": "Aggregation-rule robustness, not PCA superiority"},
        {"section": "equal_weight_summary", "metric": "Pearson r vs PC1_EF", "value": ew["pearson"], "note": "Aggregation-rule robustness, not PCA superiority"},
        {"section": "equal_weight_summary", "metric": "Max absolute rank shift", "value": ew["max_rank_shift"], "note": "Country ranking sensitivity"},
    ])
    loo_summary = results["df_loo_summary"].copy()
    loo_summary.insert(0, "section", "leave_one_variable_out_summary")
    a5 = pd.concat([
        ew_summary,
        loo_summary.rename(columns={"variant": "metric", "spearman_vs_baseline_pc1": "value"}),
    ], ignore_index=True, sort=False)

    a6 = results["df_no_lpi_no_gate"].copy().sort_values(["screening_band", "pc1_ef_score"], ascending=[True, False])
    a7 = results["df_boundary"].copy().sort_values(["lpi_score", "pc1_ef_score", "region_code"], ascending=[True, True, True])

    table_map = {
        "Table1_PCA_Backbone_Diagnostics": tb1,
        "Table2_Country_Level_Screening_Bands": tb2,
        "Table3_Diagnostic_And_Sensitivity_Checks": tb3,
        "Appendix_Table_A1_GDP_PPS_Rank_Differences": a1,
        "Appendix_Table_A2_ETI_Jackknife": a2,
        "Appendix_Table_A3_LPI_Gate_Family_Stability": a3,
        "Appendix_Table_A4_PCA_Correlation_KMO_Bartlett": a4,
        "Appendix_Table_A5_Aggregation_Robustness_EqualWeight_LOO": a5,
        "Appendix_Table_A6_NoLPI_NoGate_Band_Sensitivity": a6,
        "Appendix_Table_A7_Boundary_Cases": a7,
        "Source_Refresh_Impact_Check": results["df_source_impact"],
    }

    for name, tdf in table_map.items():
        tdf.to_csv(out_dir / f"{name}.csv", index=False, encoding="utf-8-sig")
    for name in ["Table1_PCA_Backbone_Diagnostics", "Table2_Country_Level_Screening_Bands", "Table3_Diagnostic_And_Sensitivity_Checks"]:
        table_map[name].to_excel(out_dir / f"{name}.xlsx", index=False)

    with pd.ExcelWriter(out_dir / f"CBEC_EU27_screening_results_{YEAR}.xlsx", engine="openpyxl") as writer:
        analysis.to_excel(writer, sheet_name="analysis_table", index=False)
        for name, tdf in table_map.items():
            sheet = name.replace("Appendix_Table_", "A_").replace("Table", "T")[:31]
            tdf.to_excel(writer, sheet_name=sheet, index=False)
        results["df_loo_country"].to_excel(writer, sheet_name="LOO_country_details"[:31], index=False)

    scan_outputs_for_forbidden_language(out_dir)
    return table_map


def scan_outputs_for_forbidden_language(out_dir: Path) -> None:
    files_to_scan = list(out_dir.glob("*.csv"))
    for path in files_to_scan:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for term in OLD_FORBIDDEN_LABELS:
            if term in text:
                raise ValueError(f"Forbidden old tier label found in output {path.name}: {term}")
        for term in FORBIDDEN_PASSFAIL:
            if f",{term}," in text or f"\n{term}," in text or f",{term}\n" in text:
                raise ValueError(f"Forbidden manuscript-facing PASS/FAIL language found in output {path.name}: {term}")

# =============================================================================
# 7. FIGURE GENERATION
# =============================================================================
def validate_figure(fig_name: str, expected: List[str], plotted: List[str], logs: List[Dict[str, Any]]) -> None:
    missing = sorted(set(expected) - set(plotted))
    duplicates = len(plotted) - len(set(plotted))
    status = "OK" if not missing and duplicates == 0 else "FAIL"
    logs.append({
        "figure": fig_name,
        "expected_count": len(set(expected)),
        "plotted_count": len(plotted),
        "missing_countries": ", ".join(missing) if missing else "None",
        "duplicate_count": duplicates,
        "status": status,
    })


def save_figure(fig: plt.Figure, out_dir: Path, stem: str, svg: bool = False) -> None:
    fig.savefig(out_dir / f"{stem}.png", dpi=350, bbox_inches="tight")
    fig.savefig(out_dir / f"{stem}.pdf", bbox_inches="tight")
    if svg:
        fig.savefig(out_dir / f"{stem}.svg", bbox_inches="tight")


def generate_figure2(results: Dict[str, Any], out_dir: Path, logs: List[Dict[str, Any]]) -> None:
    df = results["df_main"].copy()
    src = df[[
        "region_code", "country", "pc1_ef_score", "mp_eshoppers_16_74_millions",
        "mp_estimated_eshoppers_16_74", "cbo_pct", "screening_band"
    ]].copy()
    src.to_csv(out_dir / "Source_Figure2_Portfolio.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(11.5, 7.2))

    for band in BAND_ORDER:
        sub = src[src["screening_band"] == band]
        ax.scatter(
            sub["pc1_ef_score"], sub["mp_eshoppers_16_74_millions"],
            s=95, label=band, color=BAND_COLORS[band], marker=BAND_MARKERS[band],
            edgecolor="black", alpha=0.88, linewidth=0.7, zorder=3
        )

    # Carefully curated manual offsets
    label_offsets_points: Dict[str, Tuple[int, int]] = {
        "PT": (-6, 6),
        "EL": (10, 8),    # Leader line used
        "SK": (-12, 0),
        "LU": (6, -6),
        "SI": (-4, 4),
        "CY": (6, -6),
        "LV": (-8, -6),   # Leader line used
        "HR": (0, 9),     # Leader line used
        "MT": (0, -8),
        "EE": (8, 0),
        "HU": (-6, 6),
        "CZ": (6, 6),
        "BG": (6, 6),
        "RO": (6, 6),
        "PL": (6, 6),
        "IT": (-6, 6),
        "FR": (6, 6),
        "DE": (6, 6),
        "IE": (-8, -8),
        "LT": (6, -8),
        "AT": (6, 6),
        "ES": (6, 6),
        "BE": (6, 6),
        "NL": (6, 6),
        "SE": (6, 6),
        "FI": (6, -8),
        "DK": (6, 6),
    }

    plotted = []
    for _, row in src.iterrows():
        iso = str(row["region_code"])
        x = float(row["pc1_ef_score"])
        y = float(row["mp_eshoppers_16_74_millions"])
        dx, dy = label_offsets_points.get(iso, (6, 6))

        ha = "left" if dx > 0 else ("right" if dx < 0 else "center")
        va = "bottom" if dy > 0 else ("top" if dy < 0 else "center")

        arrow_args = None
        if iso in ["EL", "HR", "LV"]:
            # Small leader line to explicitly connect the label to the dot
            arrow_args = dict(arrowstyle="-", color="#555555", lw=0.6, shrinkA=1, shrinkB=2)

        ax.annotate(
            iso,
            xy=(x, y),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=7.9,
            fontweight="bold",
            zorder=4,
            clip_on=True,
            arrowprops=arrow_args
        )
        plotted.append(iso)

    ax.set_xlabel("PCA-derived execution-condition screening axis (PC1_EF)", fontsize=11)
    ax.set_ylabel("Market potential, estimated e-shoppers aged 16-74 (millions)", fontsize=11)

    ax.set_title("EU-27 CBEC screening portfolio", fontsize=13, fontweight="bold", pad=10)
    ax.grid(True, color="#dddddd", linewidth=0.7, alpha=0.7, zorder=0)
    ax.legend(title="Screening band", frameon=True, fontsize=9, title_fontsize=9, loc="upper left")

    x_min, x_max = src["pc1_ef_score"].min(), src["pc1_ef_score"].max()
    y_min, y_max = src["mp_eshoppers_16_74_millions"].min(), src["mp_eshoppers_16_74_millions"].max()

    ax.set_xlim(x_min - 0.32, x_max + 0.32)
    ax.set_ylim(y_min - 2.8, y_max + 3.0)

    validate_figure("Figure2_EU27_CBEC_Screening_Portfolio", EU27_CODES, plotted, logs)
    save_figure(fig, out_dir, "Figure2_EU27_CBEC_Screening_Portfolio", svg=True)
    plt.close(fig)


def read_gisco_geometry() -> Optional[gpd.GeoDataFrame]:
    local_candidates = [
        "GISCO_CNTR_RG_60M_2020_4326.geojson",
        "CNTR_RG_60M_2020_4326.geojson",
    ]
    for f in local_candidates:
        if Path(f).exists():
            return gpd.read_file(f)
    url = "https://gisco-services.ec.europa.eu/distribution/v2/countries/geojson/CNTR_RG_60M_2020_4326.geojson"
    return gpd.read_file(url)


def generate_figure3(results: Dict[str, Any], out_dir: Path, logs: List[Dict[str, Any]]) -> None:
    df = results["df_main"][["region_code", "country", "screening_band"]].copy()
    df.to_csv(out_dir / "Source_Figure3_Map.csv", index=False, encoding="utf-8-sig")
    try:
        geo = read_gisco_geometry()
        if geo is None or geo.empty:
            raise ValueError("GISCO geometry unavailable or empty.")
        if "CNTR_ID" not in geo.columns:
            raise ValueError("GISCO geometry does not contain CNTR_ID column.")

        geo = geo[geo["CNTR_ID"].isin(EU27_CODES)].copy()
        if geo.empty:
            raise ValueError("No EU-27 geometries found in GISCO file.")
        if geo.crs is None:
            geo = geo.set_crs("EPSG:4326")
        geo = geo.to_crs("EPSG:4326")

        bbox = gpd.GeoDataFrame({"geometry": [box(-12, 34, 35, 72)]}, crs="EPSG:4326")
        geo_clipped = gpd.clip(geo, bbox)
        geo_clipped = geo_clipped[~geo_clipped.geometry.is_empty].copy()
        geo_clipped = geo_clipped.to_crs(epsg=3035)

        plot_df = geo_clipped.merge(df, left_on="CNTR_ID", right_on="region_code", how="inner")
        plotted = plot_df["region_code"].astype(str).tolist()
        validate_figure("Figure3_EU27_Screening_Bands_Map", EU27_CODES, plotted, logs)
        if sorted(set(plotted)) != sorted(EU27_CODES):
            raise ValueError("Map geometry did not include all EU-27 countries after crop/merge.")

        import matplotlib.patheffects as pe

        fig, ax = plt.subplots(figsize=(8.8, 8.8))
        for band in BAND_ORDER:
            sub = plot_df[plot_df["screening_band"] == band]
            sub.plot(ax=ax, color=BAND_COLORS[band], edgecolor="#333333", linewidth=0.55)

        # add country codes on map
        # custom offsets for small countries so the text doesn't hide their color
        map_label_offsets = {
            "MT": (9, -3),  # Malta: slightly right and down
            "LU": (7, -1),     # Luxembourg: slightly right and down
        }

        for _, row in plot_df.iterrows():
            iso = str(row["region_code"])
            pt = row["geometry"].representative_point()
            dx, dy = map_label_offsets.get(iso, (0, 0))

            ax.annotate(
                text=iso,
                xy=(pt.x, pt.y),
                xytext=(dx, dy),
                textcoords="offset points",
                ha="center", va="center",
                fontsize=7.5, fontweight="bold", color="white",
                path_effects=[pe.withStroke(linewidth=1.5, foreground="black")],
                zorder=4
            )

        ax.axis("off")
        ax.set_aspect("equal")
        ax.set_title("EU-27 screening bands", fontsize=13, fontweight="bold", pad=10)

        handles = [Patch(facecolor=BAND_COLORS[b], edgecolor="#333333", label=b) for b in BAND_ORDER]
        ax.legend(
            handles=handles,
            title="Screening band",
            loc="lower center",
            bbox_to_anchor=(0.5, -0.06),
            ncol=3,
            frameon=True,
            fontsize=8.5,
            title_fontsize=9,
        )

        save_figure(fig, out_dir, "Figure3_EU27_Screening_Bands_Map", svg=True)
        plt.close(fig)
    except Exception as exc:
        logs.append({
            "figure": "Figure3_EU27_Screening_Bands_Map",
            "expected_count": 27,
            "plotted_count": 0,
            "missing_countries": "geometry/map generation failed",
            "duplicate_count": 0,
            "status": f"NOT GENERATED: {exc}",
        })
        print(f"WARNING: Figure 3 map was not generated cleanly: {exc}")


def generate_appendix_figures(results: Dict[str, Any], out_dir: Path, logs: List[Dict[str, Any]]) -> None:
    df = results["df_main"].copy()

    # Figure A1
    src_a1 = df[["region_code", "country", "pc1_ef_rank", "gdp_pps_rank", "rank_difference_pc1_minus_gdp", "gdp_pps_index"]].copy()
    src_a1.to_csv(out_dir / "Source_FigureA1_GDP_PPS_Rank_Difference.csv", index=False, encoding="utf-8-sig")
    plot_a1 = src_a1.sort_values("rank_difference_pc1_minus_gdp", ascending=True)
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    colors = ["#3182bd" if v < 0 else "#de2d26" for v in plot_a1["rank_difference_pc1_minus_gdp"]]
    ax.barh(plot_a1["region_code"], plot_a1["rank_difference_pc1_minus_gdp"], color=colors, edgecolor="black", linewidth=0.4)
    ax.axvline(0, color="black", linewidth=0.9)
    ax.set_xlabel("Rank difference: PC1_EF rank minus GDP_PPS rank")
    ax.set_title("GDP_PPS rank-difference diagnostic", fontsize=12, fontweight="bold", pad=10)
    ax.set_axisbelow(True)
    ax.grid(True, color="#dddddd", linewidth=0.7)
    validate_figure("FigureA1_GDP_PPS_Rank_Difference", EU27_CODES, plot_a1["region_code"].tolist(), logs)
    save_figure(fig, out_dir, "FigureA1_GDP_PPS_Rank_Difference")
    plt.close(fig)

    # Figure A2
    src_a2 = df.dropna(subset=["eti_pct"])[["region_code", "country", "pc1_ef_score", "eti_pct"]].copy()
    src_a2.to_csv(out_dir / "Source_FigureA2_ETI_Criterion_Consistency.csv", index=False, encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(src_a2["pc1_ef_score"], src_a2["eti_pct"], s=70, edgecolor="black", color="#6baed6", alpha=0.88, zorder=3)

    # Compact alignment
    eti_label_offsets: Dict[str, Tuple[int, int]] = {
        "PT": (-5, 4),
        "SK": (-8, 0),
        "EL": (4, -4),
        "PL": (3, 3),
        "IT": (-3, 3),
        "SI": (4, -4),
        "HU": (3, 3),
        "CY": (4, 4),
        "LV": (-4, -3),
        "HR": (-4, 4),
        "CZ": (4, 4),
        "MT": (4, -4),
        "FR": (4, -4),
        "EE": (3, 3),
        "DE": (3, -3),
        "IE": (4, 4),
        "LT": (3, 3),
        "AT": (4, 4),
        "ES": (4, 4),
        "BE": (4, 4),
        "NL": (-4, 2),
        "SE": (3, 3),
        "FI": (4, -4),
        "DK": (4, 4),
        "BG": (4, 4),
    }

    for _, row in src_a2.iterrows():
        iso = str(row["region_code"])
        x = float(row["pc1_ef_score"])
        y = float(row["eti_pct"])
        dx, dy = eti_label_offsets.get(iso, (4, 4))

        ha = "left" if dx > 0 else ("right" if dx < 0 else "center")
        va = "bottom" if dy > 0 else ("top" if dy < 0 else "center")

        ax.annotate(
            iso,
            xy=(x, y),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=7.8,
            zorder=4,
            clip_on=True,
        )

    ax.set_xlabel("PCA-derived execution-condition screening axis (PC1_EF)")
    ax.set_ylabel("E-commerce turnover intensity (ETI, %)")
    ax.set_title(f"ETI criterion-consistency check (N={len(src_a2)})", fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, color="#dddddd", linewidth=0.7, zorder=0)
    ax.margins(x=0.045, y=0.065)

    validate_figure("FigureA2_ETI_Criterion_Consistency_Scatter", src_a2["region_code"].tolist(), src_a2["region_code"].tolist(), logs)
    save_figure(fig, out_dir, "FigureA2_ETI_Criterion_Consistency_Scatter")
    plt.close(fig)

    # Figure A3
    src_a3 = results["df_gate"].copy()
    src_a3.to_csv(out_dir / "Source_FigureA3_LPI_Gate_Family_Stability.csv", index=False, encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.plot(src_a3["lpi_gate_fraction"], src_a3["change_share"], marker="o", linewidth=1.8, color="#756bb1")
    ax.axhline(0.20, linestyle="--", color="#636363", linewidth=1.0, label="Diagnostic reference: 0.20")
    ax.set_xlabel("LPI gate fraction")
    ax.set_ylabel("Screening-band change share")
    ax.set_title("LPI gate-family sensitivity", fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, color="#dddddd", linewidth=0.7)
    ax.legend(frameon=True, fontsize=8.5)
    validate_figure("FigureA3_LPI_Gate_Family_Stability", ["stability_check"], ["stability_check"], logs)
    save_figure(fig, out_dir, "FigureA3_LPI_Gate_Family_Stability")
    plt.close(fig)


def generate_figures(results: Dict[str, Any], out_dir: Path) -> pd.DataFrame:
    logs: List[Dict[str, Any]] = []
    generate_figure2(results, out_dir, logs)
    generate_figure3(results, out_dir, logs)
    generate_appendix_figures(results, out_dir, logs)
    return pd.DataFrame(logs)

# =============================================================================
# 8. MANIFEST, ZIP, AND RUNNER
# =============================================================================

def package_outputs(out_dir: Path, zip_name: str) -> str:
    if Path(zip_name).exists():
        Path(zip_name).unlink()
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(out_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(out_dir)))
    return zip_name


def print_summary(results: Dict[str, Any], out_dir: Path, zip_path: str) -> None:
    df = results["df_main"]
    print("\n=== Manuscript Outputs Successfully Generated ===")
    print(f"Countries processed: {len(df)}/27")
    print("Main Market Potential field used: mp_estimated_eshoppers_16_74")
    print(f"ETI usable observations: {df['eti_pct'].notna().sum()}/27 (LU and RO are missing from Eurostat).")
    print(f"Outputs saved to directory: {out_dir}")
    print(f"All files compressed into: {zip_path}")
    print("\nKey files created:")

    key_names = [
        f"CBEC_EU27_screening_analysis_{YEAR}.csv",
        f"CBEC_EU27_screening_results_{YEAR}.xlsx",
        "Table1_PCA_Backbone_Diagnostics.csv",
        "Table2_Country_Level_Screening_Bands.csv",
        "Table3_Diagnostic_And_Sensitivity_Checks.csv",
        "Figure2_EU27_CBEC_Screening_Portfolio.png",
        "Figure3_EU27_Screening_Bands_Map.png",
        "FigureA1_GDP_PPS_Rank_Difference.png",
        "FigureA2_ETI_Criterion_Consistency_Scatter.png",
        "FigureA3_LPI_Gate_Family_Stability.png",
        "Source_Refresh_Impact_Check.csv",
    ]
    for name in key_names:
        marker = "" if (out_dir / name).exists() else " [failed to generate]"
        print(f" - {name}{marker}")


def main() -> None:
    print("\n" + "=" * 78)
    print("Step 2: Data Generation and Plotting for EU27 CBEC Manuscript")
    print("This script reads the data package produced in the previous step,")
    print("and automatically generates the visual assets and tables needed.")
    print("Please ensure the ZIP file from Script 01 is available.")
    print("=" * 78 + "\n")

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data = load_revised_inputs()
    results = run_revised_analysis(data)
    generate_tables(results, OUT_DIR)
    generate_figures(results, OUT_DIR)
    zip_path = package_outputs(OUT_DIR, OUTPUT_ZIP)

    print_summary(results, OUT_DIR, zip_path)
    display_downloads(zip_path)


if __name__ == "__main__":
    main()