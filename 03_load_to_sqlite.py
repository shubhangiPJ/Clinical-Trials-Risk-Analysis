"""
Project 1 - Step 4: Load Cleaned Data into SQLite
Reads the cleaned clinical trials CSV and loads it into a SQLite database.
The database can then be queried using SQL in the next step of the project.
"""
import pandas as pd
import sqlite3
import os

def load_to_sqlite():
    """Load the cleaned CSV into a SQLite database."""
    # Read the cleaned dataset
    df = pd.read_csv("clinical_trials_clean.csv")

    # Create (or open) the SQLite database
    conn = sqlite3.connect("clinical_trials.db")

    # Write the dataframe into a table called 'trials'
    # Replace the table if it already exists
    df.to_sql("trials", conn, if_exists="replace", index=False)

    # Create indexes to make SQL queries faster
    cursor = conn.cursor()
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nct_id
        ON trials(nct_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_therapeutic_area
        ON trials(therapeutic_area_search_term)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_phase
        ON trials(phase_clean)
    """)

    # Save the changes
    conn.commit()
    # Close the database connection
    conn.close()

    print("Data successfully loaded into clinical_trials.db")
    print("Table created: trials")
    print("Indexes created successfully.")

def main():
    # Check the cleaned CSV exists before trying to load it
    if not os.path.exists("clinical_trials_clean.csv"):
        print("clinical_trials_clean.csv not found - run 02_data_cleaning.py first.")
        return
    load_to_sqlite()

if __name__ == "__main__":
    main()
