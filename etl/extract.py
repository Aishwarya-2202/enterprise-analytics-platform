"""
extract.py

The "E" in ETL. This module is responsible ONLY for reading raw data
files into pandas DataFrames. It performs no cleaning, no validation,
no transformation — that all happens later, in transform.py.

Keeping extraction "dumb" preserves an unmodified view of what the
source data actually looked like, which is essential for debugging
and for re-running the pipeline if cleaning logic changes later.
"""

import pandas as pd


def extract_csv(file_path: str) -> pd.DataFrame:
    """
    Read a CSV file into a DataFrame exactly as-is.

    Parameters
    ----------
    file_path : str
        Path to the CSV file to read.

    Returns
    -------
    pd.DataFrame
        The raw contents of the file, completely unmodified.
    """
    df = pd.read_csv(file_path)
    return df


def extract_excel(file_path: str, sheet_name: str = 0) -> pd.DataFrame:
    """
    Read an Excel file into a DataFrame exactly as-is.

    Parameters
    ----------
    file_path : str
        Path to the .xlsx file to read.
    sheet_name : str or int, default 0
        Which sheet to read. Defaults to the first sheet (index 0).

    Returns
    -------
    pd.DataFrame
        The raw contents of the sheet, completely unmodified.
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
    return df


def inspect(df: pd.DataFrame, label: str = "DataFrame") -> None:
    """
    Print a quick, standard inspection summary of a DataFrame.
    Run this on every new dataset before doing anything else to it.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to inspect.
    label : str
        A name to print alongside the summary, for readability when
        inspecting multiple DataFrames in the same run.
    """
    print(f"\n--- Inspecting: {label} ---")
    print(f"Shape (rows, columns): {df.shape}")
    print("\nColumn data types:")
    print(df.dtypes)
    print("\nFirst 5 rows:")
    print(df.head())
    print("\nMissing values per column:")
    print(df.isna().sum())


if __name__ == "__main__":
    # This block only runs when extract.py is executed directly
    # (e.g. `python etl/extract.py`), not when it's imported by
    # another file such as pipeline.py in a later lesson.
    raw_sales = extract_csv("data/raw/sample_sales.csv")
    inspect(raw_sales, label="raw_sales")