# Life OS

A personal productivity system that integrates with Things 3 to manage tasks and track progress.

## Features

- Get tasks from Things 3 Today view
- Track completed tasks from yesterday and today
- Group tasks by areas and projects
- Maintain task order from Things 3

## Setup

1. Install dependencies:
```bash
pip3 install flask things
```

2. Start the server:
```bash
python3 -m flask --app backend/app/__init__.py run --port 5004
```

## API Endpoints

- `/api/tasks/today` - Get current tasks in Today view
- `/api/tasks/yesterday/completed` - Get tasks completed yesterday
- `/api/tasks/completed/recent` - Get tasks completed since yesterday (including today)
- `/api/tasks/today/save_snapshot` - Save current Today view state

## Requirements

- Python 3.x
- Things 3 app
- macOS (required for Things 3) 