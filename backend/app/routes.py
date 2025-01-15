import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from .models import db, Reflection, Image
from .things_integration import ThingsDB
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
main_bp = Blueprint('main', __name__, url_prefix='/api')

@main_bp.route('/')
def test_server():
    return jsonify({'message': 'Server is running!'}), 200

@main_bp.route('/reflection', methods=['POST'])
def create_reflection():
    data = request.json
    reflection = Reflection(
        type=data.get('type'),
        priorities=data.get('priorities'),
        intention=data.get('intention'),
        reflection=data.get('reflection'),
        challenges=data.get('challenges'),
        tomorrow=data.get('tomorrow')
    )
    db.session.add(reflection)
    db.session.commit()
    return jsonify({'id': reflection.id}), 201

@main_bp.route('/reflection/<date>/<type>', methods=['GET'])
def get_reflection(date, type):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        reflection = Reflection.query.filter(
            db.func.date(Reflection.date) == date_obj.date(),
            Reflection.type == type
        ).first()
        
        if not reflection:
            return jsonify({'error': 'Reflection not found'}), 404
            
        return jsonify({
            'id': reflection.id,
            'type': reflection.type,
            'priorities': reflection.priorities,
            'intention': reflection.intention,
            'reflection': reflection.reflection,
            'challenges': reflection.challenges,
            'tomorrow': reflection.tomorrow,
            'images': [{'id': img.id, 'path': img.path} for img in reflection.images]
        })
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

@main_bp.route('/reflection/weekly', methods=['GET'])
def get_weekly_summary():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    reflections = Reflection.query.filter(
        Reflection.date.between(start_date, end_date)
    ).all()
    
    return jsonify([{
        'id': r.id,
        'date': r.date.strftime('%Y-%m-%d'),
        'type': r.type,
        'priorities': r.priorities,
        'reflection': r.reflection
    } for r in reflections]) 

@main_bp.route('/tasks/today', methods=['GET'])
def get_today_tasks():
    things = ThingsDB()
    try:
        tasks = things.get_today_tasks()
        return jsonify(tasks)
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Error accessing Things 3: {str(e)}'}), 500

@main_bp.route('/tasks/upcoming', methods=['GET'])
def get_upcoming_tasks():
    days = request.args.get('days', default=7, type=int)
    things = ThingsDB()
    try:
        tasks = things.get_upcoming_tasks(days)
        return jsonify(tasks)
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Error accessing Things 3: {str(e)}'}), 500 

@main_bp.route('/tasks/test', methods=['GET'])
def test_things_connection():
    things = ThingsDB()
    try:
        if things.test_connection():
            return jsonify({'status': 'success', 'message': 'Successfully connected to Things 3'})
        else:
            return jsonify({'status': 'error', 'message': 'Could not connect to Things 3'}), 500
    except FileNotFoundError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500 

@main_bp.route('/tasks/yesterday', methods=['GET'])
def get_yesterday_tasks():
    things = ThingsDB()
    try:
        tasks = things.get_yesterday_completed()
        return jsonify(tasks)
    except Exception as e:
        return jsonify({'error': f'Error accessing Things 3: {str(e)}'}), 500 

@main_bp.route('/overview/ceo', methods=['GET'])
def get_ceo_overview():
    """Get a high-level overview of tasks, events, and weather for CEO-level insights"""
    try:
        overview = {
            'attention_needed': {'count': 0, 'items': []},
            'high_priority': {'count': 0, 'items': []},
            'productivity': {'completed_yesterday': 0, 'planned_today': 0},
            'upcoming_meetings': {'count': 0, 'items': []},
            'weather': None
        }

        # Get Weather information
        try:
            from .weather_integration import WeatherClient
            weather = WeatherClient()
            overview['weather'] = weather.get_weather()
            logger.info("Weather data retrieved successfully")
        except Exception as e:
            logger.error(f"Error getting weather data: {str(e)}")

        # Get ClickUp tasks
        try:
            from .clickup_integration import ClickUpClient
            clickup = ClickUpClient()
            today = datetime.now()
            start_date = today - timedelta(days=1)  # Yesterday
            end_date = today + timedelta(days=7)    # Week ahead
            clickup_tasks = clickup.get_tasks(start_date, end_date)

            # Process ClickUp tasks for attention needed
            attention_needed = []
            high_priority_tasks = []
            for task in clickup_tasks:
                # Check for high priority tasks
                if task.get('priority') in ['urgent', 'high']:
                    high_priority_tasks.append({
                        'title': task['name'],
                        'due_date': task['due_date'],
                        'status': task['status'],
                        'url': task['url']
                    })
                
                # Check for tasks needing attention (overdue or blocked)
                if (task.get('status') == 'blocked' or 
                    (task.get('due_date') and task['due_date'] < today.isoformat())):
                    attention_needed.append({
                        'title': task['name'],
                        'reason': 'overdue' if task.get('due_date') else 'blocked',
                        'status': task['status'],
                        'url': task['url']
                    })

            overview['attention_needed'] = {
                'count': len(attention_needed),
                'items': attention_needed
            }
            overview['high_priority'] = {
                'count': len(high_priority_tasks),
                'items': high_priority_tasks
            }
            logger.info("ClickUp tasks retrieved successfully")
        except Exception as e:
            logger.error(f"Error getting ClickUp data: {str(e)}")

        # Get Things tasks
        try:
            things = ThingsDB()
            today_tasks = things.get_today_tasks()
            yesterday_completed = things.get_yesterday_completed_tasks()

            # Calculate productivity metrics
            tasks_completed_yesterday = len(yesterday_completed.get('projects', []))
            tasks_planned_today = sum(len(area) for area in today_tasks.get('areas', {}).values())
            
            overview['productivity'] = {
                'completed_yesterday': tasks_completed_yesterday,
                'planned_today': tasks_planned_today
            }
            logger.info("Things data retrieved successfully")
        except Exception as e:
            logger.error(f"Error getting Things data: {str(e)}")

        # Get Calendar events if available
        try:
            try:
                from .calendar_integration import get_calendar_client
                calendar = get_calendar_client()
                calendar_events = calendar.get_events(
                    start_time=(today - timedelta(days=1)).isoformat(),
                    end_time=(today + timedelta(days=7)).isoformat()
                )

                upcoming_meetings = []
                for event in calendar_events:
                    upcoming_meetings.append({
                        'title': event['summary'],
                        'start_time': event['start_time'],
                        'end_time': event['end_time'],
                        'attendees': event.get('attendees', [])
                    })

                overview['upcoming_meetings'] = {
                    'count': len(upcoming_meetings),
                    'items': upcoming_meetings
                }
                logger.info("Calendar events retrieved successfully")
            except ImportError:
                logger.warning("Calendar integration not available")
        except Exception as e:
            logger.error(f"Error getting calendar data: {str(e)}")
        
        return jsonify({
            'status': 'success',
            'overview': overview
        })

    except Exception as e:
        logger.error(f"Error generating CEO overview: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 