import datetime
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.auth.transport.requests
import google_auth_httplib2
import googleapiclient.errors
import httplib2


SCOPES = ['https://www.googleapis.com/auth/calendar']
logging.basicConfig(level=logging.INFO)

def authenticate(service_account_file):
    """
    Authenticates and returns a Google Calendar service object.

    Parameters:
    - service_account_file: Path to the service account JSON file.

    Returns:
    - service: Authenticated Google Calendar service object.
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=SCOPES)
        authorized_http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http(disable_ssl_certificate_validation=True))
        service = build('calendar', 'v3', http=authorized_http, cache_discovery=False)
        return service
    except Exception as e:
        logging.error(f"Failed to authenticate with Google Calendar API: {e}")
        raise

def create_calendar(service, calendar_name, timezone):
    """
    Creates a new calendar with the specified name and timezone.

    Parameters:
    - service: Authenticated Google Calendar service object.
    - calendar_name: Name for the new calendar.
    - timezone: Timezone for the calendar.

    Returns:
    - calendar_id: The ID of the newly created calendar.
    """
    try:
        calendar = {'summary': calendar_name, 'timeZone': timezone}
        created_calendar = service.calendars().insert(body=calendar).execute()
        return created_calendar['id']
    except googleapiclient.errors.HttpError as e:
        logging.error(f"Failed to create calendar '{calendar_name}': {e}")
        raise

def share_calendar(service, calendar_id, user_email):
    """
    Shares the specified calendar with a user by email.

    Parameters:
    - service: Authenticated Google Calendar service object.
    - calendar_id: ID of the calendar to share.
    - user_email: Email address of the user to share the calendar with.
    """
    try:
        rule = {'scope': {'type': 'user', 'value': user_email}, 'role': 'writer'}
        service.acl().insert(calendarId=calendar_id, body=rule).execute()
        logging.info(f"Shared calendar '{calendar_id}' with '{user_email}'.")
    except googleapiclient.errors.HttpError as e:
        logging.error(f"Failed to share calendar '{calendar_id}' with '{user_email}': {e}")
        raise

def add_event(service, calendar_id, summary, start_time, end_time, timezone, description=None, location=None):
    """
    Adds an event to the specified calendar.

    Parameters:
    - service: Authenticated Google Calendar service object.
    - calendar_id: ID of the calendar to add the event to.
    - summary: Title of the event.
    - start_time: Start time of the event (datetime object).
    - end_time: End time of the event (datetime object).
    - timezone: Timezone of the event.
    - description: (Optional) Description of the event.
    - location: (Optional) Location of the event.

    Returns:
    - event_id: The ID of the newly created event.
    """
    try:
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': timezone},
            'end': {'dateTime': end_time, 'timeZone': timezone}
        }
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        logging.info(f"Event '{summary}' added to calendar '{calendar_id}'.")
        return event.get('id')
    except googleapiclient.errors.HttpError as e:
        logging.error(f"Failed to add event '{summary}' to calendar '{calendar_id}': {e}")
        raise

def delete_calendar(service, calendar_id):
    """
    Deletes the specified calendar.

    Parameters:
    - service: Authenticated Google Calendar service object.
    - calendar_id: ID of the calendar to delete.
    """
    try:
        service.calendars().delete(calendarId=calendar_id).execute()
        logging.info(f"Calendar '{calendar_id}' deleted.")
    except googleapiclient.errors.HttpError as e:
        logging.error(f"Failed to delete calendar '{calendar_id}': {e}")
        raise

def edit_event(service, calendar_id, event_id, timezone, summary=None, start_time=None, end_time=None, description=None, location=None):
    """
    Edits an existing event in the specified calendar.

    Parameters:
    - service: Authenticated Google Calendar service object.
    - calendar_id: ID of the calendar containing the event.
    - event_id: ID of the event to edit.
    - timezone: Timezone of the event.
    - summary: (Optional) New summary/title of the event.
    - start_time: (Optional) New start time of the event (datetime object).
    - end_time: (Optional) New end time of the event (datetime object).
    - description: (Optional) New description of the event.
    - location: (Optional) New location of the event.
    """
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        if summary: event['summary'] = summary
        if start_time:
            event['start']['dateTime'] = start_time
            event['start']['timeZone'] = timezone
        if end_time:
            event['end']['dateTime'] = end_time
            event['end']['timeZone'] = timezone
        if description: event['description'] = description
        if location: event['location'] = location
        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        logging.info(f"Event '{summary}' updated in calendar '{calendar_id}'.")
    except googleapiclient.errors.HttpError as e:
        logging.error(f"Failed to update event '{event_id}' in calendar '{calendar_id}': {e}")
        raise

def get_calendars(service):
    """
    Retrieves all calendars accessible by the authenticated user.

    Parameters:
    - service: Authenticated Google Calendar service object.

    Returns:
    - calendars: List of calendars available to the user.
    """
    try:
        return service.calendarList().list().execute()
    except googleapiclient.errors.HttpError as e:
        logging.error("Failed to retrieve calendars.")
        raise

def search_event(service, calendar_id, summary):
    """
    Searches for an event by summary in the specified calendar.

    Parameters:
    - service: Authenticated Google Calendar service object.
    - calendar_id: ID of the calendar to search.
    - summary: Summary of the event to search for.

    Returns:
    - events: List of events matching the summary.
    """
    try:
        events_result = service.events().list(calendarId=calendar_id).execute()
        return [event for event in events_result.get('items', []) if event['summary'] == summary]
    except googleapiclient.errors.HttpError as e:
        logging.error(f"Failed to search events with summary '{summary}' in calendar '{calendar_id}': {e}")
        raise


def delete_event(service, calendar_id, event_id):
    """
    Deletes an event from the calendar.

    Parameters:
    - service: Authenticated Google Calendar service object.
    - calendars_id: Calendar to modify.
    - event_id: Event to delete. 
    """
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        print(f"Deleted event: {event_id}")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_upcoming_events(service, calendar_id, time_min=None):
    """
    Retrieves upcoming events from the specified calendar starting from time_min.

    Parameters:
    - service: Authenticated Google Calendar service object.
    - calendar_id: ID of the calendar to retrieve events from.
    - time_min: (Optional) Start time for filtering events, defaults to the current time.

    Returns:
    - upcoming_events: Dictionary of upcoming events, keyed by event summary.
    """
    try:
        # Use timezone-aware datetime for time_min
        time_min = time_min if time_min else datetime.datetime.now(datetime.timezone.utc).isoformat()

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        upcoming_events = {event['summary']: event for event in events_result.get('items', [])}
        return upcoming_events

    except googleapiclient.errors.HttpError as error:
        logging.error(f"An error occurred while retrieving upcoming events: {error}")
        return {}
