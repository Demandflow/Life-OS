from flask import Flask
from .things_integration import things_bp
from .calendar_integration import calendar_bp
from .clickup_integration import clickup_bp

def create_app():
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(things_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(clickup_bp)
    
    return app 