# Life OS

A personal productivity system that integrates with various tools and services.

## Current Integrations

- Things 3 (Tasks)
- Google Calendar (Events)

## Setup

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. Set up Google Calendar integration:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download the credentials and save as `credentials.json` in the project root

3. Start the server:
```bash
python3 -m flask --app backend/app/__init__.py run --port 5004
```

## API Endpoints

### Tasks (Things 3)

- `GET /api/tasks/today`: Get all tasks in Today view

### Calendar (Google Calendar)

- `GET /api/calendar/events/recent`: Get events from yesterday and today

## Development

- The server runs in debug mode by default
- First request to calendar endpoints will trigger Google OAuth flow
- Credentials are cached in `token.pickle` 