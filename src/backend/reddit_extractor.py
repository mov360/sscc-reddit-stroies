import logging
import sys
import time

try:
    import pandas as pd
except ModuleNotFoundError:
    print("Required dependency missing: pandas")
    print("Run: pip install -r requirements.txt")
    raise SystemExit(1)

try:
    import praw
    from prawcore import exceptions as praw_exceptions
except ModuleNotFoundError:
    print("Required dependency missing: praw")
    print("Run: pip install -r requirements.txt")
    raise SystemExit(1)

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    print("Required dependency missing: tqdm")
    print("Run: pip install -r requirements.txt")
    raise SystemExit(1)

from core.runtime_config import (
    ACTIVE_COLLECTION_MODE,
    COLLECTION_MODE,
    COMMENT_REPLACE_MORE_LIMIT,
    CSV_OUTPUT_FILE,
    END_DATE_LOCAL,
    JSON_OUTPUT_FILE,
    LOG_FILE,
    LOGS_DIR,
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
from core.keywords import (
    find_keyword_matches,
    get_reddit_search_queries,
)
from core.dataset_rows import (
    build_comment_row,
    build_post_row,
    clean_text,
    is_useful_body,
    safe_attr,
)


Forbidden = praw_exceptions.Forbidden
NotFound = praw_exceptions.NotFound
RequestException = praw_exceptions.RequestException
ResponseException = praw_exceptions.ResponseException
ServerError = praw_exceptions.ServerError
TooManyRequests = praw_exceptions.TooManyRequests
OAuthException = getattr(praw_exceptions, "OAuthException", ResponseException)
InvalidToken = getattr(praw_exceptions, "InvalidToken", ResponseException)
PrawcoreException = getattr(praw_exceptions, "PrawcoreException", Exception)


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

def setup_logging():
    """
    Sends extraction logs to both terminal and logs/reddit_extraction.log.
    """

    LOGS_DIR.mkdir(exist_ok=True)

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


def verify_reddit_access(subreddit):
    """
    Performs a small Reddit request before the full extraction starts.

    This catches wrong credentials, no internet connection, and private/missing
    subreddit errors early with a clear message.
    """

    try:
        _ = subreddit.id
        return True

    except (OAuthException, InvalidToken, ResponseException) as error:
        raise RuntimeError(
            "Could not authenticate with Reddit. Check your client ID, client secret, and user agent."
        ) from error

    except Forbidden as error:
        raise RuntimeError(
            f"Could not access r/{SUBREDDIT_NAME}. The subreddit may be private or restricted."
        ) from error

    except NotFound as error:
        raise RuntimeError(
            f"Could not find r/{SUBREDDIT_NAME}. Check the subreddit name in config/settings.json."
        ) from error

    except TooManyRequests as error:
        raise RuntimeError(
            "Reddit rate-limited the initial request. Try again later."
        ) from error

    except (RequestException, ServerError) as error:
        raise RuntimeError(
            "Network or Reddit server error while connecting. Check your internet connection and try again."
        ) from error


# ------------------------------------------------------------
# Extraction helpers
# ------------------------------------------------------------

def get_submission_text(submission):
    """
    Combines post title and body for keyword matching.
    """

    title = clean_text(safe_attr(submission, "title", ""))
    body = clean_text(safe_attr(submission, "selftext", ""))

    return f"{title} {body}".strip()


def should_keep_submission(submission):
    """
    Keeps posts inside the selected CES date range.
    """

    return is_within_date_range(safe_attr(submission, "created_utc", None))


def should_keep_comment(comment):
    """
    Keeps useful comments inside the selected CES date range.
    """

    if not is_within_date_range(safe_attr(comment, "created_utc", None)):
        return False

    if not is_useful_body(safe_attr(comment, "body", "")):
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
        try:
            if should_keep_comment(comment):
                comment_text = clean_text(safe_attr(comment, "body", ""))
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

        except Exception as error:
            logging.warning("Skipping one broken comment: %s", error)
            logging.debug("Broken comment details", exc_info=True)

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

def save_dataset(rows, partial=False):
    """
    Saves extracted rows to CSV and JSON.

    Returns True when saving succeeds. Returns False when the output file could
    not be written.
    """

    if not rows:
        logging.warning("No rows collected. Nothing was saved.")
        return True

    try:
        dataframe = pd.DataFrame(rows)

        dataframe.drop_duplicates(
            subset=["type", "post_id", "comment_id"],
            inplace=True,
        )

        dataframe.sort_values(
            by=["created_utc", "type", "post_id", "comment_id"],
            inplace=True,
        )

        CSV_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        JSON_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        dataframe.to_csv(CSV_OUTPUT_FILE, index=False, encoding="utf-8")
        dataframe.to_json(
            JSON_OUTPUT_FILE,
            orient="records",
            indent=2,
            force_ascii=False,
        )

    except PermissionError:
        logging.error(
            "Could not write output file. Close the CSV/JSON file if it is open in Excel and try again."
        )
        return False

    except OSError as error:
        logging.error("Could not write output file: %s", error)
        logging.error("Check disk space and project folder permissions.")
        return False

    post_count = len(dataframe[dataframe["type"] == "post"])
    comment_count = len(dataframe[dataframe["type"] == "comment"])

    if partial:
        logging.info("Partial dataset saved successfully.")
    else:
        logging.info("Dataset saved successfully.")

    logging.info("Saved CSV: %s", CSV_OUTPUT_FILE)
    logging.info("Saved JSON: %s", JSON_OUTPUT_FILE)
    logging.info("Total saved rows: %s", len(dataframe))
    logging.info("Saved posts: %s", post_count)
    logging.info("Saved comments: %s", comment_count)

    return True


# ------------------------------------------------------------
# Main workflow
# ------------------------------------------------------------

def run_extraction():
    """
    Runs the full Reddit extraction workflow.
    """

    validate_config()

    logging.info("Starting Reddit extraction")
    logging.info("Target subreddit: r/%s", SUBREDDIT_NAME)
    logging.info("Date range: %s to %s", START_DATE_LOCAL.date(), END_DATE_LOCAL.date())
    logging.info("Collection mode: %s", COLLECTION_MODE)
    logging.info("Collection label: %s", ACTIVE_COLLECTION_MODE["label"])
    logging.info("Search sort modes: %s", SEARCH_SORT_MODES)

    reddit = create_reddit_client()
    subreddit = reddit.subreddit(SUBREDDIT_NAME)
    verify_reddit_access(subreddit)

    search_queries = get_reddit_search_queries()

    logging.info("Total search queries: %s", len(search_queries))

    all_rows = []
    seen_post_ids = set()
    row_id = 1

    total_searches = len(search_queries) * len(SEARCH_SORT_MODES)

    try:
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
                            submission_id = clean_text(safe_attr(submission, "id", ""))

                            if not submission_id:
                                logging.warning("Skipping one Reddit post because it has no post ID.")
                                continue

                            if submission_id in seen_post_ids:
                                continue

                            if not should_keep_submission(submission):
                                continue

                            seen_post_ids.add(submission_id)

                            logging.info(
                                "Matched post: %s | %s",
                                submission_id,
                                clean_text(safe_attr(submission, "title", "")),
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
                                    submission_id,
                                    error,
                                )

                            except TooManyRequests as error:
                                logging.warning("Rate limited while reading post %s: %s", submission_id, error)
                                logging.warning("Sleeping for 60 seconds before continuing.")
                                time.sleep(60)

                            except KeyboardInterrupt:
                                raise

                            except Exception as error:
                                logging.warning(
                                    "Skipping post %s after unexpected extraction error: %s",
                                    submission_id,
                                    error,
                                )
                                logging.debug("Post extraction details", exc_info=True)

                    except TooManyRequests as error:
                        logging.warning("Reddit rate limit reached: %s", error)
                        logging.warning("Sleeping for 60 seconds before continuing.")
                        time.sleep(60)

                    except (RequestException, ServerError) as error:
                        logging.warning("Network or Reddit server error: %s", error)
                        logging.warning("Sleeping for 10 seconds before continuing.")
                        time.sleep(10)

                    except (Forbidden, NotFound) as error:
                        logging.error("Could not access subreddit search results: %s", error)
                        logging.info("Saving data collected so far before stopping.")
                        save_dataset(all_rows, partial=True)
                        return 1

                    except (OAuthException, InvalidToken, ResponseException) as error:
                        logging.error("Reddit authentication failed: %s", error)
                        logging.error("Check your Reddit credentials in .env.")
                        save_dataset(all_rows, partial=True)
                        return 1

                    except KeyboardInterrupt:
                        raise

                    except Exception as error:
                        logging.warning(
                            "Unexpected error during search query=%s sort=%s: %s",
                            search_query,
                            sort_mode,
                            error,
                        )
                        logging.debug("Search error details", exc_info=True)

                    progress_bar.update(1)

    except KeyboardInterrupt:
        logging.warning("Extraction stopped by user with Ctrl+C.")
        logging.info("Saving partial results before exiting.")
        save_dataset(all_rows, partial=True)
        return 130

    logging.info("Extraction complete before final save.")
    logging.info("Unique matched posts collected: %s", len(seen_post_ids))
    logging.info("Raw rows collected before deduplication: %s", len(all_rows))

    if not all_rows:
        logging.info("Extraction completed, but no matching posts or comments were found.")
        logging.info("Try expanding the time range or keyword list.")
        return 0

    if save_dataset(all_rows, partial=False):
        return 0

    return 1


def main():
    """
    Entry point for the extraction command.
    """

    try:
        setup_logging()
        return run_extraction()

    except KeyboardInterrupt:
        print()
        print("Extraction stopped by user.")
        return 130

    except ModuleNotFoundError as error:
        print()
        print(f"Missing dependency: {error}")
        print("Run: pip install -r requirements.txt")
        return 1

    except RuntimeError as error:
        logging.error("%s", error)
        return 1

    except ValueError as error:
        logging.error("Configuration error: %s", error)
        return 1

    except FileNotFoundError as error:
        logging.error("Missing file: %s", error)
        return 1

    except Exception as error:
        logging.error("Unexpected extraction error: %s", error)
        logging.debug("Unexpected extraction details", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
