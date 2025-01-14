import logging
from flask import Blueprint, jsonify, Response
import things
import sys
from datetime import datetime, timedelta
import json
import os

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

things_bp = Blueprint('things', __name__)

@things_bp.route('/')
def root():
    """Root endpoint showing available routes"""
    return jsonify({
        "status": "API is running",
        "available_endpoints": [
            "/api/test - Test if API is working",
            "/api/tasks/today - Get today's tasks from Things 3",
            "/api/tasks/yesterday/completed - Get yesterday's completed tasks"
        ]
    })

@things_bp.route('/api/test')
def test_endpoint():
    """Simple test endpoint to verify the API is responding"""
    return jsonify({"status": "API is working"})

class ThingsDB:
    def __init__(self):
        logger.info("Initializing ThingsDB")
        try:
            # Test Things connection immediately
            things.todos()
            logger.info("Successfully connected to Things 3")
            self.snapshot_file = 'today_tasks_snapshot.json'
        except Exception as e:
            logger.error(f"Failed to connect to Things 3: {str(e)}")
    
    def save_today_snapshot(self, task_ids):
        """Save a snapshot of task IDs that are in Today view"""
        snapshot = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'task_ids': task_ids
        }
        with open(self.snapshot_file, 'w') as f:
            json.dump(snapshot, f)
        logger.info(f"Saved snapshot with {len(task_ids)} tasks")
    
    def load_today_snapshot(self):
        """Load the most recent snapshot of Today tasks"""
        try:
            if os.path.exists(self.snapshot_file):
                with open(self.snapshot_file, 'r') as f:
                    snapshot = json.load(f)
                logger.info(f"Loaded snapshot from {snapshot['date']}")
                return snapshot['task_ids']
        except Exception as e:
            logger.error(f"Error loading snapshot: {str(e)}")
        return None

    def get_today_tasks(self):
        try:
            all_tasks = things.todos()
            logger.info(f"Retrieved {len(all_tasks)} total tasks from Things 3")
            
            areas = {}
            today_tasks = []
            today = datetime.now().strftime('%Y-%m-%d')
            
            for task in all_tasks:
                if task.get('status') == 'completed':
                    continue
                    
                # Get key fields that determine if a task is in Today view
                start = task.get('start', '')
                start_date = task.get('start_date')
                today_index = task.get('today_index', 0)
                
                # A task is in Today view if:
                # 1. It's explicitly set to start Today, or
                # 2. It has today's date as start date, or
                # 3. It's in Anytime and has been moved to Today (positive today_index)
                if (start == 'Today' or 
                    start_date == today or 
                    (start == 'Anytime' and today_index > 0)):
                    today_tasks.append(task)
                    logger.info(f"\nIncluding task in Today view: {task.get('title')}")
                    logger.info(f"  start: {start}")
                    logger.info(f"  start_date: {start_date}")
                    logger.info(f"  today_index: {today_index}")

            # Sort tasks by today_index to maintain Things 3 order
            today_tasks.sort(key=lambda x: x.get('today_index', 0))
            logger.info(f"\nAfter filtering: Found {len(today_tasks)} tasks for Today view")

            # Group tasks by area
            for task in today_tasks:
                area_title = task.get('area_title', '')
                if not area_title:
                    area_title = task.get('project_title', 'No Area')
                
                # Create task info
                task_info = {
                    'title': task.get('title', ''),
                    'status': task.get('status', ''),
                    'notes': task.get('notes', ''),
                    'project_title': task.get('project_title', ''),
                    'today_index': task.get('today_index', 0),
                    'start_date': task.get('start_date'),
                    'deadline': task.get('deadline')
                }
                
                # Initialize area if not exists
                if area_title not in areas:
                    areas[area_title] = []
                areas[area_title].append(task_info)

            return {
                "status": "success",
                "message": f"Found {len(today_tasks)} tasks in Today view",
                "areas": areas
            }

        except Exception as e:
            logger.error(f"Error getting tasks from Things 3: {str(e)}")
            return {'status': 'error', 'error': f'Error getting tasks from Things 3: {str(e)}'}

    def get_yesterday_completed_tasks(self):
        try:
            logger.info("Getting yesterday's completed tasks")
            yesterday = datetime.now() - timedelta(days=1)
            yesterday_str = yesterday.strftime('%Y-%m-%d')
            
            # Use logbook() instead of todos() to get completed tasks
            completed_tasks = things.logbook()
            
            # Log all tasks with completion dates for debugging
            for task in completed_tasks:
                logger.info(f"Found completed task: {task.get('title')} - Stop Date: {task.get('stop_date')} - Status: {task.get('status')}")
            
            yesterday_tasks = [
                task for task in completed_tasks 
                if task.get('stop_date', '').startswith(yesterday_str)
            ]
            
            logger.info(f"Found {len(yesterday_tasks)} tasks completed yesterday")
            if yesterday_tasks:
                logger.info(f"Sample completed task: {yesterday_tasks[0]}")
            
            # Group tasks by project/area
            projects = {}
            for task in yesterday_tasks:
                # Try to get area first, then project, then default
                project_name = task.get('area_title') or task.get('project_title') or 'No Project'
                    
                if project_name not in projects:
                    projects[project_name] = []
                    
                task_info = {
                    'title': task.get('title', 'No Title'),
                    'notes': task.get('notes', ''),
                    'completed_time': task.get('stop_date', ''),
                    'tags': task.get('tags', [])
                }
                projects[project_name].append(task_info)
                logger.info(f"Added completed task: {task_info['title']} to project: {project_name}")
            
            # Convert to list and sort by project name
            projects_list = [
                {'name': name, 'tasks': tasks}
                for name, tasks in sorted(projects.items())
            ]
            
            return {
                'status': 'success',
                'date': yesterday_str,
                'total_completed': len(yesterday_tasks),
                'projects': projects_list
            }
        except Exception as e:
            logger.error(f"Error getting completed tasks: {str(e)}")
            return {'status': 'error', 'message': f'Error getting completed tasks: {str(e)}'}

    def get_recent_completed_tasks(self):
        """Get tasks completed since yesterday (including today)"""
        try:
            logger.info("Getting tasks completed since yesterday")
            yesterday = datetime.now() - timedelta(days=1)
            yesterday_str = yesterday.strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            
            completed_tasks = things.logbook()
            
            # Get tasks completed yesterday or today
            recent_tasks = [
                task for task in completed_tasks 
                if task.get('stop_date', '').startswith(yesterday_str) or 
                   task.get('stop_date', '').startswith(today)
            ]
            
            logger.info(f"Found {len(recent_tasks)} tasks completed since yesterday")
            
            # Group tasks by completion date, then by project/area
            days = {}
            for task in recent_tasks:
                stop_date = task.get('stop_date', '').split()[0]  # Get just the date part
                if stop_date not in days:
                    days[stop_date] = {}
                
                # Get project or area name
                project_name = task.get('area_title') or task.get('project_title') or 'No Project'
                if project_name not in days[stop_date]:
                    days[stop_date][project_name] = []
                
                task_info = {
                    'title': task.get('title', 'No Title'),
                    'notes': task.get('notes', ''),
                    'completed_time': task.get('stop_date', ''),
                    'tags': task.get('tags', [])
                }
                days[stop_date][project_name].append(task_info)
                logger.info(f"Added task: {task_info['title']} to {project_name} on {stop_date}")
            
            # Convert the nested dict to a more organized structure
            days_list = []
            for date in sorted(days.keys(), reverse=True):  # Most recent first
                projects_list = [
                    {'name': name, 'tasks': tasks}
                    for name, tasks in sorted(days[date].items())
                ]
                days_list.append({
                    'date': date,
                    'total_completed': sum(len(p['tasks']) for p in projects_list),
                    'projects': projects_list
                })
            
            return {
                'status': 'success',
                'total_completed': len(recent_tasks),
                'days': days_list
            }
            
        except Exception as e:
            logger.error(f"Error getting completed tasks: {str(e)}")
            return {'status': 'error', 'message': f'Error getting completed tasks: {str(e)}'}

