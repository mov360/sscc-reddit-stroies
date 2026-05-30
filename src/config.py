import os
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .settings_manager import (
    PROJECT_ROOT,
    CONFIG_DIR,
    SETTINGS_FILE,
    KEYWORDS_FILE,
    load_settings,
    save_settings,
    COLLECTION_MODES,
    get_active_collection_mode,
)


# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

LOG_FILE = LOGS_DIR / "reddit_extraction.log"


# ------------------------------------------------------------
# User settings
# ------------------------------------------------------------
# config/settings.json is the user-editable state of the app.
# The menu updates that file; the extractor reads from it.

SETTINGS = load_settings()


# ------------------------------------------------------------
# Reddit extraction scope
# ------------------------------------------------------------

SUBREDDIT_NAME = SETTINGS["subreddit"].replace("r/", "").strip("/")
SUBREDDIT_URL = f"https://www.reddit.com/r/{SUBREDDIT_NAME}/"

LOCAL_TIMEZONE = ZoneInfo("Australia/Melbourne")


def parse_local_date(date_text, is_end_date=False):
    """
    Converts YYYY-MM-DD into a timezone-aware Melbourne datetime.

    Start dates begin at 00:00:00.
    End dates finish at 23:59:59 so the selected end date is included.
    """

    parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date()

    if is_end_date:
        selected_time = time(23, 59, 59)
    else:
        selected_time = time(0, 0, 0)

    return datetime.combine(
        parsed_date,
        selected_time,
        tzinfo=LOCAL_TIMEZONE,
    )


def get_effective_end_date_text():
    """
    Returns the saved end date, or today's Melbourne date if the user left
    the end date blank.
    """

    saved_end_date = SETTINGS.get("end_date", "")

    if saved_end_date and saved_end_date.strip():
        return saved_end_date.strip()

    return datetime.now(tz=LOCAL_TIMEZONE).date().isoformat()


START_DATE_LOCAL = parse_local_date(SETTINGS["start_date"], is_end_date=False)
END_DATE_LOCAL = parse_local_date(get_effective_end_date_text(), is_end_date=True)

START_DATE_UTC = START_DATE_LOCAL.astimezone(timezone.utc)
END_DATE_UTC = END_DATE_LOCAL.astimezone(timezone.utc)

START_TIMESTAMP = START_DATE_UTC.timestamp()
END_TIMESTAMP = END_DATE_UTC.timestamp()


# ------------------------------------------------------------
# Output files
# ------------------------------------------------------------

CSV_OUTPUT_FILE = PROJECT_ROOT / SETTINGS["output_csv"]
JSON_OUTPUT_FILE = PROJECT_ROOT / SETTINGS["output_json"]


# ------------------------------------------------------------
# CES collection mode
# ------------------------------------------------------------

COLLECTION_MODE = SETTINGS["collection_mode"]

if COLLECTION_MODE not in COLLECTION_MODES:
    raise ValueError(
        f"Invalid collection_mode in settings.json: {COLLECTION_MODE}. "
        f"Allowed values: {', '.join(COLLECTION_MODES.keys())}"
    )

ACTIVE_COLLECTION_MODE = get_active_collection_mode(SETTINGS)

SEARCH_SORT_MODES = ACTIVE_COLLECTION_MODE["search_sort_modes"]
POST_LIMIT_PER_QUERY = ACTIVE_COLLECTION_MODE["post_limit_per_query"]
COMMENT_REPLACE_MORE_LIMIT = ACTIVE_COLLECTION_MODE["comment_replace_more_limit"]
SLEEP_SECONDS_BETWEEN_POSTS = ACTIVE_COLLECTION_MODE["sleep_seconds_between_posts"]


# ------------------------------------------------------------
# Environment variables
# ------------------------------------------------------------

load_dotenv(PROJECT_ROOT / ".env")


# ------------------------------------------------------------
# Data settings
# ------------------------------------------------------------
# Usernames are not stored directly. A salted hash allows repeated authors
# to be detected without exposing their Reddit usernames.

AUTHOR_HASH_SALT = os.getenv(
    "AUTHOR_HASH_SALT",
    "rmit_ces_default_author_hash_salt_change_for_final_collection",
)

IGNORED_BODIES = {
    "",
    "[deleted]",
    "[removed]",
}


# ------------------------------------------------------------
# Reddit API credentials
# ------------------------------------------------------------

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")


# ------------------------------------------------------------
# Validation helpers
# ------------------------------------------------------------

def validate_config():
    """
    Checks that required folders, files, settings, and Reddit credentials exist.
    """

    CONFIG_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    if not SETTINGS_FILE.exists():
        raise FileNotFoundError(f"Missing settings file: {SETTINGS_FILE}")

    if not KEYWORDS_FILE.exists():
        raise FileNotFoundError(f"Missing keywords file: {KEYWORDS_FILE}")

    if START_DATE_LOCAL > END_DATE_LOCAL:
        raise ValueError("Start date must not be after end date.")

    missing_values = []

    if not REDDIT_CLIENT_ID or REDDIT_CLIENT_ID == "your_client_id_here":
        missing_values.append("REDDIT_CLIENT_ID")

    if not REDDIT_CLIENT_SECRET or REDDIT_CLIENT_SECRET == "your_client_secret_here":
        missing_values.append("REDDIT_CLIENT_SECRET")

    if (
        not REDDIT_USER_AGENT
        or REDDIT_USER_AGENT == "your_user_agent_here"
        or "your_reddit_username" in REDDIT_USER_AGENT
    ):
        missing_values.append("REDDIT_USER_AGENT")

    if missing_values:
        missing_text = ", ".join(missing_values)
        raise ValueError(
            f"Missing or incomplete Reddit API credentials in .env: {missing_text}"
        )


def is_within_date_range(created_utc):
    """
    Returns True when a Reddit UTC timestamp is inside the selected date range.
    """

    return START_TIMESTAMP <= created_utc <= END_TIMESTAMP