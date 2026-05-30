import logging
import time

import pandas as pd
import praw
from prawcore.exceptions import (
    Forbidden,
    NotFound,
    RequestException,
    ResponseException,
    ServerError,
    TooManyRequests,
)
from tqdm import tqdm

from .config import (
    ACTIVE_COLLECTION_MODE,
    COLLECTION_MODE,
    COMMENT_REPLACE_MORE_LIMIT,
    CSV_OUTPUT_FILE,
    END_DATE_LOCAL,
    JSON_OUTPUT_FILE,
    LOG_FILE,
    POST_LIMIT_PER_QUERY,
    SEARCH_SORT_MODES,
    SLEEP_SECONDS_BETWEEN_POSTS,
    START_DATE_LOCAL,
    SUBREDDIT_NAME,
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    validate_config,
    is_within_date_range,
)
from .keywords import (
    find_keyword_matches,
    get_reddit_search_queries,
)
from .utils import (
    build_comment_row,
    build_post_row,
    clean_text,
    is_useful_body,
)


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

def setup_logging():
    """
    Sends extraction logs to both terminal and logs/reddit_extraction.log.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


# ------------------------------------------------------------
# Reddit connection
# ------------------------------------------------------------

def create_reddit_client():
    """
    Creates a read-only Reddit API client.
    """

    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


# ------------------------------------------------------------
# Extraction helpers
# ------------------------------------------------------------

def get_submission_text(submission):
    """
    Combines post title and body for keyword matching.
    """

    title = clean_text(submission.title)
    body = clean_text(submission.selftext)

    return f"{title} {body}".strip()


def should_keep_submission(submission):
    """
    Keeps posts inside the selected CES date range.
    """

    return is_within_date_range(submission.created_utc)


def should_keep_comment(comment):
    """
    Keeps useful comments inside the selected CES date range.
    """

    if not is_within_date_range(comment.created_utc):
        return False

    if not is_useful_body(comment.body):
        return False

    return True


def fetch_comments_for_submission(submission):
    """
    Loads comments for one matched Reddit post.

    The depth depends on the selected CES collection mode.
    """

    submission.comments.replace_more(limit=COMMENT_REPLACE_MORE_LIMIT)

    return submission.comments.list()


def extract_submission_thread(submission, matched_query, starting_row_id):
    """
    Extracts one matched post and its useful comments.

    The post is saved because it matched the keyword search.
    Comments are saved if they are useful and inside the selected date range.
    """

    rows = []
    row_id = starting_row_id

    submission_text = get_submission_text(submission)
    post_matched_terms, post_matched_categories = find_keyword_matches(submission_text)

    rows.append(
        build_post_row(
            row_id=row_id,
            submission=submission,
            matched_query=matched_query,
            matched_terms=post_matched_terms,
            matched_categories=post_matched_categories,
        )
    )
    row_id += 1

    comments = fetch_comments_for_submission(submission)

    for comment in comments:
        if should_keep_comment(comment):
            comment_text = clean_text(comment.body)
            comment_matched_terms, comment_matched_categories = find_keyword_matches(
                comment_text
            )

            rows.append(
                build_comment_row(
                    row_id=row_id,
                    submission=submission,
                    comment=comment,
                    matched_query=matched_query,
                    matched_terms=comment_matched_terms,
                    matched_categories=comment_matched_categories,
                )
            )
            row_id += 1

    return rows, row_id


def search_subreddit(subreddit, search_query, sort_mode):
    """
    Runs one keyword search against the configured subreddit.
    """

    return subreddit.search(
        query=search_query,
        sort=sort_mode,
        time_filter="all",
        limit=POST_LIMIT_PER_QUERY,
    )


# ------------------------------------------------------------
# Save helpers
# ------------------------------------------------------------

def save_dataset(rows):
    """
    Saves extracted rows to CSV and JSON.
    """

    if not rows:
        logging.warning("No rows collected. Nothing was saved.")
        return

    dataframe = pd.DataFrame(rows)

    dataframe.drop_duplicates(
        subset=["type", "post_id", "comment_id"],
        inplace=True,
    )

    dataframe.sort_values(
        by=["created_utc", "type", "post_id", "comment_id"],
        inplace=True,
    )

    CSV_OUTPUT_FILE.parent.mkdir(exist_ok=True)
    JSON_OUTPUT_FILE.parent.mkdir(exist_ok=True)

    dataframe.to_csv(CSV_OUTPUT_FILE, index=False, encoding="utf-8")
    dataframe.to_json(
        JSON_OUTPUT_FILE,
        orient="records",
        indent=2,
        force_ascii=False,
    )

    post_count = len(dataframe[dataframe["type"] == "post"])
    comment_count = len(dataframe[dataframe["type"] == "comment"])

    logging.info("Saved CSV: %s", CSV_OUTPUT_FILE)
    logging.info("Saved JSON: %s", JSON_OUTPUT_FILE)
    logging.info("Total saved rows: %s", len(dataframe))
    logging.info("Saved posts: %s", post_count)
    logging.info("Saved comments: %s", comment_count)


# ------------------------------------------------------------
# Main workflow
# ------------------------------------------------------------

def main():
    """
    Runs the full Reddit extraction workflow.
    """

    validate_config()
    setup_logging()

    logging.info("Starting Reddit extraction")
    logging.info("Target subreddit: r/%s", SUBREDDIT_NAME)
    logging.info("Date range: %s to %s", START_DATE_LOCAL.date(), END_DATE_LOCAL.date())
    logging.info("Collection mode: %s", COLLECTION_MODE)
    logging.info("Collection label: %s", ACTIVE_COLLECTION_MODE["label"])
    logging.info("Search sort modes: %s", SEARCH_SORT_MODES)

    reddit = create_reddit_client()
    subreddit = reddit.subreddit(SUBREDDIT_NAME)

    search_queries = get_reddit_search_queries()

    logging.info("Total search queries: %s", len(search_queries))

    all_rows = []
    seen_post_ids = set()
    row_id = 1

    total_searches = len(search_queries) * len(SEARCH_SORT_MODES)

    with tqdm(total=total_searches, desc="Searching Reddit") as progress_bar:
        for search_query in search_queries:
            for sort_mode in SEARCH_SORT_MODES:
                logging.info(
                    "Searching r/%s | query=%s | sort=%s",
                    SUBREDDIT_NAME,
                    search_query,
                    sort_mode,
                )

                try:
                    submissions = search_subreddit(
                        subreddit=subreddit,
                        search_query=search_query,
                        sort_mode=sort_mode,
                    )

                    for submission in submissions:
                        if submission.id in seen_post_ids:
                            continue

                        if not should_keep_submission(submission):
                            continue

                        seen_post_ids.add(submission.id)

                        logging.info(
                            "Matched post: %s | %s",
                            submission.id,
                            clean_text(submission.title),
                        )

                        try:
                            thread_rows, row_id = extract_submission_thread(
                                submission=submission,
                                matched_query=search_query,
                                starting_row_id=row_id,
                            )

                            all_rows.extend(thread_rows)

                            time.sleep(SLEEP_SECONDS_BETWEEN_POSTS)

                        except (Forbidden, NotFound) as error:
                            logging.warning(
                                "Could not access comments for post %s: %s",
                                submission.id,
                                error,
                            )

                        except Exception as error:
                            logging.exception(
                                "Unexpected error while extracting post %s: %s",
                                submission.id,
                                error,
                            )

                except TooManyRequests as error:
                    logging.warning("Rate limited by Reddit: %s", error)
                    logging.warning("Sleeping for 60 seconds.")
                    time.sleep(60)

                except (RequestException, ResponseException, ServerError) as error:
                    logging.warning("Reddit/API error: %s", error)
                    logging.warning("Sleeping for 10 seconds.")
                    time.sleep(10)

                except Exception as error:
                    logging.exception(
                        "Unexpected error during search query=%s sort=%s: %s",
                        search_query,
                        sort_mode,
                        error,
                    )

                progress_bar.update(1)

    logging.info("Extraction complete before final save.")
    logging.info("Unique matched posts collected: %s", len(seen_post_ids))
    logging.info("Raw rows collected before deduplication: %s", len(all_rows))

    save_dataset(all_rows)


if __name__ == "__main__":
    main()