@things_bp.route('/api/tasks/today')
def get_today_tasks():
    """Endpoint to get today's tasks from Things 3"""
    try:
        logger.info("API endpoint /api/tasks/today called")
        db = ThingsDB()
        result = db.get_today_tasks()
        logger.info(f"API result: {result}")
        
        # Ensure we always return a response
        if result is None:
            logger.error("get_today_tasks returned None")
            return jsonify({
                "status": "error",
                "message": "No response from Things 3 integration"
            }), 500
            
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": str(sys.exc_info())
        }), 500 

@things_bp.route('/api/tasks/yesterday/completed')
def get_yesterday_completed():
    """Endpoint to get yesterday's completed tasks"""
    try:
        logger.info("API endpoint /api/tasks/yesterday/completed called")
        db = ThingsDB()
        result = db.get_yesterday_completed_tasks()
        logger.info(f"API result: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": str(sys.exc_info())
        }), 500 

@things_bp.route('/api/tasks/today/save_snapshot', methods=['POST'])
def save_snapshot():
    """Endpoint to save current Today tasks as a snapshot"""
    try:
        logger.info("API endpoint /api/tasks/today/save_snapshot called")
        db = ThingsDB()
        all_tasks = things.todos()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get IDs of tasks that are in Today view
        task_ids = []
        for task in all_tasks:
            if task.get('status') != 'completed':
                # Debug: Print ALL task properties
                title = task.get('title', '')
                logger.info(f"\n=== Analyzing task: {title} ===")
                for key, value in task.items():
                    logger.info(f"  {key}: {value}")
                
                # For now, include all non-completed tasks to see what we get
                task_ids.append(task['uuid'])
                logger.info("  -> Including task for analysis")
        
        db.save_today_snapshot(task_ids)
        return jsonify({
            "status": "success",
            "message": f"Saved snapshot with {len(task_ids)} tasks"
        })
        
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": str(sys.exc_info())
        }), 500 

@things_bp.route('/api/tasks/completed/recent')
def get_recent_completed():
    """Endpoint to get tasks completed since yesterday (including today)"""
    try:
        logger.info("API endpoint /api/tasks/completed/recent called")
        db = ThingsDB()
        result = db.get_recent_completed_tasks()
        logger.info(f"API result: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in API endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": str(sys.exc_info())
        }), 500 