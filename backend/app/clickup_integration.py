import os
import logging
import requests
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
clickup_bp = Blueprint('clickup', __name__, url_prefix='/api/clickup')

class ClickUpClient:
    def __init__(self):
        """Initialize the ClickUp client with API key from environment variables."""
        self.api_key = os.getenv('CLICKUP_API_KEY')
        if not self.api_key:
            logger.error("No ClickUp API key found in environment variables")
            raise ValueError("CLICKUP_API_KEY environment variable is not set")
            
        self.base_url = "https://api.clickup.com/api/v2"
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        self.requests_this_minute = 0
        self.minute_start = time.time()
        
        logger.info("Initializing ClickUp client...")
        
        # Test the API key with a simple request
        test_response = requests.get(f"{self.base_url}/team", headers=self.headers)
        if test_response.status_code != 200:
            logger.error(f"API key test failed. Status code: {test_response.status_code}")
            raise ValueError("Invalid API key or API access denied")
            
        # Get workspace ID from the test response
        try:
            data = test_response.json()
            teams = data.get('teams', [])
            if not teams:
                raise ValueError("No workspaces found")
                
            self.workspace_id = teams[0]['id']
            logger.info(f"ClickUp client initialized with workspace ID: {self.workspace_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ClickUp client: {str(e)}")
            raise ValueError(f"Failed to initialize ClickUp client: {str(e)}")

    def _make_request(self, method, url, **kwargs):
        """Make a request to the ClickUp API with rate limiting."""
        current_time = time.time()
        if current_time - self.minute_start >= 60:
            self.requests_this_minute = 0
            self.minute_start = current_time
        elif self.requests_this_minute >= 95:
            wait_time = 60 - (current_time - self.minute_start)
            logger.info(f"Rate limit approaching. Waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)
            self.requests_this_minute = 0
            self.minute_start = time.time()

        response = requests.request(method, url, headers=self.headers, **kwargs)
        self.requests_this_minute += 1
        return response

    def get_spaces(self, workspace_id):
        """Get all spaces in a workspace"""
        try:
            logger.info(f"Fetching spaces for workspace {workspace_id}")
            response = self._make_request("GET", f"{self.base_url}/team/{workspace_id}/space")
            response.raise_for_status()
            spaces = response.json().get('spaces', [])
            logger.info(f"Found {len(spaces)} spaces")
            return spaces
        except Exception as e:
            logger.error(f"Error getting spaces: {str(e)}")
            return []

    def get_folders(self, space_id):
        """Get all folders in a space."""
        try:
            url = f"{self.base_url}/space/{space_id}/folder"
            response = self._make_request("GET", url)
            if response.status_code == 200:
                folders = response.json()["folders"]
                logger.info(f"Found {len(folders)} folders in space {space_id}")
                return folders
            return []
        except Exception as e:
            logger.error(f"Error getting folders: {str(e)}")
            return []

    def get_lists_in_folder(self, folder_id):
        """Get all lists in a folder."""
        try:
            url = f"{self.base_url}/folder/{folder_id}/list"
            response = self._make_request("GET", url)
            if response.status_code == 200:
                lists = response.json()["lists"]
                logger.info(f"Found {len(lists)} lists in folder {folder_id}")
                return lists
            return []
        except Exception as e:
            logger.error(f"Error getting lists in folder: {str(e)}")
            return []

    def get_tasks(self, start_date=None, end_date=None):
        """Get tasks from ClickUp within the specified date range."""
        all_tasks = []
        try:
            spaces = self.get_spaces(self.workspace_id)
            for space in spaces:
                space_id = space.get('id')
                folders = self.get_folders(space_id)
                
                for folder in folders:
                    lists = self.get_lists_in_folder(folder['id'])
                    for list_data in lists:
                        tasks = self._get_tasks_from_list(list_data['id'], start_date, end_date)
                        all_tasks.extend(tasks)
            
            return all_tasks
        except Exception as e:
            logger.error(f"Error getting tasks: {str(e)}")
            return []

    def _get_tasks_from_list(self, list_id, start_date=None, end_date=None):
        """Helper method to get tasks from a specific list."""
        tasks = []
        try:
            params = {
                'include_closed': 'true',
                'subtasks': 'true',
                'order_by': 'due_date'
            }
            
            response = self._make_request("GET", f"{self.base_url}/list/{list_id}/task", params=params)
            if response.status_code == 200:
                tasks_data = response.json().get('tasks', [])
                for task in tasks_data:
                    due_date_ms = task.get('due_date')
                    if not due_date_ms:
                        continue
                        
                    due_date = datetime.fromtimestamp(int(due_date_ms) / 1000)
                    if start_date and due_date < start_date:
                        continue
                    if end_date and due_date > end_date:
                        continue
                        
                    tasks.append(task)
            
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks from list: {str(e)}")
            return []

@clickup_bp.route('/tasks/recent', methods=['GET'])
def get_recent_tasks():
    """Get tasks from the past week and upcoming month."""
    try:
        clickup = ClickUpClient()
        today = datetime.now()
        start_date = today - timedelta(days=7)
        end_date = today + timedelta(days=30)
        
        tasks = clickup.get_tasks(start_date, end_date)
        
        if not tasks:
            return jsonify({
                'status': 'success',
                'total_tasks': 0,
                'days': []
            })
        
        # Group tasks by date
        days_dict = {}
        for task in tasks:
            due_date = task.get('due_date')
            if not due_date:
                continue
            
            date_key = datetime.fromtimestamp(int(due_date) / 1000).strftime('%Y-%m-%d')
            if date_key not in days_dict:
                days_dict[date_key] = []
            days_dict[date_key].append(task)
        
        # Convert to sorted list of days
        days_list = [
            {
                'date': date,
                'tasks': sorted(tasks, key=lambda x: x.get('due_date', ''))
            }
            for date, tasks in sorted(days_dict.items())
        ]
        
        return jsonify({
            'status': 'success',
            'total_tasks': len(tasks),
            'days': days_list
        })
        
    except Exception as e:
        logger.error(f"Error in get_recent_tasks: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@clickup_bp.route('/spaces/folders', methods=['GET'])
def get_space_folders():
    """Get all folders and their lists for each space."""
    try:
        clickup = ClickUpClient()
        spaces = clickup.get_spaces(clickup.workspace_id)
        result = []
        
        for space in spaces:
            space_data = {
                "space_id": space["id"],
                "name": space["name"],
                "folders": []
            }
            
            folders = clickup.get_folders(space["id"])
            for folder in folders:
                folder_data = {
                    "folder_id": folder["id"],
                    "name": folder["name"],
                    "lists": []
                }
                
                lists = clickup.get_lists_in_folder(folder["id"])
                folder_data["lists"] = [{
                    "list_id": lst["id"],
                    "name": lst["name"],
                    "task_count": lst.get("task_count", 0)
                } for lst in lists]
                
                space_data["folders"].append(folder_data)
            
            result.append(space_data)
        
        return jsonify({"status": "success", "spaces": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500 