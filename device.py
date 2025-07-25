import requests
from mac_vendor_lookup import MacLookup

def get_device_info(ip, mac):
    """Gather additional device information"""
    info = {
        'ip': ip,
        'mac': mac,
        'hostname': None,
        'vendor': None,
        'device_type': 'Unknown',
        'open_ports': []
    }

    # Get hostname
    try:
        info['hostname'] = socket.gethostbyaddr(ip)[0]
    except:
        pass

    # Get vendor from MAC address
    try:
        mac_lookup = MacLookup()
        info['vendor'] = mac_lookup.lookup(mac)
    except:
        pass

    # Basic port scanning (be careful with this)
    common_ports = [22, 23, 53, 80, 443, 445, 993, 995]
    for port in common_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ip, port))
        if result == 0:
            info['open_ports'].append(port)
        sock.close()

    return info
