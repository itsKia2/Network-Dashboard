from flask import Blueprint, render_template, jsonify, request
from flask_socketio import emit
from app import socketio
from app.models import Device, NetworkScan, Stats
from app.scanner import NetworkScanner
import threading
import time
from datetime import datetime

main = Blueprint('main', __name__)

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
            # Emit scan started event
            socketio.emit('scan_started', {'message': 'Network scan started'})

            # Perform the scan
            devices_found, scan_duration = scanner.full_scan()

            # Update database
            for device_data in devices_found:
                # Normalize keys for DB
                if 'ip' in device_data:
                    device_data['ip_address'] = device_data['ip']
                if 'mac' in device_data:
                    device_data['mac_address'] = device_data['mac']
                Device.upsert(device_data)

            # Mark old devices as inactive
            Device.mark_inactive(cutoff_hours=2)

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

# Start auto-scan thread when module loads
auto_scan_thread = threading.Thread(target=auto_scan)
auto_scan_thread.daemon = True
auto_scan_thread.start()
