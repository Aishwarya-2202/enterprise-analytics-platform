"""
pipeline.py

The single entry point for the ETL process. Runs, in order:
    1. Extract  - read the raw source file
    2. Transform - clean, validate, engineer features
    3. Load     - resolve dimensions, refresh fact_sales, insert

This is the one file a scheduler (cron, Windows Task Scheduler, or a
future orchestration tool) would actually call to run the pipeline.
"""

import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from extract import extract_csv
from transform import transform
from load import load, get_engine
from config.config import DATABASE_URL


# --- Logging setup -----------------------------------------------------
# INFO level shows normal progress; WARNING/ERROR would show problems.
# In a real deployment this would also write to a log FILE, not just
# the console -- flagged as a follow-up exercise below.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def reset_fact_sales(engine) -> None:
    """
    Full-refresh strategy: wipe fact_sales clean before reloading.

    We deliberately do NOT truncate the dimension tables -- those
    should keep accumulating (new customers, products, stores, dates)
    across runs. Only the fact table, which is fully re-derived from
    the source file every run, gets reset.

    RESTART IDENTITY resets the sale_id auto-increment counter back
    to 1, so IDs stay clean and low instead of climbing forever across
    repeated test runs.
    """
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_sales RESTART IDENTITY"))
    logger.info("fact_sales truncated (full refresh strategy).")


def run_pipeline(source_file: str) -> None:
    """
    Run the full ETL pipeline against a single source file.
    Raises the original exception after logging it, so the failure is
    never silently swallowed -- a caller (or scheduler) can detect and
    react to a failed run.
    """
    logger.info(f"Pipeline started for source file: {source_file}")

    try:
        raw_df = extract_csv(source_file)
        logger.info(f"Extracted {len(raw_df)} raw row(s).")

        clean_df = transform(raw_df)
        logger.info(f"Transformed to {len(clean_df)} clean row(s).")

        engine = get_engine()
        reset_fact_sales(engine)

        load(clean_df)
        logger.info("Pipeline completed successfully.")

    except Exception:
        logger.exception("Pipeline failed. See traceback above.")
        raise


if __name__ == "__main__":
    run_pipeline("data/raw/sample_sales.csv")