import os
import psutil
from dotenv import load_dotenv
import time
from datetime import datetime
import logging
import getpass
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

# Environment variables for OAuth
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# SCOPES define the permissions for Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Setup logging
logging.basicConfig(filename='vscode_usage_and_process.log',
                    level=logging.DEBUG,
                    format='%(asctime)s - %(message)s',
                    filemode='a')  # Log appends to the existing file
logger = logging.getLogger(__name__)

# Get the current user's username
current_user = getpass.getuser()

# Function to get VSCode process
def get_vscode_process():
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if 'code helper' in proc.info['name'].lower():
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None


def load_client_config():
    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "project_id": "your_project_id",  # Replace this with your project ID
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": CLIENT_SECRET,
            "redirect_uris": ["http://localhost"]
        }
    }
    return client_config

def get_credentials():
    creds = None
    # Load token.json if it exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_config(load_client_config(), SCOPES)
        creds = flow.run_local_server(port=0)

        # Save the credentials for the future
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def create_event(start_time, end_time):
    creds = get_credentials()

    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': 'VSCode Coding Session',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Jerusalem',  # Change to your timezone
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Asia/Jerusalem',  # Change to your timezone
        }
    }

    try:
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Event created: {event_result.get('htmlLink')}")
    except Exception as e:
        logger.error(f"Failed to create event: {e}")

def track_application_close():
    vscode_process = None
    open_time = None

    try:
        while True:
            current_vscode_process = get_vscode_process()
            if current_vscode_process:
                if not vscode_process:
                    # New VSCode process detected, start timing
                    vscode_process = current_vscode_process
                    open_time = datetime.now()
                    logger.info(f"VSCode opened at {open_time}")
                    print(f"VScode opened, time: {open_time}")
            else:
                if vscode_process:
                    # VSCode just closed
                    close_time = datetime.now()
                    if open_time:
                        usage_time = close_time - open_time
                        logger.info(f"VSCode closed at {close_time}, Total time open: {usage_time}")
                        print(f"VScode closed, close time: {close_time}")
                        # Create an event in Google Calendar
                        create_event(open_time, close_time)
                    else:
                        logger.warning("VSCode closed but open_time is not set.")
                    vscode_process = None  # Reset the process tracker
            time.sleep(5)  # Check every 5 seconds to reduce CPU usage
    except KeyboardInterrupt:
        logger.info("Tracking closed applications stopped.")

if __name__ == "__main__":
    track_application_close()
