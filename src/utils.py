import hashlib
from datetime import datetime, timezone

from .config import AUTHOR_HASH_SALT, IGNORED_BODIES


def clean_text(text):
    """
    Normalises Reddit text for CSV/JSON storage.
    """

    if text is None:
        return ""

    cleaned = str(text)
    cleaned = cleaned.replace("\r", " ")
    cleaned = cleaned.replace("\n", " ")
    cleaned = " ".join(cleaned.split())

    return cleaned.strip()


def is_useful_body(text):
    """
    Returns False for empty, deleted, or removed Reddit content.
    """

    cleaned = clean_text(text)

    return cleaned not in IGNORED_BODIES


def hash_author(author):
    """
    Hashes a Reddit username before storage.

    This keeps repeated-author analysis possible without storing the actual
    Reddit username in the dataset.
    """

    if author is None:
        return "deleted_or_unknown"

    raw_author = str(author)
    salted_author = raw_author + AUTHOR_HASH_SALT

    return hashlib.sha256(salted_author.encode("utf-8")).hexdigest()[:12]


def utc_timestamp_to_iso(created_utc):
    """
    Converts Reddit's UTC timestamp into ISO format.
    """

    return datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()


def join_list(values):
    """
    Converts a list into a pipe-separated string for CSV storage.
    """

    if values is None:
        return ""

    return " | ".join(values)


def safe_int(value, default=0):
    """
    Converts a value to int. Returns default if conversion fails.
    """

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_post_row(
    row_id,
    submission,
    matched_query,
    matched_terms,
    matched_categories,
):
    """
    Builds one output row for a Reddit post.
    """

    return {
        "row_id": row_id,
        "type": "post",
        "subreddit": str(submission.subreddit),
        "post_id": submission.id,
        "comment_id": "",
        "parent_id": "",
        "title": clean_text(submission.title),
        "body": clean_text(submission.selftext),
        "created_utc": utc_timestamp_to_iso(submission.created_utc),
        "score": safe_int(submission.score),
        "num_comments": safe_int(submission.num_comments),
        "permalink": "https://www.reddit.com" + submission.permalink,
        "matched_query": matched_query,
        "matched_terms": join_list(matched_terms),
        "matched_categories": join_list(matched_categories),
        "author_hash": hash_author(submission.author),
    }


def build_comment_row(
    row_id,
    submission,
    comment,
    matched_query,
    matched_terms,
    matched_categories,
):
    """
    Builds one output row for a Reddit comment.
    """

    return {
        "row_id": row_id,
        "type": "comment",
        "subreddit": str(submission.subreddit),
        "post_id": submission.id,
        "comment_id": comment.id,
        "parent_id": comment.parent_id,
        "title": clean_text(submission.title),
        "body": clean_text(comment.body),
        "created_utc": utc_timestamp_to_iso(comment.created_utc),
        "score": safe_int(comment.score),
        "num_comments": "",
        "permalink": "https://www.reddit.com" + comment.permalink,
        "matched_query": matched_query,
        "matched_terms": join_list(matched_terms),
        "matched_categories": join_list(matched_categories),
        "author_hash": hash_author(comment.author),
    }