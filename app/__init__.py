from flask import Flask
from flask_socketio import SocketIO
import os

socketio = SocketIO()

def create_app():
    app = Flask(
        __name__,
        static_folder='../static',
        template_folder='../templates'
    )
    app.config.from_object('config.Config')

    # Initialize SocketIO for real-time updates
    socketio.init_app(app, cors_allowed_origins="*")

    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)

    return app
