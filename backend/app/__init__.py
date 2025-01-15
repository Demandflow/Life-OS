from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///life_os.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    
    # Import and register blueprints
    from .routes import main_bp
    from .clickup_integration import clickup_bp
    from .weather_integration import weather_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(clickup_bp)
    app.register_blueprint(weather_bp)
    
    return app 