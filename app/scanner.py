import subprocess
import re
import socket
import ipaddress
import threading
from datetime import datetime
import time
import json

from config import Config as conf
networkRange = conf.NETWORK_RANGE

try:
    from mac_vendor_lookup import MacLookup
    MAC_LOOKUP_AVAILABLE = True
except ImportError:
    MAC_LOOKUP_AVAILABLE = False
    print("Warning: mac-vendor-lookup not available. Install with: pip install mac-vendor-lookup")

class NetworkScanner:
    def __init__(self, network_range=networkRange):
        self.network_range = network_range
        self.devices = []
        self.scan_lock = threading.Lock()
        if MAC_LOOKUP_AVAILABLE:
            self.mac_lookup = MacLookup()
            self.mac_lookup.update_vendors()
        # Detect local IP and MAC
        self.local_ip = self._get_local_ip()
        self.local_mac = self._get_local_mac(self.local_ip)
        # Fallback: get MAC from local interfaces if not found
        if not self.local_mac:
            try:
                import netifaces
                for iface in netifaces.interfaces():
                    addrs = netifaces.ifaddresses(iface)
                    if netifaces.AF_INET in addrs:
                        for addr in addrs[netifaces.AF_INET]:
                            if addr.get('addr') == self.local_ip:
                                mac = addrs.get(netifaces.AF_LINK, [{}])[0].get('addr')
                                if mac:
                                    self.local_mac = mac
                                    break
            except ImportError:
                print("Warning: netifaces not installed. Local MAC fallback unavailable.")

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return None

    def _get_local_mac(self, ip):
        if not ip:
            return None
        try:
            import platform
            system = platform.system().lower()
            if system == 'windows':
                result = subprocess.run(['arp', '-a', ip], capture_output=True, text=True, timeout=5)
                match = re.search(r'([a-fA-F0-9-]{17})', result.stdout)
                if match:
                    return match.group(1).replace('-', ':')
            else:
                result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True, timeout=5)
                match = re.search(r'([a-fA-F0-9:]{17})', result.stdout)
                if match:
                    return match.group(1)
        except:
            pass
        return None

    def get_local_network_range(self):
        """Automatically detect local network range"""
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            # Assume /24 subnet
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            return network
        except Exception as e:
            print(f"Could not detect network range: {e}")
            return ipaddress.IPv4Network(self.network_range)

    def scan_arp_table(self):
        """Scan ARP table for connected devices"""
        devices = []
        try:
            import platform
            system = platform.system().lower()

            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                print(f"ARP command failed: {result.stderr}")
                return devices

            # Parse ARP entries
            for line in result.stdout.split('\n'):
                if system == 'windows':
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([a-fA-F0-9-]{17})', line)
                    if match:
                        ip, mac = match.groups()
                        mac = mac.replace('-', ':')
                else:
                    match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\) at ([a-fA-F0-9:]{17})', line)
                    if match:
                        ip, mac = match.groups()

                if match and self._is_valid_ip(ip):
                    device_info = self._get_device_info(ip, mac, method='ARP')
                    if device_info:
                        devices.append(device_info)

        except subprocess.TimeoutExpired:
            print("ARP scan timed out")
        except Exception as e:
            print(f"ARP scan failed: {e}")

        return devices

    def ping_sweep(self, network_range=None):
        """Perform ping sweep to find active devices"""
        if network_range is None:
            network_range = self.get_local_network_range()

        active_devices = []
        threads = []

        def ping_host(ip):
            try:
                import platform
                system = platform.system().lower()

                if system == 'windows':
                    cmd = ['ping', '-n', '1', '-w', '1000', str(ip)]
                else:
                    cmd = ['ping', '-c', '1', '-W', '1', str(ip)]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)

                if result.returncode == 0:
                    with self.scan_lock:
                        device_info = self._get_device_info(str(ip), None, method='ping')
                        if device_info:
                            active_devices.append(device_info)

            except Exception as e:
                pass  # Ignore ping failures

        for ip in network_range.hosts():
            thread = threading.Thread(target=ping_host, args=(ip,))
            threads.append(thread)
            thread.start()

            if len(threads) >= 50:
                for t in threads:
                    t.join()
                threads = []

        for thread in threads:
            thread.join()

        filtered_devices = [d for d in active_devices if d]
        return filtered_devices

    def port_scan(self, ip, ports=None):
        """Scan common ports on a device"""
        if ports is None:
            ports = [22, 23, 24, 53, 80, 135, 139, 443, 445, 993, 995, 3000, 3389, 5050, 5060, 5900, 8080]

        open_ports = []

        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except Exception:
                pass

        return open_ports

    def _get_device_info(self, ip, mac, method=None):
        """Gather additional device information"""
        try:
            info = {
                'ip': ip,
                'mac': mac,
                'hostname': self._get_hostname(ip),
                'vendor': self._get_vendor(mac),
                'device_type': self._classify_device(mac, ip),
                'last_seen': datetime.now(),
                'open_ports': [],
                'method': method or 'unknown'
            }

            # Get open ports
            info['open_ports'] = self.port_scan(ip)
            return info
        except Exception as e:
            print(f"Error getting device info for {ip}: {e}")
            return None

    def _get_hostname(self, ip):
        """Get hostname for IP address"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return None

    def _get_vendor(self, mac):
        """Get vendor from MAC address"""
        if not MAC_LOOKUP_AVAILABLE or not mac:
            return None
        try:
            vendor = self.mac_lookup.lookup(mac)
            return vendor
        except:
            return None

    def _classify_device(self, mac, ip):
        """Classify device type based on MAC vendor and other info"""
        if not mac:
            return 'Unknown'

        vendor = self._get_vendor(mac)
        hostname = self._get_hostname(ip)
        if not vendor:
            return 'Unknown'

        # convert to lower to ensure no errors
        vendor = vendor.lower()
        hostname = hostname.lower()

        # check for local IP and MAC
        if ip == self.local_ip and mac == self.local_mac:
            return 'This Device'

        # Router/Gateway detection
        if any(term in vendor for term in ['cisco', 'netgear', 'linksys', 'asus', 'tp-link', 'dlink', 'askey']):
            return 'Router/Gateway'
        if any(term in hostname for term in ['cisco', 'netgear', 'linksys', 'asus', 'tp-link', 'dlink', 'askey']):
            return 'Router/Gateway'
        # Mobile devices
        if any(term in vendor for term in ['apple', 'samsung', 'lg electronics', 'htc', 'pixel']):
            return 'Mobile Device'
        if any(term in hostname for term in ['pixel', 'samsung', 'apple', 'iphone', 'htc']):
            return 'Mobile Device'
        # Computers
        if any(term in vendor for term in ['dell', 'hp', 'lenovo', 'intel', 'asus', 'framework']):
            return 'Computer'
        if any(term in hostname for term in ['dell', 'hp', 'lenovo', 'intel', 'asus', 'framework']):
            return 'Computer'
        # IoT devices
        if any(term in vendor for term in ['amazon', 'google', 'nest', 'philips', 'sonos', 'roku', 'tv', 'tcl']):
            return 'IoT Device'
        if any(term in hostname for term in ['amazon', 'google', 'nest', 'philips', 'sonos', 'roku', 'tv', 'tcl']):
            return 'IoT Device'
        return 'Unknown'

    def _is_valid_ip(self, ip):
        """Check if IP is valid and not a broadcast/network address"""
        try:
            ip_obj = ipaddress.IPv4Address(ip)
            # Exclude broadcast and network addresses
            if str(ip_obj).endswith('.0') or str(ip_obj).endswith('.255'):
                return False
            return True
        except:
            return False

    def full_scan(self):
        """Perform a comprehensive network scan"""
        print("Starting network scan...")
        start_time = time.time()

        all_devices = []

        # ARP scan
        print("Scanning ARP table...")
        arp_devices = self.scan_arp_table()
        all_devices.extend(arp_devices)

        # Ping sweep
        print("Performing ping sweep...")
        ping_devices = self.ping_sweep()

        # Merge devices (avoid duplicates by IP)
        existing_ips = {device['ip'] for device in all_devices}
        for device in ping_devices:
            if device['ip'] not in existing_ips:
                all_devices.append(device)

        # Enhance devices found via ping with ARP info
        for device in all_devices:
            if device['mac'] is None and device['method'] == 'ping':
                mac = self._get_mac_from_arp(device['ip'])
                if mac != None:
                    device['mac'] = mac
                    device['vendor'] = self._get_vendor(mac)
                    device['device_type'] = self._classify_device(mac, device['ip'])

        # Remove any local device entries without a MAC (from ping/ARP)
        all_devices = [d for d in all_devices if not (d['ip'] == self.local_ip and not d.get('mac'))]

        # If local device is not in the list, add it manually
        local_present = any(d['ip'] == self.local_ip and d.get('mac') == self.local_mac for d in all_devices)
        if self.local_ip and self.local_mac and not local_present:
            local_info = self._get_device_info(self.local_ip, self.local_mac, method='local')
            if local_info:
                all_devices.append(local_info)

        # Ensure local device is saved to the database with all info, and remove any DB rows for local_ip with no MAC
        if self.local_ip and self.local_mac:
            from app.models import Device, DatabaseManager
            # Remove DB rows for local_ip with no MAC
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM devices WHERE ip_address = ? AND (mac_address IS NULL OR mac_address = '')", (self.local_ip,))
            conn.commit()
            conn.close()
            local_info = self._get_device_info(self.local_ip, self.local_mac, method='local')
            if local_info:
                local_info['ip_address'] = local_info['ip']
                local_info['mac_address'] = local_info['mac']
                local_info['is_active'] = 1
                Device.upsert(local_info)

        scan_duration = time.time() - start_time
        print(f"Scan completed in {scan_duration:.2f} seconds. Found {len(all_devices)} devices.")

        return all_devices, scan_duration

    def _get_mac_from_arp(self, ip):
        """Get MAC address from ARP table for specific IP"""
        try:
            import platform
            system = platform.system().lower()

            if system == 'windows':
                result = subprocess.run(['arp', '-a', ip], capture_output=True, text=True, timeout=5)
                match = re.search(r'([a-fA-F0-9-]{17})', result.stdout)
                if match:
                    return match.group(1).replace('-', ':')
            else:
                result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True, timeout=5)
                match = re.search(r'([a-fA-F0-9:]{17})', result.stdout)
                if match:
                    return match.group(1)
        except:
            pass

        return None
