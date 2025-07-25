import subprocess
import re
import socket
import ipaddress
from datetime import datetime

def get_network_range():
    """Get the local network range"""
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    # Assume /24 subnet
    network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
    return network

def scan_arp_table():
    """Scan ARP table for connected devices"""
    devices = []
    try:
        # On Windows: arp -a
        # On Linux/Mac: arp -a or ip neigh
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True)

        for line in result.stdout.split('\n'):
            # Parse ARP entries
            match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\) at ([a-fA-F0-9:]{17})', line)
            if match:
                ip, mac = match.groups()
                devices.append({
                    'ip': ip,
                    'mac': mac,
                    'last_seen': datetime.now(),
                    'method': 'ARP'
                })
    except Exception as e:
        print(f"ARP scan failed: {e}")

    return devices

def ping_sweep(network_range):
    """Perform ping sweep to find active devices"""
    active_devices = []
    for ip in network_range.hosts():
        try:
            # Ping with 1 second timeout
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '1000', str(ip)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                active_devices.append({
                    'ip': str(ip),
                    'status': 'active',
                    'last_seen': datetime.now(),
                    'method': 'ping'
                })
        except Exception:
            continue

    return active_devices
