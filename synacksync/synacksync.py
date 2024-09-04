"""
synacksync.py

This script is designed to synchronize tasks, targets, and patch verifications from 
a Synack API with a Google Calendar. The script fetches data from the Synack platform 
and updates the calendar with relevant events. It also manages local storage of this 
data using a SQLite database.

Modules:
    - warnings: Used to manage and filter warning messages.
    - requests: Used for making HTTP requests to the Synack API.
    - json: Used for parsing and generating JSON data.
    - datetime: Used for handling date and time operations.
    - time: Provides various time-related functions.
    - os: Provides a way of using operating system-dependent functionality.
    - re: Used for regular expression operations.
    - pytz: Used for timezone handling.
    - urllib3: Used for handling HTTP connections and SSL warnings.

Imports from gcaltool.calendar_service:
    - authenticate: Authenticates with the Google Calendar API using a service account.
    - get_upcoming_events: Retrieves upcoming events from a Google Calendar.

Imports from database:
    - setup_database: Sets up the SQLite database.
    - save_tasks_to_db: Saves or updates tasks in the database.
    - save_targets_to_db: Saves or updates targets in the database.
    - save_patch_verifications_to_db: Saves or updates patch verifications in the database.
    - get_upcoming_entries: Retrieves upcoming tasks, targets, and patch verifications from the database.

Functions:
    - load_synacksync_config() -> dict:
        Loads the SynackSync configuration file, returning a dictionary of configuration settings.
    
    - sanitize_text(text: str) -> str:
        Sanitizes text by masking IP addresses and domain names with generic placeholders.

    - read_token(file_path: str) -> str or None:
        Reads and returns the authorization token from a file. Returns None if the file is not found or unreadable.

    - get_system_timezone() -> str:
        Returns the system's current timezone as a string.

    - load_calendar_ids() -> tuple:
        Loads and returns the Google Calendar IDs for missions, patches, and upcoming events from the configuration.

    - add_event(service, calendar_id: str, summary: str, start, end, description: str = None, location: str = None) -> str:
        Adds an event to the specified Google Calendar and returns the event ID.

    - edit_event(service, calendar_id: str, event_id: str, summary: str = None, start = None, end = None, description: str = None, location: str = None) -> str:
        Edits an existing event in the specified Google Calendar and returns the event ID.

    - fetch_patch_verifications() -> list:
        Fetches patch verifications from the Synack API.

    - fetch_tasks() -> list:
        Fetches tasks from the Synack API.

    - fetch_targets() -> list:
        Fetches targets from the Synack API.

    - compare_and_update(db_entries: list, api_entries: list, entry_type: str, service, calendar_id: str) -> None:
        Compares entries from the database with those from the API, updating the calendar and database as necessary.

    - main() -> None:
        The main function that orchestrates the fetching, comparison, and updating of tasks, targets, and patch verifications between the Synack API, Google Calendar, and the local database.

Usage:
    This script should be executed to synchronize Synack tasks, targets, and patch verifications with Google Calendar events. 
    Run the script periodically (e.g., via cron job) to keep your Google Calendar up-to-date with the latest Synack data.
"""

import datetime
import json
import os
import re
import time
import warnings
import pytz
import requests
import urllib3
from database import (
    get_upcoming_entries,
    save_patch_verifications_to_db,
    save_targets_to_db,
    save_tasks_to_db,
    setup_database,
)
from gcaltool.calendar_service import authenticate, get_upcoming_events, delete_event

warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# Check if SNIMissingWarning exists in urllib3.exceptions and suppress it if it does
if hasattr(urllib3.exceptions, "SNIMissingWarning"):
    warnings.filterwarnings("ignore", category=urllib3.exceptions.SNIMissingWarning)

# Override the default verify flag for requests
requests.Session().verify = False


