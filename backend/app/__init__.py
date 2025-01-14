from flask import Flask
from .things_integration import things_bp
from .calendar_integration import calendar_bp

def create_app():
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(things_bp)
    app.register_blueprint(calendar_bp)
    
    return app 