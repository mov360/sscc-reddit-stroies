import json
from datetime import datetime
from pathlib import Path


# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
KEYWORDS_FILE = CONFIG_DIR / "keywords.json"


# ------------------------------------------------------------
# Default user settings
# ------------------------------------------------------------
# These are fallback values only. The menu stores the user's chosen
# settings in config/settings.json.

DEFAULT_SETTINGS = {
    "subreddit": "rmit",
    "start_date": "2025-03-01",
    "end_date": "2026-05-29",
    "collection_mode": "deep_ces",
    "output_csv": "data/rmit_reddit_cs_dataset.csv",
    "output_json": "data/rmit_reddit_cs_dataset.json",
}


# ------------------------------------------------------------
# CES collection modes
# ------------------------------------------------------------
# The user sees simple qualitative choices.
# The extractor uses the technical values behind those choices.

COLLECTION_MODES = {
    "test_run": {
        "menu_number": "1",
        "label": "Test run",
        "description": "Use this only to check that the app works.",
        "benefit": "Fastest option.",
        "downside": "Not suitable for final CES analysis.",
        "search_sort_modes": ["relevance"],
        "post_limit_per_query": 10,
        "comment_replace_more_limit": 0,
        "sleep_seconds_between_posts": 0.1,
    },

    "standard_ces": {
        "menu_number": "2",
        "label": "Standard CES collection",
        "description": "Use this when you need a reasonable CES dataset with less waiting time.",
        "benefit": "Good balance between useful evidence and runtime.",
        "downside": "May miss some deeper comment threads or less-visible discussions.",
        "search_sort_modes": ["relevance", "new"],
        "post_limit_per_query": 50,
        "comment_replace_more_limit": 0,
        "sleep_seconds_between_posts": 0.2,
    },

    "deep_ces": {
        "menu_number": "3",
        "label": "Deep CES collection",
        "description": "Recommended default for CES analysis.",
        "benefit": "Collects broader evidence and more complete comment threads.",
        "downside": "Takes longer and creates a larger dataset.",
        "search_sort_modes": ["relevance", "new", "comments", "top"],
        "post_limit_per_query": None,
        "comment_replace_more_limit": 32,
        "sleep_seconds_between_posts": 0.2,
    },

    "maximum_ces": {
        "menu_number": "4",
        "label": "Maximum CES collection",
        "description": "Use this when completeness matters more than time.",
        "benefit": "Attempts to collect as much relevant Reddit discussion as possible.",
        "downside": "Slowest option, larger files, and higher chance of Reddit rate limits.",
        "search_sort_modes": ["relevance", "new", "comments", "top", "hot"],
        "post_limit_per_query": None,
        "comment_replace_more_limit": None,
        "sleep_seconds_between_posts": 0.5,
    },
}


COLLECTION_MODE_MENU_ORDER = [
    "test_run",
    "standard_ces",
    "deep_ces",
    "maximum_ces",
]


def load_settings():
    """
    Loads config/settings.json.

    If the settings file does not exist, it is created using DEFAULT_SETTINGS.
    Missing keys are filled from DEFAULT_SETTINGS so older settings files
    remain compatible after new options are added.
    """

    CONFIG_DIR.mkdir(exist_ok=True)

    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
        user_settings = json.load(file)

    settings = DEFAULT_SETTINGS.copy()
    settings.update(user_settings)

    return settings


def save_settings(settings):
    """
    Saves the current app settings to config/settings.json.
    """

    CONFIG_DIR.mkdir(exist_ok=True)

    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=2)


def validate_date_text(date_text, field_name):
    """
    Validates a YYYY-MM-DD date string.

    Returns the parsed datetime object if valid.
    Raises ValueError if invalid.
    """

    try:
        return datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from error


def update_time_range(start_date, end_date):
    """
    Updates the saved extraction date range.

    start_date is mandatory.
    end_date is optional. If end_date is blank, extraction will use today's
    date at runtime.
    """

    start_date = start_date.strip()

    if not start_date:
        raise ValueError("Start date is mandatory.")

    start_datetime = validate_date_text(start_date, "Start date")

    cleaned_end_date = ""

    if end_date is not None and end_date.strip():
        cleaned_end_date = end_date.strip()
        end_datetime = validate_date_text(cleaned_end_date, "End date")

        if end_datetime < start_datetime:
            raise ValueError("End date must not be before start date.")

    settings = load_settings()
    settings["start_date"] = start_date
    settings["end_date"] = cleaned_end_date

    save_settings(settings)


def update_collection_mode(mode_key):
    """
    Updates the saved CES collection mode.
    """

    if mode_key not in COLLECTION_MODES:
        allowed_modes = ", ".join(COLLECTION_MODES.keys())
        raise ValueError(f"Invalid collection mode. Allowed values: {allowed_modes}")

    settings = load_settings()
    settings["collection_mode"] = mode_key

    save_settings(settings)


def get_collection_mode_by_menu_number(menu_number):
    """
    Converts a menu number into an internal collection mode key.
    """

    for mode_key in COLLECTION_MODE_MENU_ORDER:
        mode = COLLECTION_MODES[mode_key]

        if mode["menu_number"] == menu_number:
            return mode_key

    return None


def get_active_collection_mode(settings=None):
    """
    Returns the active collection mode dictionary.
    """

    if settings is None:
        settings = load_settings()

    mode_key = settings.get("collection_mode", DEFAULT_SETTINGS["collection_mode"])

    if mode_key not in COLLECTION_MODES:
        raise ValueError(f"Invalid collection_mode in settings.json: {mode_key}")

    return COLLECTION_MODES[mode_key]


def format_optional_end_date(end_date):
    """
    Returns display text for an optional end date.
    """

    if end_date is None or not str(end_date).strip():
        return "Today when extraction runs"

    return end_date