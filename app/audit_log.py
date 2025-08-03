import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'audit.log')
MAX_LINES = 1000

def write_log(message):
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"
    # Append the log entry
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    # Truncate if too many lines
    truncate_log()

def truncate_log():
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if len(lines) > MAX_LINES:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines[-MAX_LINES:])
    except Exception:
        pass
