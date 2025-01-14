import os
import logging
import requests
from datetime import datetime, timedelta
from flask import Blueprint, jsonify

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
clickup_bp = Blueprint('clickup', __name__)

class ClickUpClient:
    def __init__(self):
        logger.info("Initializing ClickUp integration")
        self.api_key = os.getenv('CLICKUP_API_KEY')
        self.base_url = 'https://api.clickup.com/api/v2'
        self.headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        
    def get_workspaces(self):
        """Get all workspaces"""
        try:
            response = requests.get(
                f"{self.base_url}/team",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get('teams', [])
        except Exception as e:
            logger.error(f"Error getting workspaces: {str(e)}")
            return None
            
    def get_spaces(self, workspace_id):
        """Get all spaces in a workspace"""
        try:
            response = requests.get(
                f"{self.base_url}/team/{workspace_id}/space",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get('spaces', [])
        except Exception as e:
            logger.error(f"Error getting spaces for workspace {workspace_id}: {str(e)}")
            return None
            
    def get_lists(self, space_id):
        """Get all lists in a space"""
        try:
            response = requests.get(
                f"{self.base_url}/space/{space_id}/list",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get('lists', [])
        except Exception as e:
            logger.error(f"Error getting lists for space {space_id}: {str(e)}")
            return None
            
    def get_tasks(self, list_id, start_date=None, end_date=None):
        """Get tasks from a list with optional date filtering"""
        try:
            params = {
                'include_closed': True,
                'subtasks': True,
                'order_by': 'due_date'
            }
            
            if start_date:
                params['due_date_gt'] = int(start_date.timestamp() * 1000)
            if end_date:
                params['due_date_lt'] = int(end_date.timestamp() * 1000)
                
            response = requests.get(
                f"{self.base_url}/list/{list_id}/task",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json().get('tasks', [])
        except Exception as e:
            logger.error(f"Error getting tasks for list {list_id}: {str(e)}")
            return None

# Initialize ClickUp client
clickup = ClickUpClient()

@clickup_bp.route('/api/clickup/tasks/recent', methods=['GET'])
def get_recent_tasks():
    """Get tasks from the past day and upcoming day"""
    try:
        # Get date range
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        # Get all workspaces
        workspaces = clickup.get_workspaces()
        if not workspaces:
            return jsonify({
                'status': 'error',
                'message': 'No workspaces found'
            }), 404
            
        all_tasks = []
        for workspace in workspaces:
            workspace_id = workspace['id']
            workspace_name = workspace['name']
            
            # Get spaces in workspace
            spaces = clickup.get_spaces(workspace_id)
            if not spaces:
                continue
                
            for space in spaces:
                space_id = space['id']
                space_name = space['name']
                
                # Get lists in space
                lists = clickup.get_lists(space_id)
                if not lists:
                    continue
                    
                for list_item in lists:
                    list_id = list_item['id']
                    list_name = list_item['name']
                    
                    # Get tasks in list
                    tasks = clickup.get_tasks(list_id, yesterday, tomorrow)
                    if not tasks:
                        continue
                        
                    # Process tasks
                    for task in tasks:
                        processed_task = {
                            'id': task['id'],
                            'name': task['name'],
                            'description': task.get('description', ''),
                            'status': task['status']['status'],
                            'priority': task.get('priority', {}).get('priority', 'none'),
                            'due_date': task.get('due_date'),
                            'url': task.get('url', ''),
                            'workspace_name': workspace_name,
                            'space_name': space_name,
                            'list_name': list_name,
                            'assignees': [
                                assignee['username'] 
                                for assignee in task.get('assignees', [])
                            ],
                            'tags': [
                                tag['name'] 
                                for tag in task.get('tags', [])
                            ]
                        }
                        all_tasks.append(processed_task)
        
        # Group tasks by date
        tasks_by_date = {}
        for task in all_tasks:
            if task['due_date']:
                due_date = datetime.fromtimestamp(task['due_date']/1000).strftime('%Y-%m-%d')
                if due_date not in tasks_by_date:
                    tasks_by_date[due_date] = []
                tasks_by_date[due_date].append(task)
        
        return jsonify({
            'status': 'success',
            'total_tasks': len(all_tasks),
            'days': [
                {
                    'date': date,
                    'tasks': tasks
                }
                for date, tasks in sorted(tasks_by_date.items())
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting recent tasks: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 