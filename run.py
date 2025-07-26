import eventlet
eventlet.monkey_patch()

import os
from app import create_app, socketio
app = create_app()

if __name__ == '__main__':
    # Initialize database if it doesn't exist
    if not os.path.exists('data/network.db'):
        from database.init_db import init_database
        init_database()

    # Run the application
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
