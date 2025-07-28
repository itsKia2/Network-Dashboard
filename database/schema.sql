-- Network Dashboard Database Schema

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address VARCHAR(15) NOT NULL,
    mac_address VARCHAR(17) UNIQUE,
    hostname VARCHAR(255),
    vendor VARCHAR(255),
    device_type VARCHAR(50) DEFAULT 'Unknown',
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP, -- remove
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    method VARCHAR(20),  -- ARP, ping, etc.
    open_ports TEXT  -- JSON string of open ports
);

CREATE TABLE IF NOT EXISTS device_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER,
    ip_address VARCHAR(15),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20),
    method VARCHAR(20),  -- ARP, ping, etc.
    FOREIGN KEY (device_id) REFERENCES devices (id)
);

CREATE TABLE IF NOT EXISTS network_scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    devices_found INTEGER,
    scan_duration REAL,
    scan_method VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_name VARCHAR(100) UNIQUE,
    setting_value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings
INSERT OR IGNORE INTO settings (setting_name, setting_value) VALUES
('network_range', '192.168.1.0/24'),
('scan_interval', '300'),
('auto_scan_enabled', 'true'),
('port_scan_enabled', 'true');