# Load configuration from the synacksync config file
def load_synacksync_config():
    if os.name == "nt":  # Windows
        config_path = os.path.join(os.getenv("APPDATA"), "synacksync")
    else:  # Linux/Unix
        config_path = os.path.expanduser("~/.config/synacksync")

    config_file = os.path.join(config_path, "config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            return json.load(file)
    else:
        raise FileNotFoundError(f"Config file not found at {config_file}")


config = load_synacksync_config()

base_url = config.get("base_url", "https://platform.ks-fedprod.synack.com")
token_file_path = config.get("authorization_token_path", "")
db_path = config.get("database_path", "tasks.db")
service_account_file = config.get("service_account_file")
timezone = config.get("timezone")

if not service_account_file or not os.path.exists(service_account_file):
    raise FileNotFoundError(
        "Service account file not found. Please set the service account file in SynackSync configuration."
    )

# Authenticate with Google Calendar API
service = authenticate(service_account_file)


def sanitize_text(text):
    ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    domain_pattern = r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b"
    sanitized_text = re.sub(ip_pattern, "*.*.*.*", text)
    sanitized_text = re.sub(domain_pattern, "[domain]", sanitized_text)
    return sanitized_text


def read_token(file_path):
    try:
        with open(file_path, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        print(
            f"Error: Token file '{file_path}' not found. Please ensure the file exists."
        )
        return None
    except IOError as e:
        print(
            f"Error: An I/O error occurred while reading the token file '{file_path}': {e}"
        )
        return None


authorization_token = read_token(token_file_path)

if authorization_token is None:
    print("Failed to read the authorization token. Exiting.")
    exit(1)

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Authorization": f"Bearer {authorization_token}",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=4",
    "Te": "trailers",
    "Connection": "keep-alive",
}


def get_system_timezone():
    return str(datetime.datetime.now(pytz.timezone("UTC")).astimezone().tzinfo)


def load_calendar_ids():
    mission_calendar_id = config.get("mission_calendar")
    patch_calendar_id = config.get("patch_calendar")
    upcoming_calendar_id = config.get("upcoming_calendar")
    return mission_calendar_id, patch_calendar_id, upcoming_calendar_id


def add_event(
    service, calendar_id, summary, start, end, description=None, location=None
):
    event_timezone = timezone if timezone else get_system_timezone()

    event = {
        "summary": sanitize_text(summary),
        "location": sanitize_text(location) if location else None,
        "description": sanitize_text(description) if description else None,
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": event_timezone,
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": event_timezone,
        },
    }

    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print("Event created: %s" % (event.get("htmlLink")))
    return event.get("id")


def edit_event(
    service,
    calendar_id,
    event_id,
    summary=None,
    start=None,
    end=None,
    description=None,
    location=None,
):
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        event_timezone = timezone if timezone else get_system_timezone()

        if summary:
            event["summary"] = sanitize_text(summary)
        if start:
            event["start"]["dateTime"] = start.isoformat()
            event["start"]["timeZone"] = event_timezone
        if end:
            event["end"]["dateTime"] = end.isoformat()
            event["end"]["timeZone"] = event_timezone
        if description:
            event["description"] = sanitize_text(description)
        if location:
            event["location"] = sanitize_text(location)

        updated_event = (
            service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event)
            .execute()
        )
        print(f"Event updated: {updated_event.get('htmlLink')}")
        return updated_event.get("id")
    except googleapiclient.errors.HttpError as error:
        print(f"An error occurred: {error}")


def parse_targets_response(data):
    targets = []
    for item in data:
        if "slug" not in item:
            print(f"Skipping target with missing slug: {item}")
            continue
        target = {
            "id": item.get("slug"),
            "category": item["category"].get("name", ""),
            "codename": item.get("codename", ""),
            "averagePayout": item.get("averagePayout", 0),
            "isActive": item.get("isActive", False),
            "start": datetime.datetime.fromtimestamp(
                item.get("upcoming_start_date"), datetime.timezone.utc
            ),
            "discovery": item.get("vulnerability_discovery", False),
            "vuln_accepted": item.get("accepted_vulnerabilities", 0),
            "dynamic_payment_percentage": item.get("dynamic_payment_percentage", "0.0"),
            "event_id": item.get("event_id", None),
        }
        targets.append(target)
    return targets


