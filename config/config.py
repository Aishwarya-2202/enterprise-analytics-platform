
import os
from dotenv import load_dotenv

# Load variables from the .env file in the project root into the
# process environment. This must run before we try to read anything
# with os.getenv() below.
load_dotenv()


def _get_required_env(var_name: str) -> str:
    """
    Read an environment variable and raise a clear error if it's missing,
    instead of silently returning None and failing somewhere else later.
    """
    value = os.getenv(var_name)
    if value is None or value == "":
        raise ValueError(
            f"Missing required environment variable: '{var_name}'. "
            f"Did you create a .env file from .env.example?"
        )
    return value


# Individual settings, read once when this module is first imported.
DB_HOST = _get_required_env("DB_HOST")
DB_PORT = _get_required_env("DB_PORT")
DB_NAME = _get_required_env("DB_NAME")
DB_USER = _get_required_env("DB_USER")
DB_PASSWORD = _get_required_env("DB_PASSWORD")

# A dictionary form, useful when a function wants all settings at once.
DB_CONFIG = {
    "host": DB_HOST,
    "port": DB_PORT,
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
}

# The full SQLAlchemy connection URL, built once here so every module
# that needs to connect to PostgreSQL uses the exact same string.
# Format: postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)