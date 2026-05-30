"""
Simulated QA tests for the RMIT Reddit Course Experience Extractor.

These tests do not connect to Reddit. They use fake Reddit-like objects and
temporary files so the extractor can be checked safely during development.

Run from the project root:
    PYTHONPATH=src python -m unittest -v tests/test_simulated_qa.py
"""

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from core import keywords as keywords_module
from core import settings as settings_module
from core.dataset_rows import (
    build_comment_row,
    build_post_row,
    clean_text,
    hash_author,
    is_useful_body,
    safe_attr,
    utc_timestamp_to_iso,
)
from core.input_validation import (
    contains_control_characters,
    validate_simple_label,
    validate_terminal_text,
)
from core.settings import (
    DEFAULT_SETTINGS,
    validate_date_text,
    validate_relative_output_path,
    validate_subreddit_name,
)


EXTRACTOR_DEPENDENCIES_INSTALLED = all(
    importlib.util.find_spec(package_name) is not None
    for package_name in ["praw", "pandas", "tqdm"]
)

if EXTRACTOR_DEPENDENCIES_INSTALLED:
    from backend import reddit_extractor
else:
    reddit_extractor = None


# ------------------------------------------------------------
# Fake Reddit objects
# ------------------------------------------------------------

class FakeCommentForest:
    def __init__(self, comments):
        self._comments = comments
        self.replace_more_called = False
        self.replace_more_limit = None

    def replace_more(self, limit=None):
        self.replace_more_called = True
        self.replace_more_limit = limit

    def list(self):
        return self._comments


class FakeSubmission:
    def __init__(
        self,
        submission_id="abc123",
        title="Thoughts on COSC2804?",
        selftext="The assignment workload feels hard but useful.",
        created_utc=None,
        comments=None,
        author="student_one",
    ):
        self.id = submission_id
        self.title = title
        self.selftext = selftext
        self.created_utc = created_utc or utc_timestamp("2026-04-12T08:30:00+00:00")
        self.score = 12
        self.num_comments = 3
        self.subreddit = "rmit"
        self.permalink = f"/r/rmit/comments/{submission_id}/sample_post/"
        self.author = author
        self.comments = FakeCommentForest(comments or [])


class FakeComment:
    def __init__(
        self,
        comment_id="cmt001",
        body="The lab and assignment were confusing at first.",
        created_utc=None,
        score=5,
        author="student_two",
    ):
        self.id = comment_id
        self.parent_id = "t3_abc123"
        self.body = body
        self.created_utc = created_utc or utc_timestamp("2026-04-12T09:05:00+00:00")
        self.score = score
        self.permalink = f"/r/rmit/comments/abc123/comment/{comment_id}/"
        self.author = author


class BrokenRedditObject:
    @property
    def title(self):
        raise RuntimeError("simulated broken Reddit field")


class FakeRedditClient:
    def subreddit(self, _name):
        return FakeSubreddit()


class FakeSubreddit:
    id = "fake_subreddit_id"


# ------------------------------------------------------------
# Test helpers
# ------------------------------------------------------------

def utc_timestamp(iso_text):
    return datetime.fromisoformat(iso_text).timestamp()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

class TextCleaningAndSafetyTests(unittest.TestCase):
    def test_clean_text_normalises_newlines_tabs_and_unicode(self):
        raw_text = "  COSC2804\nassignment\twas   hard 😀  "
        self.assertEqual(clean_text(raw_text), "COSC2804 assignment was hard 😀")

    def test_deleted_removed_and_empty_bodies_are_not_useful(self):
        self.assertFalse(is_useful_body(""))
        self.assertFalse(is_useful_body("[deleted]"))
        self.assertFalse(is_useful_body("[removed]"))
        self.assertTrue(is_useful_body("This assignment was useful."))

    def test_hash_author_is_stable_and_hides_raw_username(self):
        first_hash = hash_author("real_reddit_username")
        second_hash = hash_author("real_reddit_username")

        self.assertEqual(first_hash, second_hash)
        self.assertNotIn("real_reddit_username", first_hash)
        self.assertEqual(len(first_hash), 12)
        self.assertEqual(hash_author(None), "deleted_or_unknown")

    def test_safe_attr_handles_broken_reddit_object_fields(self):
        self.assertEqual(safe_attr(BrokenRedditObject(), "title", "fallback"), "fallback")

    def test_utc_timestamp_to_iso_handles_valid_and_invalid_values(self):
        iso_text = utc_timestamp_to_iso(utc_timestamp("2026-04-12T08:30:00+00:00"))
        self.assertTrue(iso_text.startswith("2026-04-12T08:30:00"))
        self.assertEqual(utc_timestamp_to_iso("not-a-number"), "")


