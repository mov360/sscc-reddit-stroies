from core.input_validation import validate_terminal_text
from core.keywords import (
    get_all_keywords,
    load_keyword_categories,
)
from core.settings import (
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

    try:
        input("\nPress Enter to continue...")
    except KeyboardInterrupt:
        print()


def print_main_header():
    """
    Prints the app title.
    """

    print()
    print("RMIT Reddit Course Experience Extractor")
    print("=" * 45)


def read_menu_choice(prompt, allowed_options):
    """
    Reads and validates a menu option.
    """

    try:
        choice = input(prompt).strip()
        choice = validate_terminal_text(
            value=choice,
            field_name="Menu option",
            allow_empty=False,
            max_length=10,
        )
    except ValueError:
        print(f"Invalid option. Please choose one of: {', '.join(allowed_options)}.")
        return None

    if choice not in allowed_options:
        print(f"Invalid option. Please choose one of: {', '.join(allowed_options)}.")
        return None

    return choice


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

    try:
        client_id = validate_terminal_text(
            input("Reddit client ID: "),
            field_name="Reddit client ID",
            allow_empty=False,
            max_length=200,
        )

        client_secret = validate_terminal_text(
            getpass.getpass("Reddit client secret: "),
            field_name="Reddit client secret",
            allow_empty=False,
            max_length=300,
        )

        user_agent = validate_terminal_text(
            input("Reddit user agent (example: rmit_ces_research_script_by_yourusername): "),
            field_name="Reddit user agent",
            allow_empty=False,
            max_length=300,
        )

        author_hash_salt = validate_terminal_text(
            getpass.getpass("Author hash salt (optional privacy salt; press Enter to use default): "),
            field_name="Author hash salt",
            allow_empty=True,
            max_length=300,
        )

    except KeyboardInterrupt:
        print()
        print("Credential setup cancelled by user.")
        return

    except ValueError as error:
        print()
        print("Could not save credentials.")
        print(f"Reason: {error}")
        return

    env_lines = [
        f"REDDIT_CLIENT_ID={client_id}",
        f"REDDIT_CLIENT_SECRET={client_secret}",
        f"REDDIT_USER_AGENT={user_agent}",
    ]

    if author_hash_salt:
        env_lines.append(f"AUTHOR_HASH_SALT={author_hash_salt}")

    env_file = PROJECT_ROOT / ".env"

    try:
        with open(env_file, "w", encoding="utf-8") as file:
            file.write("\n".join(env_lines))
            file.write("\n")
    except OSError as error:
        print()
        print("Could not write the .env file.")
        print("Check project folder permissions and try again.")
        print(f"Reason: {error}")
        return

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
        from rmit_ces_reddit_extractor.core.runtime_config import (
            ACTIVE_COLLECTION_MODE,
            END_DATE_LOCAL,
            KEYWORDS_FILE,
            SETTINGS_FILE,
            START_DATE_LOCAL,
            SUBREDDIT_NAME,
            validate_config,
        )

        validate_config()
        load_keyword_categories()

        print("Setup looks good.")
        print(f"Settings file: {SETTINGS_FILE}")
        print(f"Keywords file: {KEYWORDS_FILE}")
        print(f"Subreddit: r/{SUBREDDIT_NAME}")
        print(f"Date range: {START_DATE_LOCAL.date()} to {END_DATE_LOCAL.date()}")
        print(f"CES collection mode: {ACTIVE_COLLECTION_MODE['label']}")

    except ModuleNotFoundError as error:
        print("Setup validation failed.")
        print(f"Reason: {error}")
        print("Run: pip install -r requirements.txt")

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
    print("End Date is optional. Leave it blank to use today's date when extraction runs.")
    print()

    try:
        start_date = validate_terminal_text(
            input("Enter start date (YYYY-MM-DD): "),
            field_name="Start date",
            allow_empty=False,
            max_length=20,
        )

        end_date = validate_terminal_text(
            input("Enter end date (YYYY-MM-DD), or press Enter to use today: "),
            field_name="End date",
            allow_empty=True,
            max_length=20,
        )

        update_time_range(start_date, end_date)
        print()
        print("Time range saved.")

    except KeyboardInterrupt:
        print()
        print("Time range update cancelled by user.")

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

    try:
        selected_option = validate_terminal_text(
            input("Select option [1-4]: "),
            field_name="CES collection option",
            allow_empty=False,
            max_length=5,
        )
    except KeyboardInterrupt:
        print()
        print("CES collection settings cancelled by user.")
        return
    except ValueError as error:
        print()
        print(f"Invalid option. {error}")
        return

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

def stop_extraction_process(process):
    """
    Stops the child extraction process after Ctrl+C.
    """

    if process.poll() is not None:
        return

    try:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        print("Extractor did not stop after Ctrl+C. Terminating process...")
        process.terminate()

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Extractor did not terminate. Killing process...")
            process.kill()
            process.wait()
    except Exception:
        process.terminate()
        process.wait()


def start_extraction_from_menu():
    """
    Starts extraction as a separate Python process.

    Running extraction in a separate process ensures the latest settings.json
    values are loaded fresh before extraction begins.
    """

    print_current_extraction_settings()
    print()

    try:
        confirm = validate_terminal_text(
            input("Start extraction with these settings? [y/N]: "),
            field_name="Confirmation",
            allow_empty=True,
            max_length=5,
        )
    except KeyboardInterrupt:
        print()
        print("Extraction cancelled.")
        return
    except ValueError as error:
        print()
        print(f"Extraction cancelled. Reason: {error}")
        return

    if not is_yes(confirm):
        print("Extraction cancelled.")
        return

    print()
    print("Starting extraction...")
    print("Press Ctrl+C to stop safely and save the data collected so far.")
    print()

    command = [
        sys.executable,
        "-m",
        "backend.reddit_extractor",
    ]

    environment = os.environ.copy()
    source_directory = str(PROJECT_ROOT / "src")
    existing_python_path = environment.get("PYTHONPATH", "")

    if existing_python_path:
        environment["PYTHONPATH"] = source_directory + os.pathsep + existing_python_path
    else:
        environment["PYTHONPATH"] = source_directory

    process = subprocess.Popen(command, cwd=PROJECT_ROOT, env=environment)

    try:
        return_code = process.wait()
    except KeyboardInterrupt:
        print()
        print("Extraction stop requested by user.")
        print("Waiting for the extractor to save partial results...")
        stop_extraction_process(process)
        print("Extraction stopped safely. Returning to menu.")
        return

    print()

    if return_code == 0:
        print("Extraction finished.")
    elif return_code == 130:
        print("Extraction stopped by user. Partial data was saved if any rows were collected.")
    else:
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

        choice = read_menu_choice("Select option: ", ["4.1", "4.2", "4.3", "4.4"])

        if choice is None:
            pause()

        elif choice == "4.1":
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


# ------------------------------------------------------------
# Option 5: summary
# ------------------------------------------------------------

def show_summary():
    """
    Shows summary statistics for the saved dataset.
    """

    try:
        from reports.dataset_summary import show_dataset_summary

        show_dataset_summary()

    except ModuleNotFoundError as error:
        print()
        print("Could not show dataset summary.")
        print(f"Reason: {error}")
        print("Run: pip install -r requirements.txt")

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
        try:
            print_main_header()
            print()
            print("1. Setup Reddit credentials")
            print("2. Validate setup")
            print("3. Check keywords")
            print("4. Run extraction")
            print("5. Show dataset summary")
            print("6. Exit")
            print()

            choice = read_menu_choice("Select option: ", ["1", "2", "3", "4", "5", "6"])

            if choice is None:
                pause()

            elif choice == "1":
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

        except KeyboardInterrupt:
            print()
            print("Program closed by user.")
            print("Goodbye.")
            return


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
    from backend.reddit_extractor import main as extract_main

    raise SystemExit(extract_main())


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
    Entry point for python -m rmit_ces_reddit_extractor.cli.menu.
    """

    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        main_menu()
        return

    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
        print("Program closed by user.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
