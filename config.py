import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'network.db')
    SCAN_INTERVAL = 10 
    NETWORK_RANGE = '192.168.1.0/24'  # Adjust for your network
    DEBUG = True
    MAX_PING_THREADS = 50
    ARP_TIMEOUT = 2
    PORT_SCAN_TIMEOUT = 1
