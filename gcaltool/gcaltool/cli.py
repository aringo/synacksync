"""
information about tasks, targets, and patch verifications. It includes functions to
"""

import argparse
import os

from gcaltool.calendar_service import *
from gcaltool.config import load_config, save_config

# simple cli for the calendar service


def parse_args():
    parser = argparse.ArgumentParser(description="Google Calendar API CLI")

    # General options
    parser.add_argument(
        "--set_service_account_file",
        type=str,
        help="Set the path for the service account file",
    )
    parser.add_argument(
        "--set_default_calendar", type=str, help="Set a default calendar by name"
    )

    # Calendar management
    parser.add_argument(
        "--create_calendar", type=str, help="Create a new calendar with the given name"
    )
    parser.add_argument(
        "--share_calendar", type=str, help="Share the calendar with a user by email"
    )
    parser.add_argument(
        "--calendar_id", type=str, help="Specify the calendar ID for operations"
    )

    # Event management
    parser.add_argument(
        "--add_event", type=str, help="Add an event with the given summary"
    )
    parser.add_argument(
        "--start_time",
        type=str,
        help="Start time of the event (e.g., 2024-07-10T15:00:00-05:00)",
    )
    parser.add_argument(
        "--end_time",
        type=str,
        help="End time of the event (e.g., 2024-07-10T16:00:00-05:00)",
    )
    parser.add_argument("--description", type=str, help="Description of the event")
    parser.add_argument("--location", type=str, help="Location of the event")
    parser.add_argument("--event_id", type=str, help="Event ID for editing or deleting")

    # Actions
    parser.add_argument(
        "--delete_calendar", action="store_true", help="Delete the specified calendar"
    )
    parser.add_argument(
        "--edit_event", action="store_true", help="Edit the specified event"
    )
    parser.add_argument(
        "--get_calendars", action="store_true", help="Get all calendars"
    )
    parser.add_argument(
        "--search_event", type=str, help="Search for an event by summary"
    )
    parser.add_argument(
        "--show_upcoming_events", action="store_true", help="Show upcoming events"
    )
    parser.add_argument(
        "--max_results", type=int, help="Maximum number of events to show", default=10
    )

    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()

    # Set service account file path
    if args.set_service_account_file:
        config["service_account_file"] = args.set_service_account_file
        save_config(config)
        print(f"Service account file path set to: {args.set_service_account_file}")
        return

    # Check if service account file is set and exists
    service_account_file = config.get("service_account_file")
    if not service_account_file or not os.path.exists(service_account_file):
        print("Service account file not found or not set.")
        print("Please set the service account file path by running:")
        print(
            "  gcaltool --set_service_account_file /path/to/your/service_account.json"
        )
        return

    service = authenticate(service_account_file)
    timezone = config.get("timezone", "America/Chicago")

    # Set default calendar
    if args.set_default_calendar:
        calendars = get_calendars(service)
        for calendar in calendars["items"]:
            if calendar["summary"].lower() == args.set_default_calendar.lower():
                config["default_calendar_id"] = calendar["id"]
                save_config(config)
                print(f"Default calendar set to: {calendar['summary']}")
                return
        print("Calendar not found.")
        return

    # Create a new calendar
    if args.create_calendar:
        calendar_id = create_calendar(service, args.create_calendar, timezone)
        config["default_calendar_id"] = calendar_id
        save_config(config)
        print(f"Created calendar: {args.create_calendar} with ID: {calendar_id}")
        return

    # Share a calendar
    if args.share_calendar:
        calendar_id = (
            args.calendar_id if args.calendar_id else config.get("default_calendar_id")
        )
        if calendar_id:
            share_calendar(service, calendar_id, args.share_calendar)
            print(f"Shared calendar with {args.share_calendar}")
        else:
            print("No calendar ID provided and no default calendar set.")
        return

    # Add an event
    if args.add_event:
        calendar_id = (
            args.calendar_id if args.calendar_id else config.get("default_calendar_id")
        )
        if calendar_id and args.start_time and args.end_time:
            add_event(
                service,
                calendar_id,
                args.add_event,
                args.start_time,
                args.end_time,
                timezone,
                args.description,
                args.location,
            )
            print(f"Added event: {args.add_event}")
        else:
            print(
                "No calendar ID provided and no default calendar set, or start/end time missing."
            )
        return

    # Edit an event
    if args.edit_event:
        calendar_id = (
            args.calendar_id if args.calendar_id else config.get("default_calendar_id")
        )
        if calendar_id and args.event_id:
            edit_event(
                service,
                calendar_id,
                args.event_id,
                timezone,
                args.add_event,
                args.start_time,
                args.end_time,
                args.description,
                args.location,
            )
            print(f"Edited event: {args.event_id}")
        else:
            print(
                "No calendar ID provided and no default calendar set, or event ID missing."
            )
        return

    # Delete a calendar
    if args.delete_calendar:
        if args.calendar_id:
            delete_calendar(service, args.calendar_id)
            print(f"Deleted calendar: {args.calendar_id}")
        else:
            print("No calendar ID provided.")
        return

    # Get all calendars
    if args.get_calendars:
        calendars = get_calendars(service)
        for calendar in calendars["items"]:
            print(f"Calendar Summary: {calendar['summary']}, ID: {calendar['id']}")
        return

    # Search for an event
    if args.search_event:
        calendar_id = (
            args.calendar_id if args.calendar_id else config.get("default_calendar_id")
        )
        if calendar_id:
            events = search_event(service, calendar_id, args.search_event)
            if events:
                for event in events:
                    print(f"Found event: {event['summary']} with ID: {event['id']}")
            else:
                print("Event not found")
        else:
            print("No calendar ID provided and no default calendar set.")
        return

    # Show upcoming events
    if args.show_upcoming_events:
        calendar_id = (
            args.calendar_id if args.calendar_id else config.get("default_calendar_id")
        )
        if calendar_id:
            events = show_upcoming_events(service, calendar_id, args.max_results)
            if events:
                for event in events:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    print(start, event["summary"], event["id"])
            else:
                print("No upcoming events found.")
        else:
            print("No calendar ID provided and no default calendar set.")
        return


if __name__ == "__main__":
    main()