class InputValidationTests(unittest.TestCase):
    def test_control_characters_are_detected(self):
        self.assertTrue(contains_control_characters("hello\x00world"))
        self.assertFalse(contains_control_characters("normal text 123"))

    def test_terminal_text_rejects_empty_and_control_characters(self):
        with self.assertRaises(ValueError):
            validate_terminal_text("", "Test field")

        with self.assertRaises(ValueError):
            validate_terminal_text("bad\x00text", "Test field")

        self.assertEqual(validate_terminal_text("  valid text  ", "Test field"), "valid text")

    def test_simple_label_rejects_unsafe_symbols(self):
        self.assertEqual(validate_simple_label("RMIT CS_2026", "Label"), "RMIT CS_2026")

        with self.assertRaises(ValueError):
            validate_simple_label("bad/path", "Label")


class SettingsValidationTests(unittest.TestCase):
    def test_date_validation_accepts_only_yyyy_mm_dd(self):
        parsed_date = validate_date_text("2026-05-29", "End date")
        self.assertEqual(parsed_date.year, 2026)

        with self.assertRaises(ValueError):
            validate_date_text("29/05/2026", "End date")

    def test_subreddit_validation_accepts_clean_names_only(self):
        self.assertEqual(validate_subreddit_name("r/rmit"), "rmit")
        self.assertEqual(validate_subreddit_name("RMIT_Study"), "RMIT_Study")

        with self.assertRaises(ValueError):
            validate_subreddit_name("bad/subreddit/name")

    def test_output_path_validation_blocks_absolute_and_parent_paths(self):
        self.assertEqual(
            validate_relative_output_path("data/output.csv", "output_csv", ".csv"),
            "data/output.csv",
        )

        with self.assertRaises(ValueError):
            validate_relative_output_path("../outside.csv", "output_csv", ".csv")

        with self.assertRaises(ValueError):
            validate_relative_output_path("data/output.txt", "output_csv", ".csv")

    def test_corrupted_settings_file_is_backed_up_and_defaults_are_restored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_dir = Path(temp_dir) / "config"
            temp_settings_file = temp_config_dir / "settings.json"
            temp_config_dir.mkdir(parents=True, exist_ok=True)
            temp_settings_file.write_text('{ "subreddit": ', encoding="utf-8")

            with mock.patch.object(settings_module, "CONFIG_DIR", temp_config_dir), \
                 mock.patch.object(settings_module, "SETTINGS_FILE", temp_settings_file), \
                 mock.patch("builtins.print"):
                loaded_settings = settings_module.load_settings()

            self.assertEqual(loaded_settings["subreddit"], DEFAULT_SETTINGS["subreddit"])
            self.assertTrue(temp_settings_file.exists())
            backups = list(temp_config_dir.glob("settings.invalid_*.json"))
            self.assertEqual(len(backups), 1)