def parse_tasks_response(data):
    tasks = []
    for item in data:
        if "id" not in item:
            print(f"Skipping task with missing id: {item}")
            continue

        claimed_on = datetime.datetime.fromisoformat(
            item.get("claimedOn").replace("Z", "+00:00")
        )

        # Handling the payout amount and currency safely
        payout_info = item.get("payout", {})
        payout_amount = payout_info.get("amount", 0)  # Default to 0 if not present
        payout_currency = payout_info.get(
            "currency", "USD"
        )  # Default to USD if not present

        task = {
            "id": item.get("id"),
            "title": sanitize_text(item.get("title", "")),
            "description": sanitize_text(item.get("description", "")),
            "listing_codename": item.get("listingCodename", ""),
            "time_given": item.get("maxCompletionTimeInSecs", 0),
            "claimed_on": claimed_on,
            "max_completion_time": claimed_on
            + datetime.timedelta(seconds=int(item.get("maxCompletionTimeInSecs", 0))),
            "payout_amount": payout_amount,  # Ensure the payout amount is set
            "payout_currency": payout_currency,  # Ensure the currency is set
            "event_id": item.get("event_id", None),
        }
        tasks.append(task)
    return tasks


def parse_patch_verifications_response(data):
    patch_verifications = []
    for item in data:
        if "id" not in item:
            print(f"Skipping patch verification with missing id: {item}")
            continue
        patch_verification = {
            "id": item.get("id"),
            "message": sanitize_text(item.get("message", "")),
            "expires": datetime.datetime.fromtimestamp(
                item.get("expires_at", 0), datetime.timezone.utc
            ),
            "vuln_id": item["vulnerability"].get("id", ""),
            "vuln_title": sanitize_text(item.get("vulnerability").get("title", "")),
            "event_id": item.get("event_id", None),
        }
        patch_verifications.append(patch_verification)
    return patch_verifications


def fetch_patch_verifications():
    params = {"page": 1, "per_page": 5}
    response = requests.get(
        f"{base_url}/api/patch_verifications",
        headers=headers,
        params=params,
        verify=False,
    )
    if response.status_code == 200:
        response_data = response.json()
        return parse_patch_verifications_response(response_data)
    else:
        print(f"Failed to fetch data: {response.status_code}")
        return []


def fetch_tasks():
    params = {
        "perPage": 20,
        "viewed": "true",
        "page": 1,
        "status": "CLAIMED",
        "includeAssignedBySynackUser": "true",
    }
    response = requests.get(
        f"{base_url}/api/tasks/v2/tasks", headers=headers, params=params, verify=False
    )
    if response.status_code == 200:
        response_data = response.json()
        return parse_tasks_response(response_data)
    else:
        print(f"Failed to fetch data: {response.status_code}")
        return []


def fetch_targets():
    current_epoch_time = (
        int(time.time()) + 5 * 24 * 60 * 60
    )  # Current time + 5 days in seconds
    params = {
        "filter[primary]": "upcoming",
        "filter[secondary]": "all",
        "filter[category]": "all",
        "filter[industry]": "all",
        "filter[payout_status]": "all",
        "filter[to]": current_epoch_time,
        "sorting[field]": "upcomingStartDate",
        "sorting[direction]": "asc",
    }
    response = requests.get(
        f"{base_url}/api/targets", headers=headers, params=params, verify=False
    )
    if response.status_code == 200:
        response_data = response.json()
        print("Targets API Response:", response_data)  # Debug print
        return parse_targets_response(response_data)
    elif response.status_code == 401:
        print("Unauthorized access. Stopping processing.")
        exit(1)
    else:
        print(f"Failed to fetch data: {response.status_code}")
        exit(1)


