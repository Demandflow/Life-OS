from flask import Flask
from flask_cors import CORS
from .things_integration import things_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(things_bp)
    
    return app 