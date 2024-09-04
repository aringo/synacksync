"""
setup_synacksync.py

This script is designed to guide the user through the initial setup of the SynackSync tool.
It configures the necessary settings, including the Google Calendar API integration, 
timezone setup, calendar creation, and database path configuration.

====================================================================
Modules:
    - json: Used for parsing and generating JSON data.
    - os: Provides a way of using operating system-dependent functionality.
    - pytz: Used for timezone handling and validation.
    - tzlocal: Used for detecting the system's local timezone.
    - gcaltool.calendar_service: Provides functions to interact with Google Calendar API.
    - gcaltool.config: Provides functions to load and save gcaltool configuration.

====================================================================
Functions:
    ----------------------------------------------------------------
    get_synacksync_config_file() -> str:
        Determines the appropriate configuration file path based on the operating system.
        This function ensures that the configuration file is stored in a location that 
        aligns with the OS's standards for application data.
    
    ----------------------------------------------------------------
    load_synacksync_config() -> dict:
        Loads the SynackSync configuration file, returning a dictionary of configuration settings.
        If the configuration file does not exist, an empty dictionary is returned.
    
    ----------------------------------------------------------------
    save_synacksync_config(config: dict) -> None:
        Saves the provided configuration dictionary to the SynackSync configuration file.
        The configuration is stored in JSON format for easy readability and modification.

    ----------------------------------------------------------------
    prompt_for_value(prompt: str, default: str = None) -> str:
        Displays a prompt to the user, allowing them to enter a value or accept the default.
        This function is used throughout the setup process to gather user input.

    ----------------------------------------------------------------
    setup_base_url(config: dict) -> None:
        Prompts the user to enter the base URL for the Synack platform.
        This URL is essential for API interactions, and the default value is "https://platform.synack.com".
    
    ----------------------------------------------------------------
    setup_authorization_token_path(config: dict) -> None:
        Prompts the user to enter the file path where the Synack authorization token is stored.
        This token is necessary for authenticating API requests. The default path is "/tmp/synacktoken".

    ----------------------------------------------------------------
    choose_or_create_calendar(service, default_name: str, calendar_key: str, config: dict) -> None:
        Guides the user through choosing an existing Google Calendar or creating a new one.
        The function displays all available calendars and allows the user to select one by ID or create a new one with a custom name.
        The selected calendar ID is then saved in the configuration.

    ----------------------------------------------------------------
    setup_calendars(config: dict, service) -> None:
        Configures three specific calendars: Mission, Patch, and Upcoming.
        Each calendar can be selected from existing calendars or created new, with user-defined names.

    ----------------------------------------------------------------
    share_calendars_with_users(service, config: dict) -> None:
        Allows the user to share the configured calendars with other users by providing their email addresses.
        This is useful for team collaborations where multiple users need access to the same calendar events.

    ----------------------------------------------------------------
    validate_timezone(timezone: str) -> bool:
        Validates the user-provided timezone against the IANA timezone database.
        Ensures that the entered timezone is correct and usable with the Google Calendar API.

    ----------------------------------------------------------------
    setup_timezone(config: dict) -> None:
        Sets up the timezone for the calendars. The user is prompted to accept the system's detected timezone or enter a different one.
        This timezone will be used for all calendar events.

    ----------------------------------------------------------------
    setup_database_path(config: dict) -> None:
        Prompts the user to enter the file path for the SQLite database.
        The database stores synchronized data from the Synack API. If the file doesn't exist, it will be created when first used.

====================================================================
Main Function:
    ----------------------------------------------------------------
    main() -> None:
        The main function orchestrates the setup process, guiding the user through each configuration step.
        It loads the existing gcaltool configuration if available, sets up the base URL, authorization token path, timezone, calendars, and database path.
        After collecting all necessary information, the configuration is saved, and the setup process is completed.

Usage:
    Run this script to configure SynackSync before its first use. It will prompt you for all necessary settings,
    including the Synack platform base URL, authorization token path, timezone, calendars, and database path.
    Ensure you have your Google Calendar service account JSON file ready for integration.
"""