def compare_and_update(db_entries, api_entries, entry_type, service, calendar_id):
    key = "id"

    # Get the upcoming events from the Google Calendar
    upcoming_events = get_upcoming_events(service, calendar_id)

    db_dict = {entry[key]: entry for entry in db_entries} if db_entries else {}
    api_dict = {entry[key]: entry for entry in api_entries if key in entry}

    for api_id, api_entry in api_dict.items():
        if entry_type == "task":
            payout_amount = api_entry.get("payout_amount", 0)
            listing_codename = api_entry.get("listing_codename", "")
            summary = f"{payout_amount} - {api_entry['title']} - {listing_codename}"
            start = api_entry.get(
                "claimed_on", datetime.datetime.now(datetime.timezone.utc)
            )
            end = api_entry.get(
                "max_completion_time", start + datetime.timedelta(hours=1)
            )  # Assuming 1-hour duration if end time is not provided
            description = api_entry["description"]
        elif entry_type == "target":
            summary = api_entry["codename"]
            start = api_entry.get("start", datetime.datetime.now(datetime.timezone.utc))
            end = (
                start  # Assuming the event ends at the same time it starts for targets
            )
            description = f"Category: {api_entry['category']}, Discovery: {api_entry['discovery']}, Vuln Accepted: {api_entry['vuln_accepted']}, Dynamic Payment Percentage: {api_entry['dynamic_payment_percentage']}"
        elif entry_type == "patch_verification":
            summary = f"Patch Verification for {api_entry['vuln_title']}"
            start = api_entry.get("start", datetime.datetime.now(datetime.timezone.utc))
            end = api_entry.get(
                "expires", start + datetime.timedelta(hours=1)
            )  # Assuming 1-hour duration if end time is not provided
            description = api_entry["message"]

        # Check if the title and time already exist in upcoming events
        event_exists = False
        for event in upcoming_events.values():
            event_start = datetime.datetime.fromisoformat(event["start"]["dateTime"])
            if event["summary"] == summary and event_start == start:
                event_exists = True
                break

        if event_exists:
            print(
                f"Skipping update for {summary} as it already exists on the calendar with the same start time."
            )
            continue

        if api_id in db_dict:
            db_entry = db_dict[api_id]
            if db_entry != api_entry:
                if "event_id" in db_entry and db_entry["event_id"]:
                    event_id = edit_event(
                        service,
                        calendar_id,
                        db_entry["event_id"],
                        summary=summary,
                        start=start,
                        end=end,
                        description=description,
                    )
                else:
                    event_id = add_event(
                        service,
                        calendar_id,
                        summary=summary,
                        start=start,
                        end=end,
                        description=description,
                    )
                api_entry["event_id"] = event_id
                if entry_type == "task":
                    save_tasks_to_db(db_path, [api_entry])
                elif entry_type == "target":
                    save_targets_to_db(db_path, [api_entry])
                elif entry_type == "patch_verification":
                    save_patch_verifications_to_db(db_path, [api_entry])
        else:
            event_id = add_event(
                service,
                calendar_id,
                summary=summary,
                start=start,
                end=end,
                description=description,
            )
            api_entry["event_id"] = event_id
            if entry_type == "task":
                save_tasks_to_db(db_path, [api_entry])
            elif entry_type == "target":
                save_targets_to_db(db_path, [api_entry])
            elif entry_type == "patch_verification":
                save_patch_verifications_to_db(db_path, [api_entry])

    for db_id, db_entry in db_dict.items():
        if db_id not in api_dict:
            if "event_id" in db_entry and db_entry["event_id"]:
                delete_event(service, calendar_id, db_entry["event_id"])
            if entry_type == "task":
                save_tasks_to_db(db_path, [db_entry], delete=True)
            elif entry_type == "target":
                save_targets_to_db(db_path, [db_entry], delete=True)
            elif entry_type == "patch_verification":
                save_patch_verifications_to_db(db_path, [db_entry], delete=True)


def main():
    mission_calendar_id, patch_calendar_id, upcoming_calendar_id = load_calendar_ids()

    print(f"Mission Calendar ID: {mission_calendar_id}")
    print(f"Patch Calendar ID: {patch_calendar_id}")
    print(f"Upcoming Calendar ID: {upcoming_calendar_id}")

    if not mission_calendar_id or not patch_calendar_id or not upcoming_calendar_id:
        print(
            "One or more calendar IDs are missing. Please set all required calendar IDs."
        )
        return

    setup_database(db_path)

    db_tasks, db_targets, db_patch_verifications = get_upcoming_entries(db_path)

    api_patch_verifications = fetch_patch_verifications()
    api_tasks = fetch_tasks()
    api_targets = fetch_targets()

    compare_and_update(db_tasks, api_tasks, "task", service, mission_calendar_id)
    compare_and_update(db_targets, api_targets, "target", service, upcoming_calendar_id)
    compare_and_update(
        db_patch_verifications,
        api_patch_verifications,
        "patch_verification",
        service,
        patch_calendar_id,
    )


if __name__ == "__main__":
    main()
