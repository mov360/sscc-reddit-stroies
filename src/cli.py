import argparse
import getpass
import subprocess
import sys

from .keywords import get_all_keywords, load_keyword_categories
from .settings_manager import (
    COLLECTION_MODE_MENU_ORDER,
    COLLECTION_MODES,
    PROJECT_ROOT,
    format_optional_end_date,
    get_active_collection_mode,
    get_collection_mode_by_menu_number,
    load_settings,
    save_settings,
    update_collection_mode,
    update_time_range,
)


# ------------------------------------------------------------
# Shared display helpers
# ------------------------------------------------------------

def pause():
    """
    Waits for the user before returning to a menu.
    """

    input("\nPress Enter to continue...")


def print_main_header():
    """
    Prints the app title.
    """

    print()
    print("RMIT Reddit Course Experience Extractor")
    print("=" * 45)


def print_current_extraction_settings():
    """
    Prints the current subreddit, date range, and CES collection mode.
    """

    settings = load_settings()
    active_mode = get_active_collection_mode(settings)

    print()
    print("Current settings:")
    print(f"- Subreddit: r/{settings['subreddit']}")
    print(f"- Start date: {settings['start_date']}")
    print(f"- End date: {format_optional_end_date(settings.get('end_date'))}")
    print(f"- CES collection mode: {active_mode['label']}")


# ------------------------------------------------------------
# Option 1: credentials
# ------------------------------------------------------------

def setup_reddit_credentials():
    """
    Creates or updates the .env file with Reddit API credentials.
    """

    print()
    print("Setup Reddit Credentials")
    print("-" * 45)
    print("You can get these values from your Reddit developer app.")
    print("The credentials will be saved locally in .env.")
    print()

    client_id = input("Reddit client ID: ").strip()
    client_secret = getpass.getpass("Reddit client secret: ").strip()
    user_agent = input(
        "Reddit user agent "
        "(example: rmit_ces_research_script_by_yourusername): "
    ).strip()

    author_hash_salt = getpass.getpass(
        "Author hash salt "
        "(optional privacy salt; press Enter to use default): "
    ).strip()

    env_lines = [
        f"REDDIT_CLIENT_ID={client_id}",
        f"REDDIT_CLIENT_SECRET={client_secret}",
        f"REDDIT_USER_AGENT={user_agent}",
    ]

    if author_hash_salt:
        env_lines.append(f"AUTHOR_HASH_SALT={author_hash_salt}")

    env_file = PROJECT_ROOT / ".env"

    with open(env_file, "w", encoding="utf-8") as file:
        file.write("\n".join(env_lines))
        file.write("\n")

    print()
    print(f"Credentials saved to: {env_file}")


# ------------------------------------------------------------
# Option 2: validation
# ------------------------------------------------------------

def validate_setup():
    """
    Validates settings, keywords file, output folders, and credentials.
    """

    print()
    print("Validate Setup")
    print("-" * 45)

    try:
        from .config import (
            ACTIVE_COLLECTION_MODE,
            END_DATE_LOCAL,
            KEYWORDS_FILE,
            SETTINGS_FILE,
            START_DATE_LOCAL,
            SUBREDDIT_NAME,
            validate_config,
        )

        validate_config()

        print("Setup looks good.")
        print(f"Settings file: {SETTINGS_FILE}")
        print(f"Keywords file: {KEYWORDS_FILE}")
        print(f"Subreddit: r/{SUBREDDIT_NAME}")
        print(f"Date range: {START_DATE_LOCAL.date()} to {END_DATE_LOCAL.date()}")
        print(f"CES collection mode: {ACTIVE_COLLECTION_MODE['label']}")

    except Exception as error:
        print("Setup validation failed.")
        print(f"Reason: {error}")


# ------------------------------------------------------------
# Option 3: keywords
# ------------------------------------------------------------

def check_keywords():
    """
    Shows keyword category and keyword counts.
    """

    print()
    print("Check Keywords")
    print("-" * 45)

    try:
        categories = load_keyword_categories()
        keywords = get_all_keywords()

        print(f"Total keyword categories: {len(categories)}")
        print(f"Total unique keywords: {len(keywords)}")
        print()

        print("Categories:")

        for category, terms in categories.items():
            print(f"- {category}: {len(terms)} keywords")

    except Exception as error:
        print("Could not read keywords.")
        print(f"Reason: {error}")


# ------------------------------------------------------------
# Option 4.1: time range
# ------------------------------------------------------------

def set_time_range_menu():
    """
    Lets the user update the extraction date range.
    """

    print()
    print("Set Time Range")
    print("-" * 45)
    print("Start Date is mandatory.")
    print("End Date is optional.")
    print()

    start_date = input("Enter start date (YYYY-MM-DD): ").strip()
    end_date = input(
        "Enter end date (YYYY-MM-DD), or press Enter to use today: "
    ).strip()

    try:
        update_time_range(start_date, end_date)
        print()
        print("Time range saved.")

    except Exception as error:
        print()
        print("Could not save time range.")
        print(f"Reason: {error}")


# ------------------------------------------------------------
# Option 4.2: CES collection settings
# ------------------------------------------------------------

