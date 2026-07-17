-- Project 1 - Step 4: Analysis Queries
-- Run these against clinical_trials.db (table: trials)
-- Tool: DB Browser for SQLite, or Python (pd.read_sql(query, conn))

-- Q1: Termination rate by therapeutic area
-- (This is your headline stat for the dashboard)
SELECT
    therapeutic_area_search_term,
    COUNT(*) AS total_trials,
    SUM(terminated_flag) AS terminated_trials,
    ROUND(100.0 * SUM(terminated_flag) / COUNT(*), 1) AS termination_rate_pct
FROM trials
GROUP BY therapeutic_area_search_term
ORDER BY termination_rate_pct DESC;


-- Q2: Termination rate by phase (which phase is riskiest?)
-- (Aggregated across all therapeutic areas - this is your single headline
-- number per phase, e.g. for a "phase funnel" dashboard visual. For the
-- same breakdown split out by therapeutic area, see Q2b below.)
SELECT
    phase_clean,
    COUNT(*) AS total_trials,
    ROUND(100.0 * SUM(terminated_flag) / COUNT(*), 1) AS termination_rate_pct
FROM trials
WHERE phase_clean != 'Not Applicable'
GROUP BY phase_clean
ORDER BY
    CASE phase_clean
        WHEN 'Early Phase 1' THEN 0
        WHEN 'Phase 1' THEN 1
        WHEN 'Phase 2' THEN 2
        WHEN 'Phase 3' THEN 3
        WHEN 'Phase 4' THEN 4
    END;


-- Q2b: Termination rate by therapeutic area AND phase
-- (Drill-down version of Q2 - answers "is Phase 2 riskier in oncology
-- specifically than Phase 2 in cardiology?" rather than an overall average.
-- Same phase-ordering logic and 'Not Applicable' exclusion as Q2.)
SELECT
    therapeutic_area_search_term,
    phase_clean,
    COUNT(*) AS total_trials,
    ROUND(100.0 * SUM(terminated_flag) / COUNT(*), 1) AS termination_rate_pct
FROM trials
WHERE phase_clean != 'Not Applicable'
GROUP BY therapeutic_area_search_term, phase_clean
ORDER BY
    therapeutic_area_search_term,
    CASE phase_clean
        WHEN 'Early Phase 1' THEN 0
        WHEN 'Phase 1' THEN 1
        WHEN 'Phase 2' THEN 2
        WHEN 'Phase 3' THEN 3
        WHEN 'Phase 4' THEN 4
    END;


-- Q3: Average trial duration by therapeutic area and phase
-- (excludes 'Not Applicable' phase trials, same as Q2, since those are mostly
-- non-drug interventional studies that don't follow a Phase 1-4 progression)
SELECT
    therapeutic_area_search_term,
    phase_clean,
    ROUND(AVG(duration_months), 1) AS avg_duration_months,
    COUNT(*) AS n_trials
FROM trials
WHERE duration_months IS NOT NULL AND phase_clean != 'Not Applicable'
GROUP BY therapeutic_area_search_term, phase_clean
ORDER BY therapeutic_area_search_term, phase_clean;


-- Q4: Top reasons why clinical trials stop early
-- why_stopped is free text typed by trial sponsors, so the same underlying
-- reason gets worded many different ways ("low enrollment", "insufficient
-- accrual", "slow patient recruitment" are all the same cause). A raw
-- GROUP BY on the exact text fragments into dozens of near-unique rows and
-- hides the real pattern - this version buckets common phrasing into
-- categories using keyword matching instead.
SELECT
    CASE
        WHEN why_stopped LIKE '%enroll%' OR why_stopped LIKE '%accrual%' OR why_stopped LIKE '%recruit%'
            THEN 'Low enrollment/recruitment'
        WHEN why_stopped LIKE '%covid%' OR why_stopped LIKE '%pandemic%'
            THEN 'COVID-19/pandemic-related'
        WHEN why_stopped LIKE '%safety%' OR why_stopped LIKE '%adverse%' OR why_stopped LIKE '%toxicity%'
            THEN 'Safety concern'
        WHEN why_stopped LIKE '%efficacy%' OR why_stopped LIKE '%futility%'
            THEN 'Lack of efficacy'
        WHEN why_stopped LIKE '%fund%' OR why_stopped LIKE '%financ%'
            THEN 'Funding issue'
        WHEN why_stopped LIKE '%business%' OR why_stopped LIKE '%sponsor decision%' OR why_stopped LIKE '%strategic%'
            THEN 'Business/sponsor decision'
        ELSE 'Other/unspecified'
    END AS stop_reason_category,
    COUNT(*) AS n_trials
FROM trials
WHERE terminated_flag = 1 AND why_stopped IS NOT NULL
GROUP BY stop_reason_category
ORDER BY n_trials DESC;


-- Q5: Termination rate by sponsor type (industry vs. academic/NIH vs. other)
-- Useful cut for a "who runs riskier trials" narrative
SELECT
    lead_sponsor_class,
    COUNT(*) AS total_trials,
    ROUND(100.0 * SUM(terminated_flag) / COUNT(*), 1) AS termination_rate_pct
FROM trials
GROUP BY lead_sponsor_class
ORDER BY termination_rate_pct DESC;


-- Q6: Enrollment size vs termination (do small trials fail more often?)
SELECT
    CASE
        WHEN enrollment_count < 50 THEN '<50'
        WHEN enrollment_count < 200 THEN '50-199'
        WHEN enrollment_count < 500 THEN '200-499'
        ELSE '500+'
    END AS enrollment_bucket,
    COUNT(*) AS total_trials,
    ROUND(100.0 * SUM(terminated_flag) / COUNT(*), 1) AS termination_rate_pct
FROM trials
WHERE enrollment_count IS NOT NULL
GROUP BY enrollment_bucket
ORDER BY
    CASE enrollment_bucket
        WHEN '<50' THEN 0
        WHEN '50-199' THEN 1
        WHEN '200-499' THEN 2
        ELSE 3
    END;


-- Q7: Trials started per year, by therapeutic area (trend line for dashboard)
SELECT
    therapeutic_area_search_term,
    strftime('%Y', start_date_parsed) AS start_year,
    COUNT(*) AS trials_started
FROM trials
WHERE start_date_parsed IS NOT NULL
GROUP BY therapeutic_area_search_term, start_year
ORDER BY start_year, therapeutic_area_search_term;
