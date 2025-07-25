#!/usr/bin/env python3
"""
Database backup script for Network Dashboard
Creates timestamped backups of the SQLite database
"""

import shutil
import datetime
import os
import sys
import argparse
import sqlite3
from pathlib import Path

def get_project_root():
    """Get the project root directory"""
    return Path(__file__).parent.parent

def create_backup_directory():
    """Create backup directory if it doesn't exist"""
    backup_dir = get_project_root() / 'data' / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def backup_database(db_path=None, backup_dir=None):
    """
    Create a backup of the database

    Args:
        db_path: Path to the database file
        backup_dir: Directory to store backups

    Returns:
        str: Path to the backup file or None if failed
    """
    if db_path is None:
        db_path = get_project_root() / 'data' / 'network.db'

    if backup_dir is None:
        backup_dir = create_backup_directory()

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return None

    # Create timestamp for backup filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"network_backup_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    try:
        # Test database integrity before backup
        if not test_database_integrity(db_path):
            print("Warning: Database integrity check failed, but proceeding with backup")

        # Create backup
        shutil.copy2(db_path, backup_path)

        # Verify backup
        if verify_backup(backup_path):
            print(f"Database backed up successfully to: {backup_path}")
            print(f"Backup size: {get_file_size(backup_path)}")
            return str(backup_path)
        else:
            print("Error: Backup verification failed")
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return None

    except Exception as e:
        print(f"Error creating backup: {e}")
        return None

def test_database_integrity(db_path):
    """
    Test database integrity

    Args:
        db_path: Path to database file

    Returns:
        bool: True if integrity check passes
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()

        return result[0] == 'ok'
    except Exception as e:
        print(f"Integrity check failed: {e}")
        return False

def verify_backup(backup_path):
    """
    Verify that backup is readable and contains expected tables

    Args:
        backup_path: Path to backup file

    Returns:
        bool: True if backup is valid
    """
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()

        # Check that main tables exist
        expected_tables = ['devices', 'device_history', 'network_scans', 'settings']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in expected_tables:
            if table not in tables:
                print(f"Warning: Expected table '{table}' not found in backup")

        # Try to read from devices table
        cursor.execute("SELECT COUNT(*) FROM devices")
        device_count = cursor.fetchone()[0]
        print(f"Backup contains {device_count} devices")

        conn.close()
        return True

    except Exception as e:
        print(f"Backup verification failed: {e}")
        return False

def get_file_size(file_path):
    """Get human-readable file size"""
    size = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def cleanup_old_backups(backup_dir=None, keep_days=30):
    """
    Remove backup files older than specified days

    Args:
        backup_dir: Directory containing backups
        keep_days: Number of days to keep backups
    """
    if backup_dir is None:
        backup_dir = create_backup_directory()

    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=keep_days)
    removed_count = 0

    try:
        for backup_file in backup_dir.glob("network_backup_*.db"):
            file_time = datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)

            if file_time < cutoff_date:
                backup_file.unlink()
                removed_count += 1
                print(f"Removed old backup: {backup_file.name}")

        if removed_count == 0:
            print("No old backups to remove")
        else:
            print(f"Removed {removed_count} old backup(s)")

    except Exception as e:
        print(f"Error cleaning up old backups: {e}")

def list_backups(backup_dir=None):
    """List all available backups"""
    if backup_dir is None:
        backup_dir = create_backup_directory()

    backups = sorted(backup_dir.glob("network_backup_*.db"), reverse=True)

    if not backups:
        print("No backups found")
        return

    print(f"Found {len(backups)} backup(s):")
    print("-" * 60)

    for backup in backups:
        stat = backup.stat()
        size = get_file_size(backup)
        modified = datetime.datetime.fromtimestamp(stat.st_mtime)

        print(f"{backup.name}")
        print(f"  Size: {size}")
        print(f"  Date: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

def restore_backup(backup_path, target_path=None):
    """
    Restore database from backup

    Args:
        backup_path: Path to backup file
        target_path: Target path for restored database
    """
    if target_path is None:
        target_path = get_project_root() / 'data' / 'network.db'

    if not os.path.exists(backup_path):
        print(f"Error: Backup file not found at {backup_path}")
        return False

    try:
        # Verify backup before restore
        if not verify_backup(backup_path):
            print("Error: Backup verification failed, aborting restore")
            return False

        # Create backup of current database if it exists
        if os.path.exists(target_path):
            current_backup = f"{target_path}.pre_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(target_path, current_backup)
            print(f"Current database backed up to: {current_backup}")

        # Restore from backup
        shutil.copy2(backup_path, target_path)
        print(f"Database restored from: {backup_path}")
        return True

    except Exception as e:
        print(f"Error restoring backup: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Network Dashboard Database Backup Tool')
    parser.add_argument('action', choices=['backup', 'list', 'cleanup', 'restore'],
                       help='Action to perform')
    parser.add_argument('--db-path', help='Path to database file')
    parser.add_argument('--backup-dir', help='Backup directory')
    parser.add_argument('--keep-days', type=int, default=30,
                       help='Days to keep backups (for cleanup)')
    parser.add_argument('--backup-file', help='Backup file to restore from')

    args = parser.parse_args()

    if args.action == 'backup':
        result = backup_database(args.db_path, args.backup_dir)
        if result:
            print("Backup completed successfully")
        else:
            print("Backup failed")
            sys.exit(1)

    elif args.action == 'list':
        list_backups(args.backup_dir)

    elif args.action == 'cleanup':
        cleanup_old_backups(args.backup_dir, args.keep_days)

    elif args.action == 'restore':
        if not args.backup_file:
            print("Error: --backup-file required for restore action")
            sys.exit(1)

        if restore_backup(args.backup_file):
            print("Restore completed successfully")
        else:
            print("Restore failed")
            sys.exit(1)

if __name__ == '__main__':
    main()