def ces_collection_settings_menu():
    """
    Lets the user choose the CES data collection depth.
    """

    print()
    print("CES Data Collection Settings")
    print("-" * 45)
    print("Choose how deeply the app should collect Reddit posts and comments")
    print("for CES evidence.")
    print()

    for mode_key in COLLECTION_MODE_MENU_ORDER:
        mode = COLLECTION_MODES[mode_key]

        print(f"{mode['menu_number']}. {mode['label']}")
        print(f"   {mode['description']}")
        print(f"   Benefit: {mode['benefit']}")
        print(f"   Downside: {mode['downside']}")
        print()

    selected_option = input("Select option [1-4]: ").strip()
    selected_mode = get_collection_mode_by_menu_number(selected_option)

    if selected_mode is None:
        print()
        print("Invalid option. Please choose between 1 and 4.")
        return

    try:
        update_collection_mode(selected_mode)
        print()
        print(f"CES collection mode saved: {COLLECTION_MODES[selected_mode]['label']}")

    except Exception as error:
        print()
        print("Could not save collection mode.")
        print(f"Reason: {error}")


# ------------------------------------------------------------
# Option 4.3: extraction
# ------------------------------------------------------------

def start_extraction_from_menu():
    """
    Starts extraction as a separate Python process.

    Running extraction in a separate process ensures the latest settings.json
    values are loaded fresh before extraction begins.
    """

    print_current_extraction_settings()
    print()
    confirm = input("Start extraction with these settings? [y/N]: ").strip().lower()

    if confirm != "y":
        print("Extraction cancelled.")
        return

    print()
    print("Starting extraction...")
    print("This may take some time depending on the selected CES collection mode.")
    print()

    command = [sys.executable, "-m", "src.extract_reddit"]
    result = subprocess.run(command, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print()
        print("Extraction finished.")
    else:
        print()
        print("Extraction ended with an error. Check the terminal output and logs.")


def run_extraction_menu():
    """
    Submenu for extraction-related settings and execution.
    """

    while True:
        print()
        print("Run Extraction")
        print("=" * 45)
        print_current_extraction_settings()
        print()
        print("4.1 Set time range")
        print("4.2 CES data collection settings")
        print("4.3 Start extraction")
        print("4.4 Back to main menu")
        print()

        choice = input("Select option: ").strip()

        if choice == "4.1":
            set_time_range_menu()
            pause()

        elif choice == "4.2":
            ces_collection_settings_menu()
            pause()

        elif choice == "4.3":
            start_extraction_from_menu()
            pause()

        elif choice == "4.4":
            return

        else:
            print("Invalid option. Please choose 4.1, 4.2, 4.3, or 4.4.")
            pause()


# ------------------------------------------------------------
# Option 5: summary
# ------------------------------------------------------------

def show_summary():
    """
    Shows summary statistics for the saved dataset.
    """

    try:
        from .summary import show_dataset_summary

        show_dataset_summary()

    except Exception as error:
        print()
        print("Could not show dataset summary.")
        print(f"Reason: {error}")


# ------------------------------------------------------------
# Interactive menu
# ------------------------------------------------------------

def main_menu():
    """
    Runs the non-technical interactive menu.
    """

    while True:
        print_main_header()
        print()
        print("1. Setup Reddit credentials")
        print("2. Validate setup")
        print("3. Check keywords")
        print("4. Run extraction")
        print("5. Show dataset summary")
        print("6. Exit")
        print()

        choice = input("Select option: ").strip()

        if choice == "1":
            setup_reddit_credentials()
            pause()

        elif choice == "2":
            validate_setup()
            pause()

        elif choice == "3":
            check_keywords()
            pause()

        elif choice == "4":
            run_extraction_menu()

        elif choice == "5":
            show_summary()
            pause()

        elif choice == "6":
            print("Goodbye.")
            return

        else:
            print("Invalid option. Please choose between 1 and 6.")
            pause()


# ------------------------------------------------------------
# Command-line mode
# ------------------------------------------------------------

def cli_setup_command(_args):
    setup_reddit_credentials()


def cli_validate_command(_args):
    validate_setup()


def cli_keywords_command(_args):
    check_keywords()


def cli_extract_command(_args):
    from .extract_reddit import main as extract_main

    extract_main()


def cli_summary_command(_args):
    show_summary()


def cli_menu_command(_args):
    main_menu()


def build_parser():
    """
    Builds the developer-facing command parser.
    """

    parser = argparse.ArgumentParser(
        description="RMIT Reddit Course Experience Extractor"
    )

    subparsers = parser.add_subparsers(dest="command")

    setup_parser = subparsers.add_parser("setup")
    setup_parser.set_defaults(func=cli_setup_command)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.set_defaults(func=cli_validate_command)

    keywords_parser = subparsers.add_parser("keywords")
    keywords_parser.set_defaults(func=cli_keywords_command)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.set_defaults(func=cli_extract_command)

    summary_parser = subparsers.add_parser("summary")
    summary_parser.set_defaults(func=cli_summary_command)

    menu_parser = subparsers.add_parser("menu")
    menu_parser.set_defaults(func=cli_menu_command)

    return parser


def main():
    """
    Entry point for python -m src.cli.
    """

    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        main_menu()
        return

    args.func(args)


if __name__ == "__main__":
    main()