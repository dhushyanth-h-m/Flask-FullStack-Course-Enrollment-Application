""" 
Edu platform 
main application factory for Flask application
"""

import os
from flask import Flask 
from flask_migrate import Migrate 

from app.extensions import db, login_manager, socketio
from app.config import Config 

def create_app (config_class = Config):
    # Factory pattern for creating app instancce
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Configure Flask-Migrate
    migrate = Migrate(app, db)

    # Config login manager 
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Register the blueprints 
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix = '/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.api import bp as api_bp 
    app.register_blueprint(api_bp, url_prefix = 'api/v1')

    # Register error handlers
    from app.main.routes import page_not_found, internal_error
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_error)


    # Shell context processor
    @app.shell_context_processor
    def make_shell_context():
        from app.models import User, Course, Quiz, Question, Enrollment
        return {
            'db': db,
            'User': User,
            'Course': Course,
            'Quiz': Quiz,
            'Question': Question,
            'Enrollment': Enrollment
        }
    
    return app 