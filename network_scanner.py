"""
TYRELL // CONTROL CENTER v2.0 - LAN Radar & Network Scanner
Discovers active nodes on the local subnet via ARP cache and multi-threaded port probing.
"""
import subprocess
import socket
import re
import threading
from typing import List, Dict, Callable

COMMON_PORTS = [22, 80, 443, 8080, 5000, 3000]

class NetworkScanner:
    @staticmethod
    def get_arp_devices() -> List[Dict[str, str]]:
        """Quickly read cached ARP table from Windows."""
        devices = []
        try:
            output = subprocess.check_output(["arp", "-a"], universal_newlines=True, stderr=subprocess.DEVNULL)
            # Match IPv4 addresses followed by MAC address and type
            pattern = re.compile(r"([0-9]{1,3}(?:\.[0-9]{1,3}){3})\s+([0-9a-fA-F\-]{17})\s+(\w+)")
            for line in output.splitlines():
                match = pattern.search(line)
                if match:
                    ip, mac, dev_type = match.groups()
                    if dev_type.lower() == "dynamic" and not ip.endswith(".255"):
                        devices.append({
                            "ip": ip,
                            "mac": mac.replace("-", ":").upper(),
                            "type": dev_type,
                            "status": "DETECTED",
                            "hostname": ""
                        })
        except Exception:
            pass
        return devices

    @staticmethod
    def probe_host(ip: str, timeout: float = 0.4) -> Dict[str, str]:
        """Test a specific IP for reachability, hostname, and open ports."""
        open_ports = []
        hostname = ""
        is_up = False
        
        # Try reverse DNS
        try:
            host_info = socket.gethostbyaddr(ip)
            hostname = host_info[0]
        except Exception:
            hostname = "Unknown Host"

        for port in COMMON_PORTS:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                res = s.connect_ex((ip, port))
                if res == 0:
                    open_ports.append(str(port))
                    is_up = True
            except Exception:
                pass
            finally:
                s.close()
                
        return {
            "ip": ip,
            "hostname": hostname,
            "open_ports": ", ".join(open_ports) if open_ports else "None",
            "status": "ONLINE" if (is_up or open_ports) else "ACTIVE_ARP"
        }

    @classmethod
    def scan_network_async(cls, on_device_found: Callable[[Dict[str, str]], None], on_finished: Callable[[int], None]):
        """Run asynchronous network scan without blocking Tkinter UI."""
        def worker():
            arp_devs = cls.get_arp_devices()
            count = 0
            threads = []
            
            def check_and_report(dev):
                nonlocal count
                probe = cls.probe_host(dev["ip"])
                dev.update(probe)
                count += 1
                on_device_found(dev)

            for d in arp_devs:
                t = threading.Thread(target=check_and_report, args=(d,), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=2.0)

            on_finished(count)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