class KeywordMatchingTests(unittest.TestCase):
    def test_keyword_matching_uses_simulated_keywords_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            keyword_file = Path(temp_dir) / "keywords.json"
            write_json(
                keyword_file,
                {
                    "course_codes": ["COSC2804", "MATH2411"],
                    "student_experience": ["assignment", "hard", "confusing"],
                },
            )

            with mock.patch.object(keywords_module, "KEYWORDS_FILE", keyword_file):
                terms, categories = keywords_module.find_keyword_matches(
                    "COSC2804 assignment was hard but useful."
                )

        self.assertEqual(terms, ["assignment", "COSC2804", "hard"])
        self.assertEqual(categories, ["course_codes", "student_experience"])

    def test_short_keywords_do_not_match_inside_unrelated_words(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            keyword_file = Path(temp_dir) / "keywords.json"
            write_json(keyword_file, {"short_terms": ["AI", "CS"]})

            with mock.patch.object(keywords_module, "KEYWORDS_FILE", keyword_file):
                terms_inside_word, _ = keywords_module.find_keyword_matches("The main topic is useful.")
                terms_standalone, _ = keywords_module.find_keyword_matches("AI and CS are popular.")

        self.assertNotIn("AI", terms_inside_word)
        self.assertIn("AI", terms_standalone)
        self.assertIn("CS", terms_standalone)

    def test_invalid_keywords_json_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            keyword_file = Path(temp_dir) / "keywords.json"
            keyword_file.write_text('{ "bad": ', encoding="utf-8")

            with mock.patch.object(keywords_module, "KEYWORDS_FILE", keyword_file):
                with self.assertRaises(ValueError):
                    keywords_module.load_keyword_categories()


class DatasetRowBuildTests(unittest.TestCase):
    def test_build_post_row_from_fake_submission(self):
        submission = FakeSubmission()

        row = build_post_row(
            row_id=1,
            submission=submission,
            matched_query="COSC2804",
            matched_terms=["COSC2804", "assignment"],
            matched_categories=["first_year_core", "student_experience"],
        )

        self.assertEqual(row["row_id"], 1)
        self.assertEqual(row["type"], "post")
        self.assertEqual(row["post_id"], "abc123")
        self.assertEqual(row["comment_id"], "")
        self.assertTrue(row["permalink"].startswith("https://www.reddit.com/r/rmit/comments/"))
        self.assertEqual(row["matched_terms"], "COSC2804 | assignment")
        self.assertNotEqual(row["author_hash"], "student_one")

    def test_build_comment_row_from_fake_comment(self):
        submission = FakeSubmission()
        comment = FakeComment()

        row = build_comment_row(
            row_id=2,
            submission=submission,
            comment=comment,
            matched_query="COSC2804",
            matched_terms=["assignment", "confusing"],
            matched_categories=["student_experience"],
        )

        self.assertEqual(row["row_id"], 2)
        self.assertEqual(row["type"], "comment")
        self.assertEqual(row["post_id"], "abc123")
        self.assertEqual(row["comment_id"], "cmt001")
        self.assertEqual(row["num_comments"], "")
        self.assertIn("assignment", row["matched_terms"])


@unittest.skipIf(
    reddit_extractor is None,
    "Extractor dependencies are missing. Run: pip install -r requirements.txt",
)
class SimulatedExtractionWorkflowTests(unittest.TestCase):
    def test_extract_submission_thread_filters_deleted_and_old_comments(self):
        useful_comment = FakeComment(
            comment_id="good001",
            body="The COSC2804 assignment was confusing but useful.",
            created_utc=utc_timestamp("2026-04-12T09:05:00+00:00"),
        )
        deleted_comment = FakeComment(
            comment_id="deleted001",
            body="[deleted]",
            created_utc=utc_timestamp("2026-04-12T10:00:00+00:00"),
        )
        old_comment = FakeComment(
            comment_id="old001",
            body="This old comment should be outside the configured date range.",
            created_utc=utc_timestamp("2020-01-01T00:00:00+00:00"),
        )
        submission = FakeSubmission(comments=[useful_comment, deleted_comment, old_comment])

        rows, next_row_id = reddit_extractor.extract_submission_thread(
            submission=submission,
            matched_query="COSC2804",
            starting_row_id=1,
        )

        row_types = [row["type"] for row in rows]
        comment_ids = [row["comment_id"] for row in rows]

        self.assertEqual(row_types, ["post", "comment"])
        self.assertIn("good001", comment_ids)
        self.assertNotIn("deleted001", comment_ids)
        self.assertNotIn("old001", comment_ids)
        self.assertEqual(next_row_id, 3)
        self.assertTrue(submission.comments.replace_more_called)

    def test_save_dataset_writes_csv_and_json_using_temp_files(self):
        submission = FakeSubmission()
        comment = FakeComment()

        rows = [
            build_post_row(1, submission, "COSC2804", ["COSC2804"], ["first_year_core"]),
            build_comment_row(2, submission, comment, "COSC2804", ["assignment"], ["student_experience"]),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_csv = Path(temp_dir) / "qa_dataset.csv"
            temp_json = Path(temp_dir) / "qa_dataset.json"

            with mock.patch.object(reddit_extractor, "CSV_OUTPUT_FILE", temp_csv), \
                 mock.patch.object(reddit_extractor, "JSON_OUTPUT_FILE", temp_json):
                saved = reddit_extractor.save_dataset(rows)

            self.assertTrue(saved)
            self.assertTrue(temp_csv.exists())
            self.assertTrue(temp_json.exists())

            with temp_csv.open("r", encoding="utf-8") as file:
                csv_rows = list(csv.DictReader(file))

            json_rows = json.loads(temp_json.read_text(encoding="utf-8"))

            self.assertEqual(len(csv_rows), 2)
            self.assertEqual(len(json_rows), 2)
            self.assertEqual(csv_rows[0]["type"], "post")
            self.assertEqual(json_rows[1]["type"], "comment")

    def test_run_extraction_returns_success_when_no_results_found(self):
        with mock.patch.object(reddit_extractor, "validate_config", return_value=None), \
             mock.patch.object(reddit_extractor, "create_reddit_client", return_value=FakeRedditClient()), \
             mock.patch.object(reddit_extractor, "verify_reddit_access", return_value=True), \
             mock.patch.object(reddit_extractor, "get_reddit_search_queries", return_value=["COSC2804"]), \
             mock.patch.object(reddit_extractor, "SEARCH_SORT_MODES", ["new"]), \
             mock.patch.object(reddit_extractor, "search_subreddit", return_value=[]), \
             mock.patch.object(reddit_extractor, "save_dataset") as mocked_save:
            result_code = reddit_extractor.run_extraction()

        self.assertEqual(result_code, 0)
        mocked_save.assert_not_called()

    def test_ctrl_c_during_extraction_saves_partial_dataset(self):
        with mock.patch.object(reddit_extractor, "validate_config", return_value=None), \
             mock.patch.object(reddit_extractor, "create_reddit_client", return_value=FakeRedditClient()), \
             mock.patch.object(reddit_extractor, "verify_reddit_access", return_value=True), \
             mock.patch.object(reddit_extractor, "get_reddit_search_queries", return_value=["COSC2804"]), \
             mock.patch.object(reddit_extractor, "SEARCH_SORT_MODES", ["new"]), \
             mock.patch.object(reddit_extractor, "search_subreddit", side_effect=KeyboardInterrupt), \
             mock.patch.object(reddit_extractor, "save_dataset", return_value=True) as mocked_save:
            result_code = reddit_extractor.run_extraction()

        self.assertEqual(result_code, 130)
        mocked_save.assert_called_once()
        self.assertTrue(mocked_save.call_args.kwargs["partial"])


class MenuInputTests(unittest.TestCase):
    def test_read_menu_choice_accepts_valid_option(self):
        from cli import menu

        with mock.patch("builtins.input", return_value="4"):
            self.assertEqual(menu.read_menu_choice("Select option: ", ["1", "2", "3", "4"]), "4")

    def test_read_menu_choice_rejects_invalid_option(self):
        from cli import menu

        with mock.patch("builtins.input", return_value="999"), \
             mock.patch("builtins.print"):
            self.assertIsNone(menu.read_menu_choice("Select option: ", ["1", "2", "3", "4"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)