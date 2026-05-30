import re


CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SAFE_SIMPLE_TEXT_PATTERN = re.compile(r"^[A-Za-z0-9 _\-\.]+$")


def contains_control_characters(value):
    """
    Returns True when the value contains terminal/control characters.

    These characters can make CLI output messy, corrupt JSON files, or hide
    unexpected behaviour in terminal input.
    """

    if value is None:
        return False

    return CONTROL_CHARACTER_PATTERN.search(str(value)) is not None


def validate_terminal_text(value, field_name, allow_empty=False, max_length=500):
    """
    Validates text entered through the CLI.

    The function intentionally allows normal punctuation because Reddit user
    agents, credentials, course names, and search keywords may contain symbols.
    It blocks control characters and very long values.
    """

    if value is None:
        value = ""

    cleaned_value = str(value).strip()

    if not cleaned_value and not allow_empty:
        raise ValueError(f"{field_name} cannot be empty.")

    if len(cleaned_value) > max_length:
        raise ValueError(f"{field_name} is too long. Maximum length is {max_length} characters.")

    if contains_control_characters(cleaned_value):
        raise ValueError(
            f"{field_name} contains unsupported control characters. "
            "Please remove hidden/newline/terminal characters and try again."
        )

    return cleaned_value


def validate_simple_label(value, field_name, allow_empty=False, max_length=80):
    """
    Validates simple labels used for menu-like values.

    This is stricter than validate_terminal_text and is useful for values that
    should only contain letters, numbers, spaces, dots, hyphens, or underscores.
    """

    cleaned_value = validate_terminal_text(
        value=value,
        field_name=field_name,
        allow_empty=allow_empty,
        max_length=max_length,
    )

    if cleaned_value and SAFE_SIMPLE_TEXT_PATTERN.fullmatch(cleaned_value) is None:
        raise ValueError(
            f"{field_name} contains unsupported characters. "
            "Use letters, numbers, spaces, dots, hyphens, or underscores."
        )

    return cleaned_value


def is_yes(value):
    """
    Returns True only for an explicit yes response.
    """

    return str(value).strip().lower() == "y"
