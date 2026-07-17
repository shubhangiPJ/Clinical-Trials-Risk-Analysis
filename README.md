# Clinical Trial Portfolio & Risk Intelligence Pipeline
<img width="1920" height="1020" alt="image" src="https://github.com/user-attachments/assets/5e5a194e-d080-45dd-a403-d8a1a87dd4b3" />
Live Dashboard:
https://public.tableau.com/views/Clinical_Trials_analysis/RiskOverview?:language=en-US&:sid=&:display_count=n&:origin=viz_share_link


## Business Case & Objective
Pharma market intelligence and asset development teams (the kind of work done by firms like Norstella/Citeline and ZS Associates) need clear visibility into pipeline risk to guide capital allocation and portfolio decisions. This project builds a data pipeline to evaluate clinical trial risk across four therapeutic areas: **Oncology, Cardiology, Neurology, and Immunology**.

**Business questions this project answers:**
- Which therapeutic areas have the highest trial termination rates, and what factors correlate with early termination?
- How do trial design factors (phase, enrollment size, sponsor type) relate to trial duration and outcome?

## Tools Used
- **Data collection:** Python (`requests`) — pulls data from the public ClinicalTrials.gov API v2
- **Data cleaning:** Python (`pandas`, `numpy`)
- **Storage:** SQLite (local relational database)
- **Analysis:** SQL
- **Visualization:** Tableau Public

## Pipeline Overview

### Step 1: Data Collection — `01_data_collection.py`
Pulls trial records from `clinicaltrials.gov/api/v2/studies` for each therapeutic area, handling pagination via the API's `nextPageToken`. Extracts key fields: NCT ID, condition, phase, status, dates, enrollment, sponsor. Output: `clinical_trials_raw.csv`.

### Step 2: Data Cleaning — `02_data_cleaning.py`
- Standardizes phase values (e.g., `PHASE1`, `PHASE2` → readable labels)
- Parses inconsistent date formats (API mixes `YYYY-MM` and `YYYY-MM-DD`)
- Calculates trial duration in months; nulls out impossible values (negative or >20 years, likely data entry errors)
- Flags terminated/withdrawn/suspended trials
- Filters to interventional studies only (removes observational study noise)

Output: `clinical_trials_clean.csv`.

### Step 3: Load to Database — `03_load_to_sqlite.py`
Loads the cleaned CSV into a local SQLite database (`clinical_trials.db`) for SQL-based analysis.

### Step 4: Analysis — `04_analysis_queries.sql`
SQL queries covering:
- Termination rate by therapeutic area
- Termination rate by phase
- Average trial duration by area and phase
- Top reasons trials stop
- Termination rate by sponsor type
- Termination rate by enrollment size bucket
- Trials started per year (trend line)

### Step 5: Modeling *(if included)*
`[Describe model here once built — e.g., logistic regression predicting termination using phase, enrollment size, and therapeutic area as features. State the accuracy/key coefficients.]`

---

## Key Findings
`[Fill this in after running the pipeline on real data — pull the actual numbers from your SQL output, e.g.:]`
- `[Therapeutic area X] shows a termination rate of __%, compared to __% average across all areas.`
- `[Phase __] trials show the highest/lowest termination rate at __%.`
- `[Sponsor type] trials have a termination rate of __% vs. __% for [other sponsor type].`
- `[Enrollment bucket] trials terminate at __% vs. __% for larger trials.`

*(Only include a finding here once you've actually verified it against your own query output — no placeholder numbers.)*

## Business Recommendation
`[This is the most important section — one or two sentences translating a finding into an actionable recommendation, the way a consulting deliverable would. E.g.: "Given the elevated termination rate in [area] driven largely by [enrollment shortfalls / a specific why_stopped reason], portfolio teams evaluating new [area] assets should weight site-selection and enrollment feasibility more heavily in early risk assessment."]`

## Dashboard
`[Link to your published Tableau Public dashboard]`

---

## How to Run Locally

```bash
git clone https://github.com/YOUR_USERNAME/clinical-trial-risk-analytics.git
cd clinical-trial-risk-analytics
pip install requests pandas
```

Then run the scripts in order:
```bash
python 01_data_collection.py
python 02_data_cleaning.py
python 03_load_to_sqlite.py
```
Then open `clinical_trials.db` in DB Browser for SQLite (or query it from Python) and run the queries in `04_analysis_queries.sql`.

## Data Source
[ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api) — public, no authentication required.
