import sqlite3
import json
from datetime import datetime, timedelta
from flask import current_app

class DatabaseManager:
    @staticmethod
    def get_connection():
        """Get database connection"""
        return sqlite3.connect(current_app.config['DATABASE_PATH'])

    @staticmethod
    def dict_factory(cursor, row):
        """Convert sqlite row to dictionary"""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

class Device:
    @staticmethod
    def get_all():
        """Get all devices from database"""
        conn = DatabaseManager.get_connection()
        conn.row_factory = DatabaseManager.dict_factory
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, ip_address, mac_address, hostname, vendor, device_type, first_seen, last_seen, is_active, open_ports
            FROM devices
            ORDER BY last_seen DESC
        """)

        devices = cursor.fetchall()
        conn.close()

        # Parse JSON fields
        for device in devices:
            if device['open_ports']:
                try:
                    device['open_ports'] = json.loads(device['open_ports'])
                except:
                    device['open_ports'] = []
            else:
                device['open_ports'] = []

        return devices

    @staticmethod
    def get_active(hours=1):
        """Get devices active within specified hours"""
        conn = DatabaseManager.get_connection()
        conn.row_factory = DatabaseManager.dict_factory
        cursor = conn.cursor()

        cutoff_time = datetime.now() - timedelta(hours=hours)
        cursor.execute("""
            SELECT id, ip_address, mac_address, hostname, vendor, device_type, first_seen, last_seen, is_active, open_ports
            FROM devices
            WHERE last_seen > ? AND is_active = 1
            ORDER BY last_seen DESC
        """, (cutoff_time,))

        devices = cursor.fetchall()
        conn.close()
        return devices

    @staticmethod
    def upsert(device_data):
        """Insert or update device information, tracking first_seen and last_seen"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        # Convert open_ports list to JSON string
        if 'open_ports' in device_data and isinstance(device_data['open_ports'], list):
            device_data['open_ports'] = json.dumps(device_data['open_ports'])

        # Check if device exists (by MAC address)
        cursor.execute("SELECT id, first_seen FROM devices WHERE mac_address = ?", (device_data.get('mac_address'),))
        existing = cursor.fetchone()

        if existing:
            # Update existing device, preserve first_seen
            cursor.execute("""
                UPDATE devices SET
                    ip_address = ?,
                    hostname = ?,
                    vendor = ?,
                    device_type = ?,
                    last_seen = CURRENT_TIMESTAMP,
                    is_active = 1,
                    open_ports = ?
                WHERE mac_address = ?
            """, (
                device_data.get('ip_address'),
                device_data.get('hostname'),
                device_data.get('vendor'),
                device_data.get('device_type', 'Unknown'),
                device_data.get('open_ports', '[]'),
                device_data.get('mac_address')
            ))
            device_id = existing[0]
        else:
            # Insert new device, set both first_seen and last_seen to now
            cursor.execute("""
                INSERT INTO devices (
                    ip_address, mac_address, hostname, vendor,
                    device_type, open_ports, first_seen, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                device_data.get('ip_address'),
                device_data.get('mac_address'),
                device_data.get('hostname'),
                device_data.get('vendor'),
                device_data.get('device_type', 'Unknown'),
                device_data.get('open_ports', '[]')
            ))
            device_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return device_id

    @staticmethod
    def mark_inactive(cutoff_hours=2):
        """Mark devices as inactive if not seen recently"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        cutoff_time = datetime.now() - timedelta(hours=cutoff_hours)
        cursor.execute("""
            UPDATE devices SET is_active = 0
            WHERE last_seen < ? AND is_active = 1
        """, (cutoff_time,))

        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        return updated_count

class NetworkScan:
    @staticmethod
    def log_scan(devices_found, duration, method):
        """Log a network scan"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO network_scans (devices_found, scan_duration, scan_method)
            VALUES (?, ?, ?)
        """, (devices_found, duration, method))

        conn.commit()
        conn.close()

    @staticmethod
    def get_recent_scans(limit=10):
        """Get recent scan history"""
        conn = DatabaseManager.get_connection()
        conn.row_factory = DatabaseManager.dict_factory
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM network_scans
            ORDER BY scan_time DESC
            LIMIT ?
        """, (limit,))

        scans = cursor.fetchall()
        conn.close()
        return scans

class Stats:
    @staticmethod
    def get_dashboard_stats():
        """Get statistics for dashboard"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        # Total devices
        cursor.execute("SELECT COUNT(*) FROM devices")
        total_devices = cursor.fetchone()[0]

        # Active devices (last hour)
        hour_ago = datetime.now() - timedelta(hours=1)
        cursor.execute("SELECT COUNT(*) FROM devices WHERE last_seen > ? AND is_active = 1", (hour_ago,))
        active_devices = cursor.fetchone()[0]

        # New devices today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cursor.execute("SELECT COUNT(*) FROM devices WHERE first_seen > ?", (today,))
        new_today = cursor.fetchone()[0]

        # Last scan time
        cursor.execute("SELECT scan_time FROM network_scans ORDER BY scan_time DESC LIMIT 1")
        last_scan_result = cursor.fetchone()
        last_scan = last_scan_result[0] if last_scan_result else None

        conn.close()

        return {
            'total_devices': total_devices,
            'active_devices': active_devices,
            'new_today': new_today,
            'last_scan': last_scan
        }
