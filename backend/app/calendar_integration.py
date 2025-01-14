import os
import logging
import pickle
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from flask import Blueprint, jsonify

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
calendar_bp = Blueprint('calendar', __name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class GoogleCalendar:
    def __init__(self):
        logger.info("Initializing Google Calendar integration")
        self.creds = None
        self.service = None
        if not self.authenticate():
            logger.error("Failed to authenticate during initialization")
        
    def authenticate(self):
        """Authenticate with Google Calendar API"""
        try:
            logger.info("Starting authentication process")
            
            # Check if credentials file exists
            if not os.path.exists('credentials.json'):
                logger.error("credentials.json file not found in current directory")
                logger.info(f"Current working directory: {os.getcwd()}")
                return False
            
            # The file token.pickle stores the user's access and refresh tokens
            if os.path.exists('token.pickle'):
                logger.info("Found existing token.pickle file")
                try:
                    with open('token.pickle', 'rb') as token:
                        self.creds = pickle.load(token)
                        logger.info("Loaded credentials from token.pickle")
                except Exception as e:
                    logger.error(f"Error loading token.pickle: {str(e)}")
                    self.creds = None
            else:
                logger.info("No token.pickle file found")
                    
            # If there are no (valid) credentials available, let the user log in.
            if not self.creds:
                logger.info("No credentials found, starting OAuth flow")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    logger.info("Successfully completed OAuth flow")
                except Exception as e:
                    logger.error(f"Error during OAuth flow: {str(e)}")
                    return False
                
                # Save the credentials for the next run
                try:
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(self.creds, token)
                    logger.info("Saved new credentials to token.pickle")
                except Exception as e:
                    logger.error(f"Error saving token.pickle: {str(e)}")
            elif not self.creds.valid:
                logger.info("Credentials exist but are not valid")
                if self.creds.expired and self.creds.refresh_token:
                    logger.info("Attempting to refresh expired credentials")
                    try:
                        self.creds.refresh(Request())
                        logger.info("Successfully refreshed credentials")
                    except Exception as e:
                        logger.error(f"Error refreshing credentials: {str(e)}")
                        return False
                else:
                    logger.info("Starting new OAuth flow due to invalid credentials")
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', SCOPES)
                        self.creds = flow.run_local_server(port=0)
                        logger.info("Successfully completed OAuth flow")
                    except Exception as e:
                        logger.error(f"Error during OAuth flow: {str(e)}")
                        return False
                    
                # Save the refreshed/new credentials
                try:
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(self.creds, token)
                    logger.info("Saved credentials to token.pickle")
                except Exception as e:
                    logger.error(f"Error saving token.pickle: {str(e)}")

            try:
                self.service = build('calendar', 'v3', credentials=self.creds)
                logger.info("Successfully built Google Calendar service")
                return True
            except Exception as e:
                logger.error(f"Error building calendar service: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_events(self, start_date, end_date):
        """Get events between start_date and end_date from all calendars"""
        try:
            if not self.service:
                logger.error("No service available")
                if not self.authenticate():
                    logger.error("Authentication failed in get_events")
                    return None
                    
            # Convert dates to RFC3339 timestamp
            start = start_date.isoformat() + 'Z'
            end = end_date.isoformat() + 'Z'
            
            logger.info(f"Fetching events from {start} to {end}")
            
            try:
                # First, test the API with a simple call
                logger.info("Testing API access with primary calendar")
                primary = self.service.calendars().get(calendarId='primary').execute()
                logger.info(f"Successfully accessed primary calendar: {primary.get('summary')}")
                
                # Now get list of all calendars
                logger.info("Fetching calendar list")
                calendar_list = self.service.calendarList().list().execute()
                calendars = calendar_list.get('items', [])
                logger.info(f"Found {len(calendars)} calendars:")
                for cal in calendars:
                    logger.info(f"Calendar: {cal.get('summary')} ({cal.get('id')})")
                    logger.info(f"Access Role: {cal.get('accessRole')}")
                    logger.info(f"Primary: {cal.get('primary', False)}")
                    logger.info("---")
                
            except Exception as e:
                logger.error(f"Error accessing calendars: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return None
            
            # Fetch events from each calendar
            all_events = []
            for calendar in calendars:
                calendar_id = calendar.get('id')
                calendar_name = calendar.get('summary', 'Unknown Calendar')
                access_role = calendar.get('accessRole', 'unknown')
                
                logger.info(f"\nProcessing calendar: {calendar_name}")
                logger.info(f"Access Role: {access_role}")
                logger.info(f"Calendar ID: {calendar_id}")
                
                # Skip if calendar is deleted or hidden
                if calendar.get('deleted', False) or calendar.get('hidden', False):
                    logger.info(f"Skipping calendar {calendar_name} - deleted or hidden")
                    continue
                
                # Skip the Tasks calendar
                if calendar_name == 'Tasks':
                    logger.info(f"Skipping Tasks calendar")
                    continue
                
                # Skip calendars we can't read
                if access_role not in ['owner', 'writer', 'reader']:
                    logger.info(f"Skipping calendar {calendar_name} due to insufficient access rights: {access_role}")
                    continue
                    
                logger.info(f"Fetching events from calendar: {calendar_name}")
                
                try:
                    # Get events with timeout
                    events_result = self.service.events().list(
                        calendarId=calendar_id,
                        timeMin=start,
                        timeMax=end,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                    logger.info(f"Found {len(events)} events in {calendar_name}")
                    
                    if not events:
                        logger.info(f"No events found in calendar {calendar_name} for the specified time period")
                        continue
                    
                    # Process events into a more usable format
                    for event in events:
                        try:
                            start = event['start'].get('dateTime', event['start'].get('date'))
                            end = event['end'].get('dateTime', event['end'].get('date'))
                            
                            processed_event = {
                                'title': event.get('summary', 'No Title'),
                                'start_time': start,
                                'end_time': end,
                                'description': event.get('description', ''),
                                'location': event.get('location', ''),
                                'attendees': [
                                    attendee['email'] 
                                    for attendee in event.get('attendees', [])
                                    if not attendee.get('self', False)  # Exclude self
                                ],
                                'calendar_id': calendar_id,
                                'calendar_name': calendar_name,
                                'event_id': event.get('id', ''),
                                'html_link': event.get('htmlLink', '')
                            }
                            all_events.append(processed_event)
                            logger.info(f"Added event: {processed_event['title']} from {calendar_name}")
                        except Exception as e:
                            logger.error(f"Error processing event in {calendar_name}: {str(e)}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error fetching events from calendar {calendar_name}: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue
            
            logger.info(f"\nTotal events found across all calendars: {len(all_events)}")
            return all_events
            
        except Exception as e:
            logger.error(f"Error getting events: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def get_recent_events(self):
        """Get events from yesterday and today"""
        try:
            yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            tomorrow = yesterday + timedelta(days=2)
            
            events = self.get_events(yesterday, tomorrow)
            if not events:
                return {
                    'status': 'error',
                    'message': 'Failed to fetch events'
                }
            
            # Group events by date
            days = {}
            for event in events:
                # Get date from start_time
                event_date = event['start_time'].split('T')[0]
                if event_date not in days:
                    days[event_date] = []
                days[event_date].append(event)
            
            # Convert to list and sort by date
            days_list = [
                {
                    'date': date,
                    'events': sorted(events, key=lambda x: x['start_time'])
                }
                for date, events in sorted(days.items())
            ]
            
            return {
                'status': 'success',
                'total_events': len(events),
                'days': days_list
            }
            
        except Exception as e:
            logger.error(f"Error getting recent events: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error getting recent events: {str(e)}'
            }

@calendar_bp.route('/api/calendar/events/recent', methods=['GET'])
def get_recent_events():
    """Get events from yesterday and today"""
    try:
        logger.info("Starting to fetch recent events")
        
        # Initialize calendar client
        calendar = GoogleCalendar()
        
        # Try to authenticate again if service is not initialized
        if not calendar.service:
            logger.info("Service not initialized, attempting to authenticate again")
            if not calendar.authenticate():
                logger.error("Failed to authenticate after OAuth flow")
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication failed after OAuth flow'
                }), 500
        
        # Get date range
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        logger.info(f"Fetching events between {yesterday} and {tomorrow}")
        
        # Get events
        events = calendar.get_events(yesterday, tomorrow)
        if events is None:
            logger.error("Failed to fetch events from calendar")
            # Try to authenticate one more time
            logger.info("Attempting to re-authenticate and fetch events")
            if calendar.authenticate():
                events = calendar.get_events(yesterday, tomorrow)
                if events is None:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to fetch events even after re-authentication'
                    }), 500
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to fetch events and re-authentication failed'
                }), 500
            
        # Group events by date
        events_by_date = {}
        for event in events:
            try:
                event_date = datetime.fromisoformat(event['start_time'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event)
            except Exception as e:
                logger.error(f"Error processing event date: {str(e)}")
                continue
        
        return jsonify({
            'status': 'success',
            'total_events': len(events),
            'days': [
                {
                    'date': date,
                    'events': day_events
                }
                for date, day_events in sorted(events_by_date.items())
            ]
        })
        
    except Exception as e:
        logger.error(f"Error in get_recent_events: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch events: {str(e)}'
        }), 500 