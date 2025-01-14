from flask import Blueprint, request, jsonify
from .models import db, Reflection, Image
from .things_integration import ThingsDB
from datetime import datetime, timedelta
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def test_server():
    return jsonify({'message': 'Server is running!'}), 200

@main_bp.route('/api/reflection', methods=['POST'])
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

@main_bp.route('/api/reflection/<date>/<type>', methods=['GET'])
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

@main_bp.route('/api/reflection/weekly', methods=['GET'])
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

@main_bp.route('/api/tasks/today', methods=['GET'])
def get_today_tasks():
    things = ThingsDB()
    try:
        tasks = things.get_today_tasks()
        return jsonify(tasks)
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Error accessing Things 3: {str(e)}'}), 500

@main_bp.route('/api/tasks/upcoming', methods=['GET'])
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

@main_bp.route('/api/tasks/test', methods=['GET'])
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

@main_bp.route('/api/tasks/yesterday', methods=['GET'])
def get_yesterday_tasks():
    things = ThingsDB()
    try:
        tasks = things.get_yesterday_completed()
        return jsonify(tasks)
    except Exception as e:
        return jsonify({'error': f'Error accessing Things 3: {str(e)}'}), 500 