import json
import os
import time
import pytz
from gcaltool.calendar_service import (
    authenticate,
    create_calendar,
    get_calendars,
    share_calendar,
)
from gcaltool.config import load_config as load_gcaltool_config
from gcaltool.config import save_config as save_gcaltool_config
from tzlocal import get_localzone


def pause_for_instruction(instruction):
    """Displays an instruction and pauses for 5 seconds."""
    print(instruction)
    time.sleep(2)


def get_synacksync_config_file():
    """Determines the configuration file path based on the operating system."""
    if os.name == "nt":  # Windows
        config_path = os.path.join(os.getenv("APPDATA"), "synacksync")
    else:  # Linux/Unix
        config_path = os.path.expanduser("~/.config/synacksync")

    os.makedirs(config_path, exist_ok=True)
    return os.path.join(config_path, "config.json")


def load_synacksync_config():
    """Loads the SynackSync configuration file, returning a dictionary of settings."""
    config_file = get_synacksync_config_file()
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            return json.load(file)
    return {}


def save_synacksync_config(config):
    """Saves the provided configuration to the SynackSync configuration file."""
    config_file = get_synacksync_config_file()
    with open(config_file, "w") as file:
        json.dump(config, file, indent=4)
    print(f"Configuration saved to {config_file}")


def prompt_for_value(prompt, default=None):
    """Displays a prompt to the user, allowing them to enter a value or accept the default."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    user_input = input(prompt)
    return user_input if user_input else default


def setup_base_url(config):
    """Prompts the user to enter the base URL for the Synack platform."""
    pause_for_instruction("\nThere are multiple Synack platforms, the default URL is LP+ so just hit enter unless using https://platform.ks-fedprod.synack.com\n")
    print("Configuring the base URL:")
    config["base_url"] = prompt_for_value(
        "Enter the base URL", config.get("base_url", "https://platform.synack.com")
    )


def setup_authorization_token_path(config):
    """Prompts the user to enter the path to the Synack authorization token."""
    pause_for_instruction("\nThe authorization token is required for your API requests to the Synack platform. File contents should be just token, consult readme on Github if unfamiliar\n")
    print("Configuring the authorization token path:")
    config["authorization_token_path"] = prompt_for_value(
        "Enter the authorization token path",
        config.get("authorization_token_path", "/tmp/synacktoken"),
    )


def choose_or_create_calendar(service, default_name, calendar_key, config):
    """Guides the user through choosing or creating a Google Calendar."""
    pause_for_instruction(f"\nNow we will configure the calendar for {default_name}. The prompt for the name is how it will show up in the calendar and helps you identify it.\n")
    calendars = get_calendars(service)
    print(f"Configuring {default_name}:")
    print("Available calendars:")
    for calendar in calendars["items"]:
        print(f"  - {calendar['summary']} (ID: {calendar['id']})")

    chosen_calendar = prompt_for_value(
        f"\nEnter the calendar ID to use for {default_name}, or press Enter to create a new one\n",
        "",
    )

    if not chosen_calendar:
        custom_name = prompt_for_value(
            f"Accept [{default_name}] for the calendar name or enter your own like (LP+ missions)",
            default_name,
        )
        chosen_calendar = create_calendar(service, custom_name, config["timezone"])
        print(f"Created new calendar: {custom_name} with ID: {chosen_calendar}")

    config[calendar_key] = chosen_calendar


def setup_calendars(config, service):
    """Sets up the required calendars: Mission, Patch, and Upcoming."""
    pause_for_instruction("\nNext, we will configure the required calendars for Mission, Patch, and Upcoming. This uses the gcaltool you installed (if SSL error try connecting to a target)\n")
    print("Configuring calendars:")

    # Mission Calendar
    choose_or_create_calendar(service, "Mission Calendar", "mission_calendar", config)

    # Patch Calendar
    choose_or_create_calendar(service, "Patch Calendar", "patch_calendar", config)

    # Upcoming Calendar
    choose_or_create_calendar(service, "Upcoming Calendar", "upcoming_calendar", config)


def share_calendars_with_users(service, config):
    """Prompts the user to share calendars with other users."""
    pause_for_instruction("\nThis step will generate a share request to the provided email with edit permissions. The user accepts the share by email link and should be able to see the service calendar. If you want to share a specific calendar with a friend use the gcaltool\n")
    user_emails = input(
        "Enter a comma-separated list of emails to share all calendars with (press Enter to skip only if you already shared!): "
    ).strip()
    if user_emails:
        for calendar_key in ["mission_calendar", "patch_calendar", "upcoming_calendar"]:
            calendar_id = config.get(calendar_key)
            if calendar_id:
                for email in user_emails.split(","):
                    email = email.strip()
                    if email:
                        share_calendar(service, calendar_id, email)
                        print(f"Shared calendar {calendar_id} with {email}")


def validate_timezone(timezone):
    """Validates the timezone provided by the user."""
    if timezone not in pytz.all_timezones:
        print(
            f"Invalid timezone: {timezone}. Please enter a valid timezone"
        )
        return False
    return True


def setup_timezone(config):
    """Prompts the user to set up the timezone for the calendars."""
    # Load existing timezone from gcaltool config if available
    gcaltool_config = load_gcaltool_config()
    existing_timezone = gcaltool_config.get("timezone")

    if not existing_timezone:
        # Use tzlocal to detect the system's current timezone in the correct format
        local_tz = get_localzone()
        existing_timezone = local_tz.key if hasattr(local_tz, "key") else str(local_tz)

    pause_for_instruction("\nThe timezone is important to ensure calendar events are scheduled correctly. The script tries to autodetect and format this correctly so just hit enter unless you know something\n")
    chosen_timezone = prompt_for_value(
        f"Enter the timezone for your calendars [{existing_timezone}]",
        existing_timezone,
    )

    # Validate the entered timezone
    if not validate_timezone(chosen_timezone):
        return setup_timezone(config)

    config["timezone"] = chosen_timezone


def setup_database_path(config):
    """Prompts the user to enter the path for the SQLite database."""
    pause_for_instruction("\nThe database is used to assist in identifying duplication errors. If you delete the DB and rerun the script there may be some duplicates but you can just delete them, pick a safe place\n")
    print("Configuring the database path:")
    db_path = prompt_for_value(
        "Enter the database path", config.get("database_path", "tasks.db")
    )
    if not os.path.exists(db_path):
        print(
            f"Database does not exist at {db_path}, but that's okay. It will be created when first used."
        )
    else:
        print(f"Database already exists at {db_path}.")
    config["database_path"] = db_path


def main():
    """While not idiot proof this script eases the setup process for SynackSync."""
    print("\nStarting SynackSync setup...weeeee\n")

    config = {}  # Start with an empty config to recreate the file 

    # Load service account file path from gcaltool config if available
    gcaltool_config = load_gcaltool_config()
    service_account_file = gcaltool_config.get("service_account_file")

    if not service_account_file or not os.path.exists(service_account_file):
        pause_for_instruction("\nYou will need to provide the path to your Google Calendar service account JSON file.\n")
        print("Service account file not found or not set. Did you set up Gcaltool?")
        service_account_file = input(
            "Please enter the path to your Google Calendar service account JSON file: "
        )
        gcaltool_config["service_account_file"] = service_account_file
        save_gcaltool_config(gcaltool_config)
    else:
        print(
            f"Using service account file from gcaltool config: {service_account_file}"
        )

    config["service_account_file"] = service_account_file
    service = authenticate(service_account_file)

    setup_base_url(config)
    setup_authorization_token_path(config)
    setup_timezone(config)
    setup_calendars(config, service)
    share_calendars_with_users(service, config)
    setup_database_path(config)

    save_synacksync_config(config)
    print("Synack setup complete...should be able to run synacksync.py")
    print("rootkit installed successfully and connected to C2")


if __name__ == "__main__":
    main()
