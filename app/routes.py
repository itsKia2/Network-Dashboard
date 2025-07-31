from flask import Blueprint, render_template, jsonify, request, abort, redirect, url_for, session, g
from flask_socketio import emit
from flask import session as flask_session
from app import socketio
from app.models import Device, NetworkScan, Stats, User
from app.scanner import NetworkScanner
import threading
import time
from datetime import datetime
import paramiko
import winrm

# Store active sessions in memory (per user session)
terminal_sessions = {}
session_lock = threading.Lock()

main = Blueprint('main', __name__)

# --- User authentication setup ---
import os
@main.before_app_request
def require_login():
    allowed_routes = ['main.login', 'main.register', 'static']
    if request.endpoint not in allowed_routes and not session.get('logged_in'):
        return redirect(url_for('main.login'))

# --- Login/Register routes ---
@main.route('/login', methods=['GET', 'POST'])
def login():
    User.create_table()
    if not User.user_exists():
        return redirect(url_for('main.register'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.check_user(username, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('main.dashboard'))
        else:
            error = 'Invalid username or password. Please try again.'
    return render_template('login.html', error=error, mode='login')

@main.route('/register', methods=['GET', 'POST'])
def register():
    User.create_table()
    if User.user_exists():
        return redirect(url_for('main.login'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username and password:
            try:
                User.set_user(username, password)
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('main.dashboard'))
            except Exception as e:
                error = 'Registration failed. Username may already exist.'
        else:
            error = 'Please provide both username and password.'
    return render_template('login.html', error=error, mode='register')

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

# Global scanner instance
scanner = NetworkScanner()
scan_in_progress = False

@main.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@main.route('/devices')
def devices_page():
    """Devices list page"""
    return render_template('devices.html')

# Device details page
@main.route('/device/<mac_address>')
def device_details(mac_address):
    from app.models import Device
    # Find device by MAC address (case-insensitive)
    devices = Device.get_all()
    device = next((d for d in devices if d.get('mac_address', '').lower() == mac_address.lower()), None)
    if not device:
        abort(404)
    return render_template('device_details.html', device=device)

# Sends command through ssh to remote device
@socketio.on('run_command')
def handle_run_command(data):
    print(f"[DEBUG] Received run_command: {data}")
    ip = data.get('ip')
    username = data.get('username')
    password = data.get('password')
    command = data.get('command')
    os_type = data.get('os', '').lower()

    if not all([ip, username, password, command]):
        print(f"[DEBUG] Missing required fields: ip={ip}, username={username}, password={'***' if password else None}, command={command}")
        emit('command_error', {'error': 'Missing required fields'})
        return

    print(f"[SSH] Attempting to run command '{command}' on {ip} as {username} (os_type={os_type})")

    if os_type == 'windows':
        # Windows (WinRM) --> TODO requires testing
        try:
            print(f"[SSH] Connecting to WinRM at {ip}")
            session = winrm.Session(f'http://{ip}:5985/wsman', auth=(username, password))
            r = session.run_cmd(command)
            print(f"[SSH] WinRM status_code: {r.status_code}")
            print(f"[SSH] WinRM stdout: {r.std_out}")
            print(f"[SSH] WinRM stderr: {r.std_err}")
            if r.status_code == 0:
                output = r.std_out.decode()
                print(f"[COMMAND OUTPUT] {output}")
                emit('command_output', {'output': output})
            else:
                error = r.std_err.decode()
                print(f"[COMMAND ERROR] {error}")
                emit('command_error', {'error': error})
        except Exception as e:
            print(f"[SSH] WinRM Exception: {e}")
            emit('command_error', {'error': str(e)})
        emit('command_done', {})
    else:
        # For linux devices (android not tested yet, but probably works with open port)
        try:
            print(f"[SSH] Connecting to SSH at {ip}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password, timeout=10)
            print(f"[SSH] Connected. Executing command: {command}")
            stdin, stdout, stderr = ssh.exec_command(command)
            # Stream output in real time
            for line in iter(stdout.readline, ""):
                if not line:
                    break
                print(f"[COMMAND OUTPUT] {line.rstrip()}")
                emit('command_output', {'output': line}, namespace='/')
            err = stderr.read().decode()
            if err:
                print(f"[COMMAND ERROR] {err}")
                emit('command_error', {'error': err})
            ssh.close()
        except Exception as e:
            print(f"[SSH] SSH Exception: {e}")
            emit('command_error', {'error': str(e)})
        emit('command_done', {})

@main.route('/api/devices')
def get_devices():
    """API endpoint to get all devices"""
    try:
        devices = Device.get_all()
        return jsonify({
            'success': True,
            'devices': devices,
            'total': len(devices)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main.route('/api/devices/active')
def get_active_devices():
    """API endpoint to get active devices"""
    try:
        hours = request.args.get('hours', 1, type=int)
        devices = Device.get_active(hours=hours)
        return jsonify({
            'success': True,
            'devices': devices,
            'total': len(devices)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_session_id():
    # Use Flask session id or username as key
    return flask_session.get('username') or str(id(flask_session))

@socketio.on('terminal_connect')
def handle_terminal_connect(data):
    sid = get_session_id()
    ip = data.get('ip')
    username = data.get('username')
    password = data.get('password')
    os_type = data.get('os', '').lower()
    with session_lock:
        if sid in terminal_sessions:
            # Clean up any previous session
            try:
                s = terminal_sessions[sid]
                if hasattr(s, 'close'):
                    s.close()
            except Exception:
                pass
            terminal_sessions.pop(sid, None)
        try:
            if os_type == 'windows':
                session = winrm.Session(f'http://{ip}:5985/wsman', auth=(username, password))
                # Test connection
                r = session.run_cmd('echo connected')
                if r.status_code == 0:
                    terminal_sessions[sid] = session
                    emit('terminal_connected', {'output': r.std_out.decode()})
                else:
                    emit('terminal_error', {'error': r.std_err.decode()})
            else:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, username=username, password=password, timeout=10)
                terminal_sessions[sid] = ssh
                emit('terminal_connected', {'output': '[SSH Connected]\n'})
        except Exception as e:
            emit('terminal_error', {'error': str(e)})

@socketio.on('terminal_command')
def handle_terminal_command(data):
    sid = get_session_id()
    command = data.get('command')
    os_type = data.get('os', '').lower()
    with session_lock:
        session_obj = terminal_sessions.get(sid)
        if not session_obj:
            emit('terminal_error', {'error': 'No active terminal session'})
            return
        try:
            if os_type == 'windows':
                r = session_obj.run_cmd(command)
                if r.status_code == 0:
                    emit('terminal_output', {'output': r.std_out.decode()})
                else:
                    emit('terminal_error', {'error': r.std_err.decode()})
            else:
                stdin, stdout, stderr = session_obj.exec_command(command)
                for line in iter(stdout.readline, ""):
                    if not line:
                        break
                    emit('terminal_output', {'output': line})
                err = stderr.read().decode()
                if err:
                    emit('terminal_error', {'error': err})
        except Exception as e:
            emit('terminal_error', {'error': str(e)})

@socketio.on('terminal_disconnect')
def handle_terminal_disconnect(data):
    sid = get_session_id()
    with session_lock:
        session_obj = terminal_sessions.pop(sid, None)
        if session_obj:
            try:
                if hasattr(session_obj, 'close'):
                    session_obj.close()
            except Exception:
                pass
    emit('terminal_disconnected', {'output': '[Session closed]'})

@main.route('/api/stats')
def get_stats():
    """API endpoint to get dashboard statistics"""
    try:
        stats = Stats.get_dashboard_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main.route('/api/scan', methods=['POST'])
def trigger_scan():
    """API endpoint to trigger network scan"""
    global scan_in_progress

    if scan_in_progress:
        return jsonify({
            'success': False,
            'error': 'Scan already in progress'
        }), 400

    # Start scan in background thread
    scan_thread = threading.Thread(target=perform_network_scan)
    scan_thread.daemon = True
    scan_thread.start()

    return jsonify({
        'success': True,
        'message': 'Network scan started'
    })

@main.route('/api/scan/status')
def scan_status():
    """API endpoint to get scan status"""
    recent_scans = NetworkScan.get_recent_scans(limit=5)
    return jsonify({
        'success': True,
        'scan_in_progress': scan_in_progress,
        'recent_scans': recent_scans
    })

from app.app_ctx import app
def perform_network_scan():
    """Perform network scan and update database"""
    global scan_in_progress
    scan_in_progress = True

    try:
        with app.app_context():
            # Set all devices to inactive before scan
            from app.models import DatabaseManager
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE devices SET is_active = 0")
            conn.commit()
            conn.close()

            # Emit scan started event
            socketio.emit('scan_started', {'message': 'Network scan started'})

            # Perform the scan
            devices_found, scan_duration = scanner.full_scan()

            # Update database and mark found devices as active
            for device_data in devices_found:
                # Normalize keys for DB
                if 'ip' in device_data:
                    device_data['ip_address'] = device_data['ip']
                if 'mac' in device_data:
                    device_data['mac_address'] = device_data['mac']
                device_data['is_active'] = 1
                Device.upsert(device_data)

            # Log the scan
            NetworkScan.log_scan(len(devices_found), scan_duration, 'full_scan')

            # Emit scan completed event
            socketio.emit('scan_completed', {
                'message': 'Network scan completed',
                'devices_found': len(devices_found),
                'duration': scan_duration
            })

            print(f"Network scan completed: {len(devices_found)} devices found in {scan_duration:.2f} seconds")

    except Exception as e:
        print(f"Scan error: {e}")
        socketio.emit('scan_error', {'error': str(e)})

    finally:
        scan_in_progress = False

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connected', {'message': 'Connected to network dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

@socketio.on('request_device_update')
def handle_device_update():
    """Handle request for device updates"""
    try:
        devices = Device.get_all()
        stats = Stats.get_dashboard_stats()
        emit('device_update', {
            'devices': devices,
            'stats': stats
        })
    except Exception as e:
        emit('error', {'message': str(e)})

# Auto-scan functionality (runs every 5 minutes)
def auto_scan():
    """Automatic network scanning"""
    while True:
        time.sleep(300)  # 5 minutes
        if not scan_in_progress:
            print("Starting automatic network scan...")
            perform_network_scan()

# Start auto-scan thread when module loads (global)
auto_scan_thread = threading.Thread(target=auto_scan)
auto_scan_thread.daemon = True
auto_scan_thread.start()
