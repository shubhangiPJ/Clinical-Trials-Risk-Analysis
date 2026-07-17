"""
Project 1 - Step 2: Data Collection
====================================
Pulls clinical trial records from the official ClinicalTrials.gov API v2
(https://clinicaltrials.gov/data-api/api) for a chosen set of therapeutic areas.

This script has no dependency on any paid API key - ClinicalTrials.gov's API
is free and public. It handles pagination automatically, since the API caps
each response at a fixed number of records per page (see PAGE_SIZE below).

Run this in Google Colab, Jupyter, or any local Python environment with
internet access.

Install requirements first (uncomment if needed):
    pip install requests pandas

Output:
    clinical_trials_raw.csv - one row per trial, per therapeutic area searched
"""

import requests
import pandas as pd
import time
import sys

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

# ---- CONFIG: change these to whatever therapeutic areas you want to compare ----
THERAPEUTIC_AREAS = ["oncology", "cardiology", "neurology", "immunology"]
PAGE_SIZE = 1000          # max allowed per page by the API
MAX_PAGES_PER_AREA = 5    # 5 x 1000 = up to 5,000 trials per area; raise if you want more


def fetch_trials_for_condition(condition, page_size=PAGE_SIZE, max_pages=MAX_PAGES_PER_AREA):
    """Fetch all trial records for a given condition/therapeutic area, handling pagination.

    The ClinicalTrials.gov API v2 returns results in pages. Each response includes
    a 'nextPageToken' if more results exist beyond the current page. This function
    keeps requesting pages, passing that token back in, until either there's no
    token left (meaning we've reached the end of the results) or we hit max_pages
    (a safety cap so we don't accidentally pull tens of thousands of records).

    If a request fails (network issue, timeout, API error), we print a message
    and stop pulling more pages for this condition rather than crashing the
    entire script - any therapeutic areas processed so far, or afterward, are
    unaffected.

    Args:
        condition (str): The condition/therapeutic area to search for
            (e.g. "oncology", "cardiology"). Passed to the API's query.cond parameter.
        page_size (int): Number of records to request per page. Defaults to
            module-level PAGE_SIZE (max allowed by the API is 1000).
        max_pages (int): Safety cap on how many pages to pull for this condition,
            to avoid an unexpectedly huge/slow pull. Defaults to MAX_PAGES_PER_AREA.

    Returns:
        list[dict]: A list of raw study records (each one a nested JSON/dict
            structure as returned by the API, not yet flattened).
    """
    all_studies = []
    page_token = None
    pages_pulled = 0

    while pages_pulled < max_pages:
        params = {
            "query.cond": condition,
            "pageSize": page_size,
            "format": "json",
            "countTotal": "true",
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"  [{condition}] Network error on page {pages_pulled + 1}: {e}")
            print(f"  [{condition}] Stopping here - keeping the {len(all_studies)} studies already pulled.")
            break

        data = response.json()
        studies = data.get("studies", [])
        all_studies.extend(studies)
        pages_pulled += 1

        print(f"  [{condition}] pulled page {pages_pulled} "
              f"({len(studies)} studies, running total: {len(all_studies)})")

        # The API tells us whether there's another page via this token.
        # If it's missing/empty, we've reached the last page.
        page_token = data.get("nextPageToken")
        if not page_token:
            break

        time.sleep(0.3)  # small delay to be polite to the public API

    return all_studies


def flatten_study(study, therapeutic_area_label):
    """Extract the specific fields we need from one trial's nested JSON structure.

    The raw API response nests everything under 'protocolSection', which is
    further broken into modules (identificationModule, statusModule, etc.).
    This function pulls out just the fields relevant to our analysis and
    returns them as a single flat dictionary - i.e. one row for a dataframe,
    rather than a deeply nested structure.

    Args:
        study (dict): A single raw study record, as returned inside the
            'studies' list of the API response.
        therapeutic_area_label (str): The search term used to find this trial
            (e.g. "oncology"). Recorded so we know which of our four
            therapeutic areas this trial came from - useful since a trial can
            match more than one search term.

    Returns:
        dict: A flat dictionary with one key per field we care about
            (nct_id, phase, enrollment_count, etc.), ready to become one row
            in a pandas DataFrame.
    """
    protocol = study.get("protocolSection", {})

    identification = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    conditions = protocol.get("conditionsModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {})

    phases = design.get("phases", [])
    enrollment_info = design.get("enrollmentInfo", {})

    # If a trial has no listed conditions at all, mark it explicitly rather
    # than leaving an empty string, which is easy to misread as missing data.
    condition_list = conditions.get("conditions", [])
    clean_conditions = "; ".join(condition_list) if condition_list else "UNSPECIFIED"

    return {
        "nct_id": identification.get("nctId"),
        "brief_title": identification.get("briefTitle"),
        "therapeutic_area_search_term": therapeutic_area_label,
        "conditions": clean_conditions,
        "overall_status": status.get("overallStatus"),
        "phase": phases[0] if phases else "NA",
        "start_date": status.get("startDateStruct", {}).get("date"),
        "completion_date": status.get("completionDateStruct", {}).get("date"),
        "why_stopped": status.get("whyStopped"),
        "enrollment_count": enrollment_info.get("count"),
        "study_type": design.get("studyType"),
        "lead_sponsor": sponsor.get("leadSponsor", {}).get("name"),
        "lead_sponsor_class": sponsor.get("leadSponsor", {}).get("class"),
    }


def main():
    """Run the full collection process: fetch, flatten, deduplicate, and save.

    Loops over every therapeutic area in THERAPEUTIC_AREAS, fetches all trials
    for that area, flattens each one into a flat row, and combines everything
    into a single pandas DataFrame. Since a trial can match more than one
    search term (e.g. a trial could involve both cardiology and oncology
    conditions), duplicate NCT IDs are dropped before saving.

    If absolutely no data was collected across every therapeutic area (e.g.
    a total network outage), the script exits with an error rather than
    silently writing an empty CSV that would confuse the next step.

    Output:
        Writes clinical_trials_raw.csv to the current working directory.
    """
    all_rows = []
    for area in THERAPEUTIC_AREAS:
        print(f"\nFetching trials for: {area}")
        studies = fetch_trials_for_condition(area)
        for s in studies:
            all_rows.append(flatten_study(s, area))

    if not all_rows:
        print("\nNo data was collected across any therapeutic area - check your internet "
              "connection and try again. Exiting without writing a CSV.")
        sys.exit(1)

    df = pd.DataFrame(all_rows)
    print(f"\nTotal records collected: {len(df)}")

    # Drop exact duplicate NCT IDs (a trial can match more than one search term)
    df = df.drop_duplicates(subset="nct_id")
    print(f"After removing duplicates: {len(df)}")

    df.to_csv("clinical_trials_raw.csv", index=False)
    print("Saved to clinical_trials_raw.csv")


if __name__ == "__main__":
    main()
