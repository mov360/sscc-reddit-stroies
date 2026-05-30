import json
import re

from .input_validation import contains_control_characters
from .settings import KEYWORDS_FILE


def load_keyword_categories():
    """
    Loads keyword categories from config/keywords.json.

    The keyword file is user-editable, so this function validates the structure
    and raises clear errors instead of letting JSON/Python errors leak to users.
    """

    if not KEYWORDS_FILE.exists():
        raise FileNotFoundError(
            "Missing config/keywords.json. Restore the keywords file before checking keywords."
        )

    try:
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as file:
            keyword_categories = json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"keywords.json could not be read because the JSON is invalid: {error}"
        ) from error

    if not isinstance(keyword_categories, dict):
        raise ValueError("keywords.json must contain a JSON object of category names and keyword lists.")

    for category, terms in keyword_categories.items():
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Every keyword category name must be a non-empty string.")

        if contains_control_characters(category):
            raise ValueError(f"Keyword category contains unsupported control characters: {category!r}")

        if not isinstance(terms, list):
            raise ValueError(f"Keyword category '{category}' must contain a list of terms.")

        for term in terms:
            if not isinstance(term, str) or not term.strip():
                raise ValueError(f"Keyword category '{category}' contains an empty or non-text term.")

            if contains_control_characters(term):
                raise ValueError(
                    f"Keyword term in category '{category}' contains unsupported control characters."
                )

    return keyword_categories


def get_all_keywords():
    """
    Returns all unique keywords from every keyword category.
    """

    keyword_categories = load_keyword_categories()
    all_keywords = []

    for category_terms in keyword_categories.values():
        for term in category_terms:
            all_keywords.append(term.strip())

    return sorted(set(all_keywords), key=str.lower)


def format_reddit_search_query(term):
    """
    Formats a keyword for Reddit search.

    Multi-word phrases are wrapped in quotes.
    Single-word terms and course codes are kept as-is.
    """

    cleaned_term = str(term).strip()

    if " " in cleaned_term:
        return f'"{cleaned_term}"'

    return cleaned_term


def get_reddit_search_queries():
    """
    Returns all keywords formatted as Reddit search queries.
    """

    search_queries = []

    for keyword in get_all_keywords():
        search_queries.append(format_reddit_search_query(keyword))

    return search_queries


def _build_keyword_pattern(term):
    """
    Builds a safe regex pattern for keyword matching.

    Short terms such as CS, AI, HD, DI, CR, PA, and WIL need stricter
    boundaries so they do not match inside unrelated words.
    """

    escaped_term = re.escape(term)

    if len(term) <= 4 and term.replace("+", "").replace("&", "").isalnum():
        return rf"(?<![A-Za-z0-9]){escaped_term}(?![A-Za-z0-9])"

    return escaped_term


def find_keyword_matches(text):
    """
    Finds keyword terms and keyword categories inside a text value.

    Returns:
        matched_terms: list[str]
        matched_categories: list[str]
    """

    if text is None:
        text = ""

    keyword_categories = load_keyword_categories()

    matched_terms = []
    matched_categories = []

    for category, terms in keyword_categories.items():
        for term in terms:
            pattern = _build_keyword_pattern(term.strip())

            if re.search(pattern, str(text), flags=re.IGNORECASE):
                matched_terms.append(term.strip())

                if category not in matched_categories:
                    matched_categories.append(category)

    matched_terms = sorted(set(matched_terms), key=str.lower)
    matched_categories = sorted(set(matched_categories), key=str.lower)

    return matched_terms, matched_categories


def has_keyword_match(text):
    """
    Returns True if the supplied text contains at least one configured keyword.
    """

    matched_terms, _ = find_keyword_matches(text)

    return len(matched_terms) > 0
