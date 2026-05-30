import hashlib
from datetime import datetime, timezone

from .runtime_config import AUTHOR_HASH_SALT, IGNORED_BODIES


def safe_attr(obj, attribute_name, default=""):
    """
    Safely reads attributes from Reddit objects.

    Some Reddit objects can be missing fields, deleted, partially loaded, or can
    raise API-backed errors when an attribute is accessed. Returning a default
    lets the extractor skip or save the rest of the usable thread.
    """

    try:
        value = getattr(obj, attribute_name, default)
    except Exception:
        value = default

    if value is None:
        return default

    return value


def clean_text(text):
    """
    Normalises Reddit text for CSV/JSON storage.
    """

    if text is None:
        return ""

    cleaned = str(text)
    cleaned = cleaned.encode("utf-8", errors="replace").decode("utf-8")
    cleaned = cleaned.replace("\r", " ")
    cleaned = cleaned.replace("\n", " ")
    cleaned = " ".join(cleaned.split())

    return cleaned.strip()


def is_useful_body(text):
    """
    Returns False for empty, deleted, or removed Reddit content.
    """

    cleaned = clean_text(text)

    return cleaned.lower() not in IGNORED_BODIES


def hash_author(author):
    """
    Hashes a Reddit username before storage.

    This keeps repeated-author analysis possible without storing the actual
    Reddit username in the dataset.
    """

    if author is None:
        return "deleted_or_unknown"

    raw_author = clean_text(author)

    if not raw_author:
        return "deleted_or_unknown"

    salted_author = raw_author + AUTHOR_HASH_SALT

    return hashlib.sha256(salted_author.encode("utf-8", errors="replace")).hexdigest()[:12]


def utc_timestamp_to_iso(created_utc):
    """
    Converts Reddit's UTC timestamp into ISO format.
    """

    try:
        return datetime.fromtimestamp(float(created_utc), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def join_list(values):
    """
    Converts a list into a pipe-separated string for CSV storage.
    """

    if values is None:
        return ""

    cleaned_values = []

    for value in values:
        cleaned_value = clean_text(value)

        if cleaned_value:
            cleaned_values.append(cleaned_value)

    return " | ".join(cleaned_values)


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

    permalink = clean_text(safe_attr(submission, "permalink", ""))

    if permalink and not permalink.startswith("http"):
        permalink = "https://www.reddit.com" + permalink

    return {
        "row_id": row_id,
        "type": "post",
        "subreddit": clean_text(safe_attr(submission, "subreddit", "")),
        "post_id": clean_text(safe_attr(submission, "id", "")),
        "comment_id": "",
        "parent_id": "",
        "title": clean_text(safe_attr(submission, "title", "")),
        "body": clean_text(safe_attr(submission, "selftext", "")),
        "created_utc": utc_timestamp_to_iso(safe_attr(submission, "created_utc", None)),
        "score": safe_int(safe_attr(submission, "score", 0)),
        "num_comments": safe_int(safe_attr(submission, "num_comments", 0)),
        "permalink": permalink,
        "matched_query": clean_text(matched_query),
        "matched_terms": join_list(matched_terms),
        "matched_categories": join_list(matched_categories),
        "author_hash": hash_author(safe_attr(submission, "author", None)),
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

    permalink = clean_text(safe_attr(comment, "permalink", ""))

    if permalink and not permalink.startswith("http"):
        permalink = "https://www.reddit.com" + permalink

    return {
        "row_id": row_id,
        "type": "comment",
        "subreddit": clean_text(safe_attr(submission, "subreddit", "")),
        "post_id": clean_text(safe_attr(submission, "id", "")),
        "comment_id": clean_text(safe_attr(comment, "id", "")),
        "parent_id": clean_text(safe_attr(comment, "parent_id", "")),
        "title": clean_text(safe_attr(submission, "title", "")),
        "body": clean_text(safe_attr(comment, "body", "")),
        "created_utc": utc_timestamp_to_iso(safe_attr(comment, "created_utc", None)),
        "score": safe_int(safe_attr(comment, "score", 0)),
        "num_comments": "",
        "permalink": permalink,
        "matched_query": clean_text(matched_query),
        "matched_terms": join_list(matched_terms),
        "matched_categories": join_list(matched_categories),
        "author_hash": hash_author(safe_attr(comment, "author", None)),
    }
