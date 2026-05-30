"""
QA-only fake dataset generator.

This file is used to create sample CSV and JSON output without connecting to Reddit.
It helps developers check the dataset format, summary screen, and downstream analysis.

Run from project root:
    PYTHONPATH=src python3 -m backend.fake_data_generator
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from core.settings import PROJECT_ROOT


CSV_OUTPUT_FILE = PROJECT_ROOT / "data" / "rmit_reddit_cs_dataset.csv"
JSON_OUTPUT_FILE = PROJECT_ROOT / "data" / "rmit_reddit_cs_dataset.json"


FIELDNAMES = [
    "row_id",
    "type",
    "subreddit",
    "post_id",
    "comment_id",
    "parent_id",
    "title",
    "body",
    "created_utc",
    "score",
    "num_comments",
    "permalink",
    "matched_query",
    "matched_terms",
    "matched_categories",
    "author_hash",
]


def now_iso():
    """
    Returns a UTC timestamp in the same style as the real extractor output.
    """

    return datetime.now(timezone.utc).isoformat()


def build_fake_rows():
    """
    Builds fake Reddit-like rows that match the real dataset structure.

    These rows are intentionally realistic enough for QA, but they are not real
    Reddit data and should never be used for final research analysis.
    """

    return [
        {
            "row_id": 1,
            "type": "post",
            "subreddit": "rmit",
            "post_id": "fake001",
            "comment_id": "",
            "parent_id": "",
            "title": "How hard is COSC2804?",
            "body": "I am thinking of taking COSC2804 next semester. Is the workload manageable?",
            "created_utc": "2026-04-12T08:30:00+00:00",
            "score": 14,
            "num_comments": 4,
            "permalink": "https://www.reddit.com/r/rmit/comments/fake001/how_hard_is_cosc2804/",
            "matched_query": "COSC2804 workload",
            "matched_terms": "COSC2804 | workload | hard",
            "matched_categories": "course_codes | workload_difficulty",
            "author_hash": "fakea91f2c44",
        },
        {
            "row_id": 2,
            "type": "comment",
            "subreddit": "rmit",
            "post_id": "fake001",
            "comment_id": "fakec001",
            "parent_id": "t3_fake001",
            "title": "How hard is COSC2804?",
            "body": "The assignments take time, but it is okay if you keep up every week.",
            "created_utc": "2026-04-12T09:05:00+00:00",
            "score": 8,
            "num_comments": "",
            "permalink": "https://www.reddit.com/r/rmit/comments/fake001/comment/fakec001/",
            "matched_query": "COSC2804 workload",
            "matched_terms": "assignments | time | week",
            "matched_categories": "assessment_feedback | workload_difficulty",
            "author_hash": "fakeb82e0f33",
        },
        {
            "row_id": 3,
            "type": "comment",
            "subreddit": "rmit",
            "post_id": "fake001",
            "comment_id": "fakec002",
            "parent_id": "t3_fake001",
            "title": "How hard is COSC2804?",
            "body": "The LC-3 and Minecraft part was confusing at first, but useful after practice.",
            "created_utc": "2026-04-12T10:20:00+00:00",
            "score": 5,
            "num_comments": "",
            "permalink": "https://www.reddit.com/r/rmit/comments/fake001/comment/fakec002/",
            "matched_query": "COSC2804 workload",
            "matched_terms": "LC-3 | confusing | practice",
            "matched_categories": "learning_experience | course_experience",
            "author_hash": "fakec41d92aa",
        },
        {
            "row_id": 4,
            "type": "post",
            "subreddit": "rmit",
            "post_id": "fake002",
            "comment_id": "",
            "parent_id": "",
            "title": "MATH2411 experience?",
            "body": "Can anyone share their experience with MATH2411? I am worried about proofs.",
            "created_utc": "2026-04-18T04:10:00+00:00",
            "score": 9,
            "num_comments": 3,
            "permalink": "https://www.reddit.com/r/rmit/comments/fake002/math2411_experience/",
            "matched_query": "MATH2411 experience",
            "matched_terms": "MATH2411 | experience | proofs",
            "matched_categories": "course_codes | learning_experience",
            "author_hash": "faked37ab901",
        },
        {
            "row_id": 5,
            "type": "comment",
            "subreddit": "rmit",
            "post_id": "fake002",
            "comment_id": "fakec003",
            "parent_id": "t3_fake002",
            "title": "MATH2411 experience?",
            "body": "The content is not impossible, but you need to practise direct proofs regularly.",
            "created_utc": "2026-04-18T05:00:00+00:00",
            "score": 6,
            "num_comments": "",
            "permalink": "https://www.reddit.com/r/rmit/comments/fake002/comment/fakec003/",
            "matched_query": "MATH2411 experience",
            "matched_terms": "direct proofs | practise | content",
            "matched_categories": "learning_experience | teaching_learning",
            "author_hash": "fakeef39c002",
        },
        {
            "row_id": 6,
            "type": "post",
            "subreddit": "rmit",
            "post_id": "fake003",
            "comment_id": "",
            "parent_id": "",
            "title": "Is the teaching quality good for first year CS?",
            "body": "I want to know if the lectures and tutorials are helpful for beginner students.",
            "created_utc": "2026-05-02T12:40:00+00:00",
            "score": 21,
            "num_comments": 6,
            "permalink": "https://www.reddit.com/r/rmit/comments/fake003/teaching_quality_first_year_cs/",
            "matched_query": "teaching quality computer science",
            "matched_terms": "teaching | lectures | tutorials | beginner",
            "matched_categories": "teaching_quality | student_support",
            "author_hash": "fakeff19ab88",
        },
    ]


def save_fake_dataset():
    """
    Saves fake rows to the same CSV and JSON files used by the real extractor.
    """

    rows = build_fake_rows()

    CSV_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with CSV_OUTPUT_FILE.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    with JSON_OUTPUT_FILE.open("w", encoding="utf-8") as json_file:
        json.dump(rows, json_file, indent=2, ensure_ascii=False)

    print()
    print("Fake QA dataset created successfully.")
    print(f"CSV file:  {CSV_OUTPUT_FILE}")
    print(f"JSON file: {JSON_OUTPUT_FILE}")
    print()
    print("You can now run option 5: Show dataset summary.")
    print()

    return rows


def main():
    save_fake_dataset()


if __name__ == "__main__":
    main()