"""
TYRELL // CONTROL CENTER v2.0 - SSH & SFTP Engine
Thread-safe Paramiko communication, real-time log streaming, and telemetry collector.
"""
import os
import time
import socket
import threading
import json
from typing import Optional, Tuple, Callable, Dict, Any
import paramiko

class SSHManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        self.is_connected = False
        self.last_error = ""
        self.connection_info = {}
        self.latency_ms = 0.0
        
        # CPU tracking state for accurate delta calculation
        self._prev_cpu_idle = 0
        self._prev_cpu_total = 0
        
        # Active stream thread tracking
        self._log_stream_active = False

    def connect(self, host: str, port: int, user: str, password: str = "", key_path: str = "", timeout: float = 5.0) -> Tuple[bool, str]:
        """Establish SSH and SFTP connections with auto key / password fallback."""
        with self.lock:
            self.disconnect()
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                connect_kwargs: Dict[str, Any] = {
                    "hostname": host,
                    "port": port,
                    "username": user,
                    "timeout": timeout,
                    "banner_timeout": timeout,
                    "auth_timeout": timeout,
                    "look_for_keys": True,
                    "allow_agent": True,
                }
                
                # Check for explicit private key
                expanded_key = os.path.expanduser(key_path) if key_path else ""
                if expanded_key and os.path.isfile(expanded_key):
                    connect_kwargs["key_filename"] = expanded_key
                elif password:
                    connect_kwargs["password"] = password

                start_time = time.time()
                client.connect(**connect_kwargs)
                self.latency_ms = round((time.time() - start_time) * 1000, 1)

                self.client = client
                self.sftp = client.open_sftp()
                self.is_connected = True
                self.last_error = ""
                self.connection_info = {
                    "host": host,
                    "port": port,
                    "user": user,
                    "connected_at": time.time()
                }
                return True, "CONNECTED"
            except Exception as e:
                self.is_connected = False
                self.last_error = str(e)
                self.disconnect()
                return False, str(e)

    def disconnect(self):
        """Safely close active connections."""
        with self.lock:
            self.is_connected = False
            if self.sftp:
                try:
                    self.sftp.close()
                except Exception:
                    pass
                self.sftp = None
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
                self.client = None

    def check_connection_health(self) -> bool:
        """Lightweight heartbeat check using SSH transport."""
        with self.lock:
            if not self.is_connected or not self.client:
                return False
            transport = self.client.get_transport()
            if transport is None or not transport.is_active():
                self.is_connected = False
                return False
            return True

    def exec_command(self, cmd: str, timeout: float = 15.0) -> Tuple[int, str, str]:
        """Execute remote command thread-safely."""
        with self.lock:
            if not self.check_connection_health() or not self.client:
                return -1, "", "SSH connection offline"
            try:
                stdin, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
                out = stdout.read().decode("utf-8", errors="replace")
                err = stderr.read().decode("utf-8", errors="replace")
                exit_code = stdout.channel.recv_exit_status()
                return exit_code, out, err
            except Exception as e:
                self.last_error = str(e)
                return -1, "", str(e)

    def get_system_metrics(self, project_dir: str = "/home/tyrell/resale-agent", service_name: str = "resale_bot.service") -> Dict[str, Any]:
        """Collect all system telemetry and database analytics in a single ultra-fast batch."""
        if not self.check_connection_health() or not self.client:
            return {"online": False, "error": "Disconnected"}

        collector_cmd = f'''python3 -c "
import os, json, subprocess, time

def read_file(path):
    try:
        with open(path) as f: return f.read()
    except: return ''

# RAM
ram_total, ram_avail = 0, 0
for line in read_file('/proc/meminfo').splitlines():
    if line.startswith('MemTotal:'): ram_total = int(line.split()[1]) * 1024
    elif line.startswith('MemAvailable:'): ram_avail = int(line.split()[1]) * 1024
ram_used = ram_total - ram_avail
ram_pct = round((ram_used / ram_total) * 100, 1) if ram_total else 0.0

# Disk
st = os.statvfs('/')
disk_total = st.f_blocks * st.f_frsize
disk_free = st.f_bavail * st.f_frsize
disk_used = disk_total - disk_free
disk_pct = round((disk_used / disk_total) * 100, 1) if disk_total else 0.0

# Temp
temp_c = 0.0
try:
    out = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
    temp_c = float(out.replace('temp=', '').replace(\\"'C\\", '').strip())
except:
    try:
        temp_c = round(int(read_file('/sys/class/thermal/thermal_zone0/temp')) / 1000.0, 1)
    except: pass

# Service Status
service_status = 'inactive'
try:
    service_status = subprocess.check_output(['systemctl', 'is-active', '{service_name}']).decode().strip()
except subprocess.CalledProcessError as e:
    service_status = e.output.decode().strip() if e.output else 'inactive'
except: pass

# Uptime
uptime_sec = 0
try: uptime_sec = int(float(read_file('/proc/uptime').split()[0]))
except: pass

# Top 5 processes
top_procs = []
try:
    ps_out = subprocess.check_output(['ps', '-eo', 'pid,%cpu,%mem,comm', '--sort=-%cpu']).decode().splitlines()
    for l in ps_out[1:6]:
        parts = l.strip().split(None, 3)
        if len(parts) >= 4:
            top_procs.append({{'pid': parts[0], 'cpu': parts[1], 'mem': parts[2], 'comm': parts[3]}})
except: pass

# SQLite DB stats
db_stats = {{'items': 0, 'subscriptions': 0, 'last_item': None}}
try:
    import sqlite3
    db_file = os.path.expanduser('{project_dir}/bazos_monitor.db')
    if os.path.exists(db_file):
        conn = sqlite3.connect(db_file, timeout=1)
        cur = conn.cursor()
        try:
            cur.execute('SELECT count(*) FROM items')
            db_stats['items'] = cur.fetchone()[0]
        except: pass
        try:
            cur.execute('SELECT count(*) FROM subscriptions')
            db_stats['subscriptions'] = cur.fetchone()[0]
        except: pass
        try:
            cur.execute('SELECT title, price, created_at FROM items ORDER BY id DESC LIMIT 1')
            row = cur.fetchone()
            if row:
                db_stats['last_item'] = {{'title': str(row[0]), 'price': str(row[1]), 'time': str(row[2])}}
        except: pass
        conn.close()
except: pass

# CPU raw values for delta
cpu_vals = []
try:
    cpu_line = [l for l in read_file('/proc/stat').splitlines() if l.startswith('cpu ')][0]
    cpu_vals = [int(x) for x in cpu_line.split()[1:]]
except: pass

res = {{
    'ram_total': ram_total,
    'ram_used': ram_used,
    'ram_pct': ram_pct,
    'disk_total': disk_total,
    'disk_used': disk_used,
    'disk_pct': disk_pct,
    'temp_c': temp_c,
    'service': service_status,
    'uptime_sec': uptime_sec,
    'top_procs': top_procs,
    'db_stats': db_stats,
    'cpu_raw': cpu_vals
}}
print(json.dumps(res))
"'''
        t_start = time.time()
        code, out, err = self.exec_command(collector_cmd, timeout=4.0)
        self.latency_ms = round((time.time() - t_start) * 1000, 1)

        if code != 0 or not out.strip():
            return {"online": True, "error": f"Collector error: {err[:100]}", "latency_ms": self.latency_ms}

        try:
            data = json.loads(out.strip())
            
            # Compute CPU delta %
            cpu_vals = data.get("cpu_raw", [])
            cpu_pct = 0.0
            if len(cpu_vals) >= 4:
                idle = cpu_vals[3] + (cpu_vals[4] if len(cpu_vals) > 4 else 0)
                total = sum(cpu_vals)
                if self._prev_cpu_total > 0 and total > self._prev_cpu_total:
                    idle_delta = idle - self._prev_cpu_idle
                    total_delta = total - self._prev_cpu_total
                    if total_delta > 0:
                        cpu_pct = max(0.0, min(100.0, round((1.0 - (idle_delta / total_delta)) * 100.0, 1)))
                self._prev_cpu_idle = idle
                self._prev_cpu_total = total

            # Format human uptime
            secs = data.get("uptime_sec", 0)
            days, rem = divmod(secs, 86400)
            hours, rem = divmod(rem, 3600)
            mins, _ = divmod(rem, 60)
            uptime_str = f"{days}d {hours}h {mins}m" if days > 0 else f"{hours}h {mins}m"

            return {
                "online": True,
                "latency_ms": self.latency_ms,
                "cpu_pct": cpu_pct,
                "ram_pct": data.get("ram_pct", 0.0),
                "ram_used_mb": round(data.get("ram_used", 0) / (1024 * 1024), 1),
                "ram_total_mb": round(data.get("ram_total", 0) / (1024 * 1024), 1),
                "disk_pct": data.get("disk_pct", 0.0),
                "disk_used_gb": round(data.get("disk_used", 0) / (1024**3), 2),
                "disk_total_gb": round(data.get("disk_total", 0) / (1024**3), 2),
                "temp_c": data.get("temp_c", 0.0),
                "service": data.get("service", "unknown"),
                "uptime_str": uptime_str,
                "top_procs": data.get("top_procs", []),
                "db_stats": data.get("db_stats", {})
            }
        except Exception as e:
            return {"online": True, "error": f"Parse error: {e}", "latency_ms": self.latency_ms}

    def manage_service(self, action: str, service_name: str = "resale_bot.service") -> Tuple[bool, str]:
        """Perform systemctl action: start, stop, restart, status."""
        valid_actions = ["start", "stop", "restart", "status", "enable", "disable"]
        if action not in valid_actions:
            return False, f"Invalid action: {action}"
        
        cmd = f"sudo systemctl {action} {service_name}"
        code, out, err = self.exec_command(cmd, timeout=10.0)
        if code == 0:
            return True, f"Service {service_name} {action} succeeded."
        else:
            return False, f"Error {code}: {err.strip() or out.strip()}"

    def read_file(self, remote_path: str, project_dir: str = "/home/tyrell/resale-agent") -> Tuple[bool, str]:
        """Read file content over SFTP."""
        with self.lock:
            if not self.check_connection_health() or not self.sftp:
                return False, "SFTP connection offline"
            
            full_path = remote_path if remote_path.startswith("/") else os.path.join(project_dir, remote_path).replace("\\", "/")
            try:
                with self.sftp.open(full_path, "r") as f:
                    content = f.read().decode("utf-8", errors="replace")
                return True, content
            except Exception as e:
                return False, f"Failed to read {full_path}: {e}"

    def write_file(self, remote_path: str, content: str, project_dir: str = "/home/tyrell/resale-agent", make_backup: bool = True) -> Tuple[bool, str]:
        """Safely write file over SFTP with optional .bak backup creation."""
        with self.lock:
            if not self.check_connection_health() or not self.sftp:
                return False, "SFTP connection offline"

            full_path = remote_path if remote_path.startswith("/") else os.path.join(project_dir, remote_path).replace("\\", "/")
            try:
                # Create backup if requested
                if make_backup:
                    try:
                        bak_path = f"{full_path}.bak"
                        # Check if original exists before backing up
                        try:
                            self.sftp.stat(full_path)
                            self.exec_command(f"cp '{full_path}' '{bak_path}'")
                        except Exception:
                            pass
                    except Exception:
                        pass

                # Write content
                with self.sftp.open(full_path, "w") as f:
                    f.write(content.encode("utf-8"))
                return True, f"Successfully deployed to {full_path}"
            except Exception as e:
                return False, f"Failed to write {full_path}: {e}"

    def stream_journal_logs(self, service_name: str, on_line_cb: Callable[[str], None], stop_event: threading.Event, lines: int = 100):
        """Dedicated worker to stream real-time logs from journalctl."""
        transport = None
        channel = None
        try:
            with self.lock:
                if not self.check_connection_health() or not self.client:
                    on_line_cb("[OFFLINE] SSH disconnected. Live log stream halted.")
                    return
                transport = self.client.get_transport()
                if not transport or not transport.is_active():
                    return
                channel = transport.open_session()
                channel.set_combine_stderr(True)
                cmd = f"journalctl -u {service_name} -n {lines} -f --no-pager"
                channel.exec_command(cmd)

            buf = ""
            while not stop_event.is_set():
                if channel.recv_ready():
                    chunk = channel.recv(4096).decode("utf-8", errors="replace")
                    if not chunk:
                        break
                    buf += chunk
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        on_line_cb(line)
                elif channel.exit_status_ready():
                    break
                else:
                    time.sleep(0.08)
        except Exception as e:
            if not stop_event.is_set():
                on_line_cb(f"[STREAM ERROR] Connection dropped: {e}")
        finally:
            if channel:
                try:
                    channel.close()
                except Exception:
                    pass
