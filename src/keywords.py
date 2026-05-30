import json
import re

from .config import KEYWORDS_FILE


def load_keyword_categories():
    """
    Loads keyword categories from config/keywords.json.
    """

    with open(KEYWORDS_FILE, "r", encoding="utf-8") as file:
        keyword_categories = json.load(file)

    return keyword_categories


def get_all_keywords():
    """
    Returns all unique keywords from every keyword category.
    """

    keyword_categories = load_keyword_categories()
    all_keywords = []

    for category_terms in keyword_categories.values():
        for term in category_terms:
            all_keywords.append(term)

    return sorted(set(all_keywords), key=str.lower)


def format_reddit_search_query(term):
    """
    Formats a keyword for Reddit search.

    Multi-word phrases are wrapped in quotes.
    Single-word terms and course codes are kept as-is.
    """

    cleaned_term = term.strip()

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
            pattern = _build_keyword_pattern(term)

            if re.search(pattern, text, flags=re.IGNORECASE):
                matched_terms.append(term)

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