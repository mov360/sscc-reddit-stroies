from collections import Counter

import pandas as pd

from .config import (
    CSV_OUTPUT_FILE,
    JSON_OUTPUT_FILE,
)
from .settings_manager import (
    format_optional_end_date,
    get_active_collection_mode,
    load_settings,
)


def _split_pipe_values(value):
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

    dataframe = pd.read_csv(CSV_OUTPUT_FILE)

    total_rows = len(dataframe)
    total_posts = len(dataframe[dataframe["type"] == "post"])
    total_comments = len(dataframe[dataframe["type"] == "comment"])

    print(f"CSV file: {CSV_OUTPUT_FILE}")
    print(f"JSON file: {JSON_OUTPUT_FILE}")
    print()
    print(f"Total rows: {total_rows}")
    print(f"Posts: {total_posts}")
    print(f"Comments: {total_comments}")

    if "created_utc" in dataframe.columns and total_rows > 0:
        print(f"Oldest row date: {dataframe['created_utc'].min()}")
        print(f"Newest row date: {dataframe['created_utc'].max()}")

    print()

    if "matched_categories" in dataframe.columns:
        category_counter = Counter()

        for value in dataframe["matched_categories"]:
            for category in _split_pipe_values(value):
                category_counter[category] += 1

        print("Top matched categories:")

        if category_counter:
            for category, count in category_counter.most_common(10):
                print(f"- {category}: {count}")
        else:
            print("- No matched categories found.")

    print("-" * 60)