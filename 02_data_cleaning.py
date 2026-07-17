"""
Project 1 - Step 3: Data Cleaning
==================================
Takes clinical_trials_raw.csv (the output of 01_data_collection.py) and
produces a cleaned, analysis-ready CSV: clinical_trials_clean.csv

The raw data from the API is messy in predictable ways: inconsistent phase
labels, mixed date granularity (some trials only record a year-month, others
a full date), missing/zero enrollment counts, and a mix of interventional
and observational study types that shouldn't be analyzed together. Each
function below handles one of these cleaning steps.

This script also tracks exactly how many values were changed/dropped at each
step and prints a before/after data quality summary at the end - both to the
console and to cleaning_summary.md, which you can paste directly into your
project README's data quality notes.
"""

import pandas as pd
import numpy as np

# Maps the API's raw phase codes to human-readable labels used throughout
# the rest of the analysis (dashboards, SQL output, etc.)
PHASE_MAP = {
    "PHASE1": "Phase 1",
    "PHASE2": "Phase 2",
    "PHASE3": "Phase 3",
    "PHASE4": "Phase 4",
    "EARLY_PHASE1": "Early Phase 1",
    "NA": "Not Applicable",
}

# A trial in any of these statuses is considered "terminated" for our
# risk-analysis purposes, since none of them reached their planned conclusion.
STOPPED_STATUSES = ["TERMINATED", "WITHDRAWN", "SUSPENDED"]


def parse_partial_date(date_str):
    """Convert an API date string into a pandas Timestamp, handling missing days.

    ClinicalTrials.gov sometimes records only a year and month (e.g. "2023-05")
    instead of a full date. pandas' default parser can fail on these partial
    dates, so this function falls back to appending "-01" (treating it as the
    1st of that month) if the first parse attempt fails.

    Args:
        date_str (str or float/NaN): The raw date string from the API, or NaN
            if the field was missing.

    Returns:
        pandas.Timestamp or pandas.NaT: The parsed date, or NaT (Not a Time)
            if the value was missing or unparseable.
    """
    if pd.isna(date_str):
        return pd.NaT
    try:
        return pd.to_datetime(date_str)
    except ValueError:
        try:
            return pd.to_datetime(date_str + "-01")
        except Exception:
            return pd.NaT


def clean_trials_data(df):
    """Apply all cleaning and feature-engineering steps to the raw trials dataframe.

    Steps performed, in order:
        1. Standardize phase values using PHASE_MAP.
        2. Parse start/completion dates (handling partial year-month dates).
        3. Derive trial duration in months; null out impossible values
           (negative durations, or durations over 20 years - both almost
           certainly data entry errors rather than real trials).
        4. Flag terminated/withdrawn/suspended trials with a binary column.
        5. Clean enrollment_count (treat 0 or negative as missing, since
           those aren't meaningful enrollment sizes).
        6. Fill missing sponsor class with "UNKNOWN" rather than leaving NaN.
        7. Filter down to INTERVENTIONAL studies only, since observational
           studies don't have comparable "termination" semantics and would
           skew duration/termination-rate statistics if mixed in.

    While applying these steps, this function also counts how many values
    were changed/dropped at each stage, so we have a clear before/after
    record of what cleaning actually did to the data.

    Args:
        df (pandas.DataFrame): The raw dataframe loaded from
            clinical_trials_raw.csv.

    Returns:
        tuple[pandas.DataFrame, dict]:
            - The cleaned dataframe, containing only the columns needed for
              downstream SQL analysis, filtered to interventional studies.
            - A dictionary of cleaning statistics (counts of rows/values
              affected by each step), used to print the summary report.
    """
    df = df.copy()
    stats = {}

    stats["raw_row_count"] = len(df)
    stats["missing_before"] = df.isna().sum().to_dict()

    # 1. Standardize phase values
    df["phase_clean"] = df["phase"].map(PHASE_MAP).fillna("Not Applicable")
    # Anything that didn't match a known key in PHASE_MAP - excluding rows
    # that were genuinely "NA" in the raw data - counts as an unmapped/unusual value.
    stats["phase_unmapped"] = int(
        ((~df["phase"].isin(PHASE_MAP.keys())) & (df["phase_clean"] == "Not Applicable")).sum()
    )

    # 2. Parse dates
    df["start_date_parsed"] = df["start_date"].apply(parse_partial_date)
    df["completion_date_parsed"] = df["completion_date"].apply(parse_partial_date)
    stats["start_dates_unparseable"] = int(
        df["start_date"].notna().sum() - df["start_date_parsed"].notna().sum()
    )
    stats["completion_dates_unparseable"] = int(
        df["completion_date"].notna().sum() - df["completion_date_parsed"].notna().sum()
    )

    # 3. Derived field: trial duration in months
    df["duration_months"] = (
        (df["completion_date_parsed"] - df["start_date_parsed"]).dt.days / 30.44
    )
    negative_mask = df["duration_months"] < 0
    extreme_mask = df["duration_months"] > 240  # >20 years = likely bad data
    stats["duration_negative_nulled"] = int(negative_mask.sum())
    stats["duration_extreme_nulled"] = int(extreme_mask.sum())
    df.loc[negative_mask, "duration_months"] = np.nan
    df.loc[extreme_mask, "duration_months"] = np.nan

    # 4. Derived field: terminated flag
    df["terminated_flag"] = df["overall_status"].isin(STOPPED_STATUSES).astype(int)

    # 5. Clean enrollment count
    df["enrollment_count"] = pd.to_numeric(df["enrollment_count"], errors="coerce")
    invalid_enrollment_mask = df["enrollment_count"] <= 0
    stats["enrollment_invalid_nulled"] = int(invalid_enrollment_mask.sum())
    df.loc[invalid_enrollment_mask, "enrollment_count"] = np.nan

    # 6. Standardize sponsor class
    stats["sponsor_class_filled_unknown"] = int(df["lead_sponsor_class"].isna().sum())
    df["lead_sponsor_class"] = df["lead_sponsor_class"].fillna("UNKNOWN")

    # 7. Keep only interventional studies for this analysis
    stats["non_interventional_dropped"] = int((df["study_type"] != "INTERVENTIONAL").sum())
    df_clean = df[df["study_type"] == "INTERVENTIONAL"].copy()

    stats["clean_row_count"] = len(df_clean)
    stats["pct_rows_retained"] = round(100 * len(df_clean) / stats["raw_row_count"], 1)

    final_cols = [
        "nct_id", "brief_title", "therapeutic_area_search_term", "conditions",
        "overall_status", "terminated_flag", "phase_clean",
        "start_date_parsed", "completion_date_parsed", "duration_months",
        "why_stopped", "enrollment_count", "lead_sponsor", "lead_sponsor_class",
    ]
    return df_clean[final_cols], stats


