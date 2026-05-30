from collections import Counter

from core.runtime_config import (
    CSV_OUTPUT_FILE,
    JSON_OUTPUT_FILE,
)
from core.settings import (
    format_optional_end_date,
    get_active_collection_mode,
    load_settings,
)


def import_pandas_for_summary():
    """
    Imports pandas with a user-friendly error message if it is missing.
    """

    try:
        import pandas as pd
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "pandas is not installed. Run: pip install -r requirements.txt"
        ) from error

    return pd


def _split_pipe_values(value, pd):
    """
    Splits pipe-separated CSV values such as:
    assessment_feedback | workload_difficulty
    """

    if pd.isna(value) or not str(value).strip():
        return []

    return [item.strip() for item in str(value).split("|") if item.strip()]


def show_dataset_summary():
    """
    Prints a concise summary of the latest extracted dataset.
    """

    pd = import_pandas_for_summary()
    settings = load_settings()
    active_mode = get_active_collection_mode(settings)

    print()
    print("Dataset Summary")
    print("-" * 60)

    print(f"Subreddit: r/{settings['subreddit']}")
    print(f"Start date: {settings['start_date']}")
    print(f"End date: {format_optional_end_date(settings.get('end_date'))}")
    print(f"CES collection mode: {active_mode['label']}")
    print()

    if not CSV_OUTPUT_FILE.exists():
        print("No CSV dataset found yet.")
        print(f"Expected file: {CSV_OUTPUT_FILE}")
        print("Run extraction first.")
        return

    try:
        dataframe = pd.read_csv(CSV_OUTPUT_FILE)
    except PermissionError as error:
        raise PermissionError(
            "Could not read the CSV dataset. Close the file if it is open in Excel and try again."
        ) from error
    except Exception as error:
        raise ValueError(
            "Could not read the CSV dataset. The file may be corrupted or not a valid CSV."
        ) from error

    required_columns = {"type", "created_utc", "matched_categories"}
    missing_columns = required_columns.difference(dataframe.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"The CSV dataset is missing expected column(s): {missing_text}. "
            "Run extraction again to regenerate the dataset."
        )

    total_rows = len(dataframe)
    total_posts = len(dataframe[dataframe["type"] == "post"])
    total_comments = len(dataframe[dataframe["type"] == "comment"])

    print(f"CSV file: {CSV_OUTPUT_FILE}")
    print(f"JSON file: {JSON_OUTPUT_FILE}")
    print()
    print(f"Total rows: {total_rows}")
    print(f"Posts: {total_posts}")
    print(f"Comments: {total_comments}")

    if total_rows > 0:
        print(f"Oldest row date: {dataframe['created_utc'].min()}")
        print(f"Newest row date: {dataframe['created_utc'].max()}")

    print()

    category_counter = Counter()

    for value in dataframe["matched_categories"]:
        for category in _split_pipe_values(value, pd):
            category_counter[category] += 1

    print("Top matched categories:")

    if category_counter:
        for category, count in category_counter.most_common(10):
            print(f"- {category}: {count}")
    else:
        print("- No matched categories found.")

    print("-" * 60)