def print_cleaning_summary(stats):
    """Print a readable before/after data quality summary to the console.

    Args:
        stats (dict): The statistics dictionary returned by clean_trials_data().
    """
    print("\n" + "=" * 55)
    print("DATA CLEANING SUMMARY")
    print("=" * 55)
    print(f"Raw rows collected:            {stats['raw_row_count']}")
    print(f"Rows after cleaning:            {stats['clean_row_count']}")
    print(f"Rows retained:                  {stats['pct_rows_retained']}%")
    print("-" * 55)
    print(f"Phase values unmapped/unusual:  {stats['phase_unmapped']}")
    print(f"Start dates unparseable:        {stats['start_dates_unparseable']}")
    print(f"Completion dates unparseable:   {stats['completion_dates_unparseable']}")
    print(f"Durations nulled (negative):    {stats['duration_negative_nulled']}")
    print(f"Durations nulled (>20 years):   {stats['duration_extreme_nulled']}")
    print(f"Enrollment counts nulled:       {stats['enrollment_invalid_nulled']}")
    print(f"Sponsor class filled 'UNKNOWN': {stats['sponsor_class_filled_unknown']}")
    print(f"Non-interventional rows dropped:{stats['non_interventional_dropped']}")
    print("=" * 55)


def write_cleaning_summary_md(stats, path="cleaning_summary.md"):
    """Write the before/after data quality summary to a markdown file.

    This file is meant to be pasted directly into your project README under
    a "Data Quality Notes" section, or kept in the repo as documentation of
    what the cleaning step actually did.

    Args:
        stats (dict): The statistics dictionary returned by clean_trials_data().
        path (str): Output file path. Defaults to "cleaning_summary.md".
    """
    lines = [
        "## Data Cleaning Summary\n",
        f"- Raw rows collected: **{stats['raw_row_count']}**",
        f"- Rows after cleaning: **{stats['clean_row_count']}** ({stats['pct_rows_retained']}% retained)",
        f"- Phase values unmapped/unusual: {stats['phase_unmapped']}",
        f"- Start dates unparseable: {stats['start_dates_unparseable']}",
        f"- Completion dates unparseable: {stats['completion_dates_unparseable']}",
        f"- Durations nulled for being negative: {stats['duration_negative_nulled']}",
        f"- Durations nulled for exceeding 20 years: {stats['duration_extreme_nulled']}",
        f"- Enrollment counts nulled (zero/negative in raw data): {stats['enrollment_invalid_nulled']}",
        f"- Sponsor class values filled as 'UNKNOWN': {stats['sponsor_class_filled_unknown']}",
        f"- Non-interventional rows dropped (observational studies): {stats['non_interventional_dropped']}",
    ]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nWrote data quality summary to {path} - paste this into your README.")


def main():
    """Load the raw CSV, clean it, save the result, and print/save a summary.

    If clinical_trials_raw.csv doesn't exist yet (Step 2 hasn't been run,
    or this script is being run from the wrong folder), prints a clear
    message and exits instead of crashing with a raw traceback.

    Output:
        - clinical_trials_clean.csv
        - cleaning_summary.md (data quality report for your README)
    """
    try:
        df = pd.read_csv("clinical_trials_raw.csv")
    except FileNotFoundError:
        print("clinical_trials_raw.csv not found - run 01_data_collection.py first.")
        return

    df_clean, stats = clean_trials_data(df)

    df_clean.to_csv("clinical_trials_clean.csv", index=False)
    print("Saved cleaned data to clinical_trials_clean.csv")

    print_cleaning_summary(stats)
    write_cleaning_summary_md(stats)


if __name__ == "__main__":
    main()
