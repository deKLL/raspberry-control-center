"""
================================================================================
TYRELL // CONTROL CENTER v2.0
Next-Gen Cyberpunk Superapp for Raspberry Pi Zero 2 W Remote Command & Telemetry
================================================================================
"""
import os
import sys
import time
import queue
import threading
import subprocess
from typing import Optional, Dict, Any
import customtkinter as ctk

from config import THEME, FONTS, PRESET_FILES, load_config, save_config
from ssh_client import SSHManager
from ui_components import (
    CyberCard,
    CyberMetricCard,
    CyberStatusBadge,
    CyberLogViewer,
    CyberCodeEditor
)
from network_scanner import NetworkScanner

# Optional Windows sound alert
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class TyrellControlCenterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Appearance & Window Setup ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.title("TYRELL // CONTROL CENTER v2.0 - CYBERPUNK ADMIN")
        self.geometry("1240x820")
        self.minsize(1050, 720)
        self.configure(fg_color=THEME["bg_dark"])

        # Load Configuration
        self.cfg = load_config()

        # Engine & State
        self.ssh = SSHManager()
        self.is_monitoring = True
        self.sound_enabled = self.cfg.get("sound_alerts", True)
        self.previous_service_state = "unknown"
        self.log_stream_stop_event = threading.Event()
        self.macro_history = []
        
        # Thread-safe UI dispatch queue
        self.ui_queue = queue.Queue()
        self._process_ui_queue()
        
        # Build UI Elements
        self._build_header()
        self._build_banner()
        self._build_tabview()
        self._build_footer()

        # Window Close Protocol
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start Background SSH Worker
        self._start_connection_loop()

    def dispatch_ui(self, fn):
        """Thread-safe UI callback dispatcher."""
        self.ui_queue.put(fn)

    def _process_ui_queue(self):
        """Periodic drain of UI events onto Tk main thread."""
        try:
            while not self.ui_queue.empty():
                try:
                    fn = self.ui_queue.get_nowait()
                    fn()
                except Exception:
                    pass
        finally:
            if self.is_monitoring:
                self.after(35, self._process_ui_queue)

    # =========================================================================
    # HEADER SECTION
    # =========================================================================
    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color=THEME["bg_sidebar"], height=64, corner_radius=0)
        self.header_frame.pack(fill="x", side="top")

        # Brand / Logo
        self.logo_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.logo_frame.pack(side="left", padx=18, pady=10)

        self.brand_title = ctk.CTkLabel(
            self.logo_frame,
            text="⚡ TYRELL // CONTROL CENTER",
            font=FONTS["title"],
            text_color=THEME["neon_green"]
        )
        self.brand_title.pack(side="left")

        self.brand_ver = ctk.CTkLabel(
            self.logo_frame,
            text=" v2.0 [CYBERPUNK EDITION]",
            font=FONTS["sub"],
            text_color=THEME["neon_cyan"]
        )
        self.brand_ver.pack(side="left", padx=(4, 0))

        # Right Controls & Status Pill
        self.header_actions = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_actions.pack(side="right", padx=16, pady=10)

        # Connection Badge
        self.conn_badge = CyberStatusBadge(self.header_actions, initial_text="CONNECTING...", initial_color=THEME["neon_gold"])
        self.conn_badge.pack(side="left", padx=6)

        # Telemetry Pill (Ping + Host)
        self.telemetry_lbl = ctk.CTkLabel(
            self.header_actions,
            text=f"{self.cfg['user']}@{self.cfg['host']} | -- ms",
            font=FONTS["mono_sm"],
            text_color=THEME["text_secondary"]
        )
        self.telemetry_lbl.pack(side="left", padx=10)

        # Reconnect Button
        self.reconnect_btn = ctk.CTkButton(
            self.header_actions,
            text="🔄 RECONNECT",
            width=90,
            height=28,
            font=FONTS["button_sm"],
            fg_color="#1F2333",
            hover_color="#2E344C",
            text_color=THEME["neon_green"],
            border_width=1,
            border_color=THEME["neon_green"],
            command=self._trigger_reconnect
        )
        self.reconnect_btn.pack(side="left", padx=4)

        # Settings Button
        self.settings_btn = ctk.CTkButton(
            self.header_actions,
            text="⚙ SETTINGS",
            width=80,
            height=28,
            font=FONTS["button_sm"],
            fg_color="#1F2333",
            hover_color="#2E344C",
            text_color=THEME["text_primary"],
            border_width=1,
            border_color=THEME["border_subtle"],
            command=self._open_settings_dialog
        )
        self.settings_btn.pack(side="left", padx=4)

        # Reboot Button
        self.reboot_btn = ctk.CTkButton(
            self.header_actions,
            text="⚡ REBOOT",
            width=75,
            height=28,
            font=FONTS["button_sm"],
            fg_color="#3D3511",
            hover_color="#5E5114",
            text_color=THEME["neon_gold"],
            border_width=1,
            border_color=THEME["neon_gold"],
            command=lambda: self._confirm_system_action("REBOOT", "sudo reboot")
        )
        self.reboot_btn.pack(side="left", padx=4)

        # Shutdown Button
        self.shutdown_btn = ctk.CTkButton(
            self.header_actions,
            text="🛑 SHUTDOWN",
            width=85,
            height=28,
            font=FONTS["button_sm"],
            fg_color="#3D1418",
            hover_color="#5E1C22",
            text_color=THEME["neon_red"],
            border_width=1,
            border_color=THEME["neon_red"],
            command=lambda: self._confirm_system_action("SHUTDOWN", "sudo shutdown now")
        )
        self.shutdown_btn.pack(side="left", padx=4)

    # =========================================================================
    # OFFLINE BANNER (Conditional)
    # =========================================================================
    def _build_banner(self):
        self.banner_frame = ctk.CTkFrame(self, fg_color="#3B1115", height=32, corner_radius=0)
        self.banner_lbl = ctk.CTkLabel(
            self.banner_frame,
            text="⚠️ SSH LINK DOWN: Unable to reach Raspberry Pi. Retrying background connection...",
            font=FONTS["mono_sm"],
            text_color="#FF8888"
        )
        self.banner_lbl.pack(pady=4)

    def _show_banner(self, show: bool, msg: str = ""):
        if show:
            if msg:
                self.banner_lbl.configure(text=f"⚠️ SSH LINK ALERT: {msg}")
            self.banner_frame.pack(fill="x", after=self.header_frame)
        else:
            self.banner_frame.pack_forget()

    # =========================================================================
    # TABVIEW NAVIGATION
    # =========================================================================
    def _build_tabview(self):
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=THEME["bg_dark"],
            segmented_button_fg_color=THEME["bg_sidebar"],
            segmented_button_selected_color="#183D24",
            segmented_button_selected_hover_color="#1F4F2E",
            segmented_button_unselected_color=THEME["bg_card"],
            segmented_button_unselected_hover_color=THEME["bg_card_alt"],
            text_color=THEME["neon_green"],
            corner_radius=8
        )
        self.tabs.pack(fill="both", expand=True, padx=14, pady=8)

        # Tab Creation
        self.tab_health = self.tabs.add("  📊 SYSTEM HEALTH  ")
        self.tab_agent = self.tabs.add("  🤖 RESALE AGENT  ")
        self.tab_ide = self.tabs.add("  💻 QUICK IDE & DEPLOY  ")
        self.tab_macros = self.tabs.add("  ⚡ QUICK MACROS & SHELL  ")
        self.tab_radar = self.tabs.add("  📡 LAN RADAR & ANALYTICS  ")

        # Populate Tabs
        self._populate_health_tab()
        self._populate_agent_tab()
        self._populate_ide_tab()
        self._populate_macros_tab()
        self._populate_radar_tab()

    # =========================================================================
    # TAB 1: SYSTEM HEALTH
    # =========================================================================
    def _populate_health_tab(self):
        grid = ctk.CTkFrame(self.tab_health, fg_color="transparent")
        grid.pack(fill="x", pady=6)
        grid.columnconfigure((0, 1, 2, 3), weight=1)

        # 4 Metric Cards
        self.card_cpu = CyberMetricCard(grid, title="CPU LOAD", icon="⚡", unit="%", max_val=100.0)
        self.card_cpu.grid(row=0, column=0, padx=6, pady=4, sticky="nsew")

        self.card_ram = CyberMetricCard(grid, title="RAM MEMORY", icon="🧠", unit="%", max_val=100.0)
        self.card_ram.grid(row=0, column=1, padx=6, pady=4, sticky="nsew")

        self.card_disk = CyberMetricCard(grid, title="SD STORAGE", icon="💾", unit="%", max_val=100.0)
        self.card_disk.grid(row=0, column=2, padx=6, pady=4, sticky="nsew")

        self.card_temp = CyberMetricCard(grid, title="CPU TEMPERATURE", icon="🌡️", unit="°C", max_val=85.0)
        self.card_temp.grid(row=0, column=3, padx=6, pady=4, sticky="nsew")

        # Bottom section: Maintenance Controls & Process Table
        lower_frame = ctk.CTkFrame(self.tab_health, fg_color="transparent")
        lower_frame.pack(fill="both", expand=True, pady=(10, 4))
        lower_frame.columnconfigure(0, weight=1)
        lower_frame.columnconfigure(1, weight=2)

        # Maintenance Action Card
        maint_card = CyberCard(lower_frame, title="// SYSTEM UTILITIES & POWER", subtitle="RASPBERRY PI ZERO 2 W")
        maint_card.grid(row=0, column=0, padx=6, sticky="nsew")

        btn_style = {"height": 34, "font": FONTS["button_sm"], "corner_radius": 6}

        ctk.CTkButton(
            maint_card,
            text="📦 UPDATE SYSTEM (APT UPGRADE)",
            fg_color="#1D2A3D",
            hover_color="#273C5A",
            border_width=1,
            border_color=THEME["neon_cyan"],
            text_color=THEME["neon_cyan"],
            command=lambda: self._execute_and_stream_macro("System Update", "sudo apt update && sudo apt upgrade -y"),
            **btn_style
        ).pack(fill="x", padx=14, pady=6)

        ctk.CTkButton(
            maint_card,
            text="🧹 DROP SYSTEM RAM CACHES",
            fg_color="#1E2822",
            hover_color="#2A3B30",
            border_width=1,
            border_color=THEME["neon_green"],
            text_color=THEME["neon_green"],
            command=lambda: self._execute_and_stream_macro("Clear Cache", "sync && echo 3 | sudo tee /proc/sys/vm/drop_caches"),
            **btn_style
        ).pack(fill="x", padx=14, pady=6)

        ctk.CTkButton(
            maint_card,
            text="🌡️ VCGEN DIAGNOSTICS & VOLTS",
            fg_color="#2B2418",
            hover_color="#423722",
            border_width=1,
            border_color=THEME["neon_gold"],
            text_color=THEME["neon_gold"],
            command=lambda: self._execute_and_stream_macro("VCGen Diagnostic", "vcgencmd measure_temp && vcgencmd get_throttled && vcgencmd measure_volts"),
            **btn_style
        ).pack(fill="x", padx=14, pady=6)

        ctk.CTkButton(
            maint_card,
            text="🌐 TEST INTERNET CONNECTIVITY",
            fg_color="#231F2E",
            hover_color="#362F47",
            border_width=1,
            border_color="#A855F7",
            text_color="#C084FC",
            command=lambda: self._execute_and_stream_macro("Network Ping", "ping -c 4 8.8.8.8"),
            **btn_style
        ).pack(fill="x", padx=14, pady=6)

        # Active Processes Card
        procs_card = CyberCard(lower_frame, title="// TOP ACTIVE PROCESSES", subtitle="REAL-TIME PS AUX MONITOR")
        procs_card.grid(row=0, column=1, padx=6, sticky="nsew")

        self.proc_textbox = ctk.CTkTextbox(
            procs_card,
            font=FONTS["mono_sm"],
            fg_color=THEME["bg_dark"],
            text_color=THEME["neon_green"],
            wrap="none",
            corner_radius=6,
            border_width=1,
            border_color=THEME["border_subtle"]
        )
        self.proc_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.proc_textbox.insert("1.0", "PID     %CPU   %MEM   COMMAND\n------------------------------------------------------------\nWaiting for telemetry data...")

    # =========================================================================
    # TAB 2: RESALE AGENT MANAGER
    # =========================================================================
    def _populate_agent_tab(self):
        # Service Banner Card
        top_service_card = CyberCard(self.tab_agent, title="// RESALE BOT SYSTEMD SERVICE", subtitle=self.cfg["service_name"])
        top_service_card.pack(fill="x", padx=6, pady=4)

        service_bar = ctk.CTkFrame(top_service_card, fg_color="transparent")
        service_bar.pack(fill="x", padx=12, pady=(0, 10))

        # Service Indicator Badge
        self.agent_status_badge = CyberStatusBadge(service_bar, initial_text="SERVICE: CHECKING...", initial_color=THEME["neon_gold"])
        self.agent_status_badge.pack(side="left", padx=4)

        self.service_meta_lbl = ctk.CTkLabel(
            service_bar,
            text="Auto-restart enabled | Service Unit: resale_bot.service",
            font=FONTS["mono_sm"],
            text_color=THEME["text_secondary"]
        )
        self.service_meta_lbl.pack(side="left", padx=12)

        # Action Buttons
        btn_cfg = {"width": 110, "height": 30, "font": FONTS["button_sm"], "corner_radius": 6}

        self.btn_agent_start = ctk.CTkButton(
            service_bar,
            text="▶ ЗАПУСТИТЬ",
            fg_color="#006629",
            hover_color="#008837",
            border_width=1,
            border_color=THEME["neon_green"],
            command=lambda: self._control_service("start"),
            **btn_cfg
        )
        self.btn_agent_start.pack(side="right", padx=3)

        self.btn_agent_stop = ctk.CTkButton(
            service_bar,
            text="⏹ ОСТАНОВИТЬ",
            fg_color="#661118",
            hover_color="#881620",
            border_width=1,
            border_color=THEME["neon_red"],
            command=lambda: self._control_service("stop"),
            **btn_cfg
        )
        self.btn_agent_stop.pack(side="right", padx=3)

        self.btn_agent_restart = ctk.CTkButton(
            service_bar,
            text="🔄 ПЕРЕЗАПУСК",
            fg_color="#2A2A38",
            hover_color="#3A3A4E",
            border_width=1,
            border_color=THEME["neon_gold"],
            command=lambda: self._control_service("restart"),
            **btn_cfg
        )
        self.btn_agent_restart.pack(side="right", padx=3)

        # Live Terminal Viewer
        self.log_viewer = CyberLogViewer(self.tab_agent)
        self.log_viewer.pack(fill="both", expand=True, padx=6, pady=4)

    # =========================================================================
    # TAB 3: QUICK IDE & DEPLOYER
    # =========================================================================
    def _populate_ide_tab(self):
        self.code_editor = CyberCodeEditor(
            self.tab_ide,
            on_load_file=self._handle_ide_load,
            on_save_file=self._handle_ide_save
        )
        self.code_editor.pack(fill="both", expand=True, padx=6, pady=6)

    # =========================================================================
    # TAB 4: QUICK MACROS & INTERACTIVE SHELL
    # =========================================================================
    def _populate_macros_tab(self):
        container = ctk.CTkFrame(self.tab_macros, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=6, pady=6)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=2)

        # Left Column: Cyber Macros Bar
        macros_card = CyberCard(container, title="// QUICK MACROS", subtitle="INSTANT SSH EXECUTION")
        macros_card.grid(row=0, column=0, sticky="nsew", padx=4)

        preset_macros = [
            ("📋 BOT LOG (TAIL 80)", f"tail -n 80 {self.cfg['project_dir']}/resale_agent.log"),
            ("🌿 GIT STATUS", f"cd {self.cfg['project_dir']} && git status"),
            ("🔄 GIT PULL ORIGIN", f"cd {self.cfg['project_dir']} && git pull"),
            ("🌐 NETWORK INTERFACES", "ip -br addr && ip route"),
            ("🐍 PYTHON VENV PACKAGES", f"{self.cfg['project_dir']}/venv/bin/pip list | head -n 25"),
            ("🌲 PYTHON PROCESS TREE", "ps aux --forest | grep -E 'python|resale'"),
            ("💾 DISK USAGE TREE", "df -hT /"),
            ("⚡ VOLTS & THROTTLE STATUS", "vcgencmd get_throttled && vcgencmd measure_volts core")
        ]

        for title, cmd in preset_macros:
            ctk.CTkButton(
                macros_card,
                text=title,
                font=FONTS["mono_sm"],
                height=32,
                fg_color=THEME["bg_card_alt"],
                hover_color="#2E3348",
                border_width=1,
                border_color=THEME["border_subtle"],
                anchor="w",
                command=lambda t=title, c=cmd: self._execute_and_stream_macro(t, c)
            ).pack(fill="x", padx=12, pady=3)

        # Right Column: Interactive Terminal
        shell_card = CyberCard(container, title="// INTERACTIVE CYBER SHELL", subtitle="BASH EXECUTION ENGINE")
        shell_card.grid(row=0, column=1, sticky="nsew", padx=4)

        # Shell Output
        self.shell_output = ctk.CTkTextbox(
            shell_card,
            font=FONTS["mono"],
            fg_color=THEME["bg_dark"],
            text_color=THEME["text_primary"],
            wrap="none",
            corner_radius=6,
            border_width=1,
            border_color=THEME["border_subtle"]
        )
        self.shell_output.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.shell_output.tag_config("tag_prompt", foreground=THEME["neon_cyan"])
        self.shell_output.tag_config("tag_err", foreground=THEME["neon_red"])
        self.shell_output.tag_config("tag_res", foreground=THEME["neon_green"])
        self.shell_output.insert("1.0", "[TYRELL SHELL READY] Enter any Linux command below.\n")

        # Shell Input Bar
        input_bar = ctk.CTkFrame(shell_card, fg_color="transparent")
        input_bar.pack(fill="x", padx=12, pady=(0, 10))

        self.shell_entry = ctk.CTkEntry(
            input_bar,
            placeholder_text="Enter remote bash command (e.g. uname -a, ls -la, htop)...",
            font=FONTS["mono"],
            height=34,
            fg_color=THEME["bg_input"],
            border_color=THEME["border_subtle"]
        )
        self.shell_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.shell_entry.bind("<Return>", lambda e: self._submit_shell_cmd())

        self.shell_run_btn = ctk.CTkButton(
            input_bar,
            text="RUN ⏎",
            width=80,
            height=34,
            font=FONTS["button_sm"],
            fg_color="#006629",
            hover_color="#008837",
            border_width=1,
            border_color=THEME["neon_green"],
            command=self._submit_shell_cmd
        )
        self.shell_run_btn.pack(side="right")

    # =========================================================================
    # TAB 5: LAN RADAR & RESALE ANALYTICS
    # =========================================================================
    def _populate_radar_tab(self):
        container = ctk.CTkFrame(self.tab_radar, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=6, pady=6)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        # Left Column: Resale Bot SQLite Database Telemetry
        analytics_card = CyberCard(container, title="// LOT ANALYTICS & DATABASE METRICS", subtitle="BAZOS_MONITOR.DB")
        analytics_card.grid(row=0, column=0, sticky="nsew", padx=4)

        self.db_items_card = CyberMetricCard(analytics_card, title="INDEXED ITEMS", icon="📦", unit="lots", max_val=5000.0)
        self.db_items_card.pack(fill="x", padx=12, pady=6)

        self.db_subs_card = CyberMetricCard(analytics_card, title="ACTIVE SUBSCRIPTIONS", icon="🎯", unit="filters", max_val=50.0)
        self.db_subs_card.pack(fill="x", padx=12, pady=6)

        # Last item detected panel
        last_item_box = CyberCard(analytics_card, title="// LATEST DETECTED LOT", subtitle="REAL-TIME SCRAPER FEED")
        last_item_box.pack(fill="both", expand=True, padx=12, pady=(6, 10))

        self.last_item_lbl = ctk.CTkLabel(
            last_item_box,
            text="No scraped items in database yet.",
            font=FONTS["mono_sm"],
            text_color=THEME["text_primary"],
            justify="left",
            anchor="nw"
        )
        self.last_item_lbl.pack(fill="both", expand=True, padx=12, pady=8)

        # Right Column: LAN Network Radar
        radar_card = CyberCard(container, title="// LAN NETWORK RADAR", subtitle="LOCAL SUBNET SCANNER")
        radar_card.grid(row=0, column=1, sticky="nsew", padx=4)

        radar_actions = ctk.CTkFrame(radar_card, fg_color="transparent")
        radar_actions.pack(fill="x", padx=12, pady=6)

        self.radar_status_lbl = ctk.CTkLabel(
            radar_actions,
            text="RADAR READY. Click Scan to discover local nodes.",
            font=FONTS["mono_sm"],
            text_color=THEME["text_secondary"]
        )
        self.radar_status_lbl.pack(side="left")

        self.scan_btn = ctk.CTkButton(
            radar_actions,
            text="📡 SCAN LAN",
            width=100,
            height=28,
            font=FONTS["button_sm"],
            fg_color="#1F283D",
            hover_color="#2D3B5A",
            border_width=1,
            border_color=THEME["neon_cyan"],
            text_color=THEME["neon_cyan"],
            command=self._start_network_scan
        )
        self.scan_btn.pack(side="right")

        self.radar_output = ctk.CTkTextbox(
            radar_card,
            font=FONTS["mono_sm"],
            fg_color=THEME["bg_dark"],
            text_color=THEME["text_primary"],
            wrap="none",
            corner_radius=6,
            border_width=1,
            border_color=THEME["border_subtle"]
        )
        self.radar_output.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.radar_output.tag_config("tag_pi", foreground=THEME["neon_green"])
        self.radar_output.tag_config("tag_node", foreground=THEME["neon_cyan"])
        self.radar_output.tag_config("tag_head", foreground=THEME["neon_gold"])
        self.radar_output.insert("1.0", "IP ADDRESS       MAC ADDRESS         STATUS     OPEN PORTS   HOST\n----------------------------------------------------------------------\n")

    # =========================================================================
    # FOOTER SECTION
    # =========================================================================
    def _build_footer(self):
        self.footer = ctk.CTkFrame(self, fg_color=THEME["bg_sidebar"], height=28, corner_radius=0)
        self.footer.pack(fill="x", side="bottom")

        self.footer_status = ctk.CTkLabel(
            self.footer,
            text="SYSTEM INITIALIZED • ASYNC THREADS RUNNING",
            font=FONTS["mono_sm"],
            text_color=THEME["text_secondary"]
        )
        self.footer_status.pack(side="left", padx=16, pady=4)

        # Sound Alert Toggle
        self.sound_cb = ctk.CTkCheckBox(
            self.footer,
            text="AUDIO SENTINEL ALERTS",
            font=FONTS["mono_sm"],
            text_color=THEME["text_secondary"],
            fg_color=THEME["neon_green"],
            hover_color=THEME["neon_green_dim"],
            checkmark_color="#000000",
            width=16,
            height=16,
            command=self._toggle_sound
        )
        if self.sound_enabled:
            self.sound_cb.select()
        self.sound_cb.pack(side="right", padx=16, pady=4)

        self.footer_version = ctk.CTkLabel(
            self.footer,
            text="TYRELL CORP // OS v2.0",
            font=FONTS["mono_sm"],
            text_color=THEME["neon_green"]
        )
        self.footer_version.pack(side="right", padx=16, pady=4)

    # =========================================================================
    # CORE LOGIC & BACKGROUND THREADS
    # =========================================================================
    def _start_connection_loop(self):
        """Dedicated background thread for connecting & periodically polling metrics."""
        def monitor_worker():
            first_connect = True
            while self.is_monitoring:
                if not self.ssh.check_connection_health():
                    # Update UI to reconnecting state
                    self.dispatch_ui(lambda: self._update_connection_ui(False, "RECONNECTING..."))
                    ok, msg = self.ssh.connect(
                        host=self.cfg["host"],
                        port=self.cfg["port"],
                        user=self.cfg["user"],
                        password=self.cfg.get("password", ""),
                        key_path=self.cfg.get("key_path", ""),
                        timeout=4.0
                    )
                    if ok:
                        self.dispatch_ui(lambda: self._update_connection_ui(True, "ONLINE"))
                        if first_connect:
                            first_connect = False
                            # Start streaming journalctl logs
                            self._start_journal_stream()
                            # Auto-load the default preset in IDE
                            self.dispatch_ui(lambda: self._handle_ide_load(PRESET_FILES[0]))
                    else:
                        self.dispatch_ui(lambda m=msg: self._update_connection_ui(False, f"OFFLINE ({m[:30]})"))
                        time.sleep(3.0)
                        continue

                # Fetch Telemetry
                metrics = self.ssh.get_system_metrics(
                    project_dir=self.cfg["project_dir"],
                    service_name=self.cfg["service_name"]
                )
                self.dispatch_ui(lambda m=metrics: self._process_telemetry(m))
                time.sleep(self.cfg.get("poll_interval_sec", 3.0))

        thread = threading.Thread(target=monitor_worker, daemon=True)
        thread.start()

    def _update_connection_ui(self, connected: bool, status_text: str):
        if connected:
            self.conn_badge.set_status("ONLINE", THEME["neon_green"])
            self.telemetry_lbl.configure(
                text=f"{self.cfg['user']}@{self.cfg['host']} | {self.ssh.latency_ms:.1f} ms"
            )
            self._show_banner(False)
        else:
            color = THEME["neon_gold"] if "RECONNECTING" in status_text else THEME["neon_red"]
            self.conn_badge.set_status(status_text, color)
            self.telemetry_lbl.configure(text=f"{self.cfg['user']}@{self.cfg['host']} | OFFLINE")
            self._show_banner(True, status_text)

    def _process_telemetry(self, m: Dict[str, Any]):
        if not m.get("online", False):
            return

        # CPU Card
        cpu_val = m.get("cpu_pct", 0.0)
        self.card_cpu.update_val(cpu_val, detail="4x ARM Cortex-A53 @ 1.0 GHz")

        # RAM Card
        ram_pct = m.get("ram_pct", 0.0)
        ram_used = m.get("ram_used_mb", 0.0)
        ram_total = m.get("ram_total_mb", 0.0)
        self.card_ram.update_val(
            ram_pct,
            detail=f"Used: {ram_used:.0f} MB / Total: {ram_total:.0f} MB",
            custom_text=f"{ram_pct:.1f} %"
        )

        # Disk Card
        disk_pct = m.get("disk_pct", 0.0)
        disk_used = m.get("disk_used_gb", 0.0)
        disk_total = m.get("disk_total_gb", 0.0)
        self.card_disk.update_val(
            disk_pct,
            detail=f"{disk_used:.1f} GB / {disk_total:.1f} GB (/dev/mmcblk0p2)",
            custom_text=f"{disk_pct:.1f} %"
        )

        # Temp Card
        temp_c = m.get("temp_c", 0.0)
        status_note = "NORMAL" if temp_c < 60 else ("WARM" if temp_c < 72 else "CRITICAL THERMAL")
        self.card_temp.update_val(
            temp_c,
            detail=f"Status: {status_note} | vcgencmd",
            custom_text=f"{temp_c:.1f} °C"
        )

        # Service Status
        service = m.get("service", "unknown").lower()
        if service == "active":
            self.agent_status_badge.set_status("ACTIVE (RUNNING)", THEME["neon_green"])
        elif service == "inactive":
            self.agent_status_badge.set_status("INACTIVE (STOPPED)", THEME["neon_red"])
        else:
            self.agent_status_badge.set_status(f"SERVICE: {service.upper()}", THEME["neon_gold"])

        # Check for service drop alert
        if self.previous_service_state == "active" and service in ("inactive", "failed"):
            self._trigger_service_failure_alert(service)
        self.previous_service_state = service

        # Top processes
        procs = m.get("top_procs", [])
        if procs:
            lines = ["PID       %CPU   %MEM   COMMAND", "-" * 56]
            for p in procs:
                lines.append(f"{p['pid']:<9} {p['cpu']:<6} {p['mem']:<6} {p['comm']}")
            self.proc_textbox.delete("1.0", "end")
            self.proc_textbox.insert("1.0", "\n".join(lines))

        # SQLite Database stats
        db = m.get("db_stats", {})
        item_cnt = db.get("items", 0)
        sub_cnt = db.get("subscriptions", 0)
        self.db_items_card.update_val(min(item_cnt, 5000), detail=f"Total Database Rows: {item_cnt}", custom_text=f"{item_cnt}")
        self.db_subs_card.update_val(min(sub_cnt, 50), detail=f"Monitored Search Filters: {sub_cnt}", custom_text=f"{sub_cnt}")

        last_item = db.get("last_item")
        if last_item:
            info = f"TITLE: {last_item['title']}\nPRICE: {last_item['price']}\nTIMESTAMP: {last_item['time']}"
            self.last_item_lbl.configure(text=info, text_color=THEME["neon_green"])

        # Header ping
        self.telemetry_lbl.configure(
            text=f"{self.cfg['user']}@{self.cfg['host']} | {m.get('latency_ms', 0):.1f} ms | Uptime: {m.get('uptime_str', '--')}"
        )

    # =========================================================================
    # LOG STREAMING WORKER
    # =========================================================================
    def _start_journal_stream(self):
        """Launch background worker for continuous log streaming."""
        self.log_stream_stop_event.set()
        time.sleep(0.1)
        self.log_stream_stop_event.clear()

        def stream_worker():
            def on_line(line: str):
                self.dispatch_ui(lambda l=line: self.log_viewer.append_log_line(l))

            self.ssh.stream_journal_logs(
                service_name=self.cfg["service_name"],
                on_line_cb=on_line,
                stop_event=self.log_stream_stop_event,
                lines=80
            )

        thread = threading.Thread(target=stream_worker, daemon=True)
        thread.start()

    # =========================================================================
    # RESALE SERVICE MANAGEMENT
    # =========================================================================
    def _control_service(self, action: str):
        self.footer_status.configure(text=f"EXECUTING SYSTEMCTL {action.upper()}...", text_color=THEME["neon_gold"])
        
        def worker():
            ok, msg = self.ssh.manage_service(action, self.cfg["service_name"])
            def ui_callback():
                color = THEME["neon_green"] if ok else THEME["neon_red"]
                self.footer_status.configure(text=f"SERVICE {action.upper()}: {msg}", text_color=color)
                # Restart stream if restarted
                if action in ("start", "restart"):
                    self._start_journal_stream()
            self.dispatch_ui(ui_callback)

        threading.Thread(target=worker, daemon=True).start()

    def _trigger_service_failure_alert(self, state: str):
        """Audio and visual alarm when the bot service crashes or stops."""
        if self.sound_enabled and HAS_WINSOUND:
            try:
                winsound.Beep(1200, 300)
                winsound.Beep(800, 300)
            except Exception:
                pass
        self._show_banner(True, f"BOT SERVICE CRITICAL: State changed to {state.upper()}!")

    # =========================================================================
    # QUICK IDE / DEPLOYER ACTIONS
    # =========================================================================
    def _handle_ide_load(self, rel_path: str):
        self.footer_status.configure(text=f"DOWNLOADING {rel_path} OVER SFTP...", text_color=THEME["neon_gold"])

        def worker():
            ok, content = self.ssh.read_file(rel_path, self.cfg["project_dir"])
            def ui_cb():
                if ok:
                    self.code_editor.set_content(rel_path, content)
                    self.footer_status.configure(text=f"LOADED {rel_path} READY TO EDIT", text_color=THEME["neon_green"])
                else:
                    self.code_editor.set_deploy_status(False, f"READ FAILED: {content[:30]}")
                    self.footer_status.configure(text=f"SFTP ERROR: {content}", text_color=THEME["neon_red"])
            self.dispatch_ui(ui_cb)

        threading.Thread(target=worker, daemon=True).start()

    def _handle_ide_save(self, rel_path: str, content: str):
        self.footer_status.configure(text=f"SAVING & DEPLOYING {rel_path} TO PI...", text_color=THEME["neon_gold"])

        def worker():
            # 1. SFTP Write with backup
            ok, msg = self.ssh.write_file(rel_path, content, self.cfg["project_dir"], make_backup=True)
            if not ok:
                self.dispatch_ui(lambda: self.code_editor.set_deploy_status(False, msg))
                return

            # 2. Restart Bot Service
            s_ok, s_msg = self.ssh.manage_service("restart", self.cfg["service_name"])
            
            def ui_cb():
                if s_ok:
                    self.code_editor.set_deploy_status(True, f"DEPLOYED & SERVICE RESTARTED")
                    self.footer_status.configure(text=f"SUCCESS: {rel_path} deployed + resale_bot restarted", text_color=THEME["neon_green"])
                    self._start_journal_stream()
                else:
                    self.code_editor.set_deploy_status(False, f"SAVED, BUT RESTART FAILED: {s_msg[:30]}")
                    self.footer_status.configure(text=f"RESTART ERROR: {s_msg}", text_color=THEME["neon_red"])
            self.dispatch_ui(ui_cb)

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # SHELL & QUICK MACROS
    # =========================================================================
    def _submit_shell_cmd(self):
        cmd = self.shell_entry.get().strip()
        if not cmd:
            return
        self.shell_entry.delete(0, "end")
        self.macro_history.append(cmd)
        
        self.shell_output.insert("end", f"\ntyrell@pi:~$ {cmd}\n", "tag_prompt")
        self.shell_output.see("end")

        def worker():
            code, out, err = self.ssh.exec_command(cmd, timeout=30.0)
            def ui_cb():
                if out:
                    self.shell_output.insert("end", out)
                if err:
                    self.shell_output.insert("end", f"[STDERR]\n{err}", "tag_err")
                self.shell_output.insert("end", f"[EXIT CODE: {code}]\n", "tag_res" if code == 0 else "tag_err")
                self.shell_output.see("end")
            self.dispatch_ui(ui_cb)

        threading.Thread(target=worker, daemon=True).start()

    def _execute_and_stream_macro(self, title: str, cmd: str):
        self.tabs.set("  ⚡ QUICK MACROS & SHELL  ")
        self.shell_output.insert("end", f"\n[MACRO: {title.upper()}] $ {cmd}\n", "tag_prompt")
        self.shell_output.see("end")

        def worker():
            code, out, err = self.ssh.exec_command(cmd, timeout=45.0)
            def ui_cb():
                if out:
                    self.shell_output.insert("end", out)
                if err:
                    self.shell_output.insert("end", err, "tag_err")
                self.shell_output.insert("end", f"[COMPLETED WITH CODE {code}]\n", "tag_res" if code == 0 else "tag_err")
                self.shell_output.see("end")
            self.dispatch_ui(ui_cb)

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # LAN RADAR
    # =========================================================================
    def _start_network_scan(self):
        self.radar_status_lbl.configure(text="SCANNING SUBNET VIA ARP & PORT PROBING...", text_color=THEME["neon_cyan"])
        self.radar_output.delete("1.0", "end")
        self.radar_output.insert("1.0", "IP ADDRESS       MAC ADDRESS         STATUS     OPEN PORTS   HOST\n----------------------------------------------------------------------\n", "tag_head")

        def on_device(dev: dict):
            def ui_cb():
                ip = dev.get("ip", "")
                mac = dev.get("mac", "")
                status = dev.get("status", "")
                ports = dev.get("open_ports", "")
                host = dev.get("hostname", "")
                line = f"{ip:<16} {mac:<19} {status:<10} {ports:<12} {host}\n"
                
                # Highlight Raspberry Pi
                tag = "tag_pi" if ip == self.cfg["host"] else "tag_node"
                if ip == self.cfg["host"]:
                    line = f"{ip:<16} {mac:<19} [PI ZERO]   {ports:<12} RASPBERRY PI\n"
                self.radar_output.insert("end", line, tag)
                self.radar_output.see("end")
            self.dispatch_ui(ui_cb)

        def on_finish(total: int):
            def ui_cb():
                self.radar_status_lbl.configure(text=f"SCAN FINISHED. Discovered {total} active nodes.", text_color=THEME["neon_green"])
            self.dispatch_ui(ui_cb)

        NetworkScanner.scan_network_async(on_device, on_finish)

    # =========================================================================
    # SYSTEM ACTIONS (REBOOT / SHUTDOWN)
    # =========================================================================
    def _confirm_system_action(self, action_name: str, cmd: str):
        modal = ctk.CTkToplevel(self)
        modal.title(f"CONFIRM {action_name}")
        modal.geometry("400x190")
        modal.resizable(False, False)
        modal.configure(fg_color=THEME["bg_card"])
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(
            modal,
            text=f"⚠️ CRITICAL SYSTEM ACTION: {action_name}",
            font=FONTS["header"],
            text_color=THEME["neon_red"] if action_name == "SHUTDOWN" else THEME["neon_gold"]
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            modal,
            text=f"Are you sure you want to execute '{cmd}'\non Raspberry Pi Zero 2 W ({self.cfg['host']})?",
            font=FONTS["mono_sm"],
            text_color=THEME["text_primary"],
            justify="center"
        ).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)

        ctk.CTkButton(
            btn_frame,
            text="CANCEL",
            width=140,
            fg_color="#2A2A38",
            hover_color="#3A3A4E",
            command=modal.destroy
        ).pack(side="left", padx=10)

        def proceed():
            modal.destroy()
            self.footer_status.configure(text=f"EXECUTING {action_name}...", text_color=THEME["neon_red"])
            self.ssh.exec_command(cmd, timeout=5.0)

        ctk.CTkButton(
            btn_frame,
            text=f"YES, {action_name}",
            width=140,
            fg_color="#8B1A24" if action_name == "SHUTDOWN" else "#736412",
            hover_color="#A8202D" if action_name == "SHUTDOWN" else "#8C7B16",
            command=proceed
        ).pack(side="right", padx=10)

    # =========================================================================
    # SETTINGS MODAL
    # =========================================================================
    def _open_settings_dialog(self):
        modal = ctk.CTkToplevel(self)
        modal.title("TYRELL CONFIGURATION")
        modal.geometry("440x480")
        modal.resizable(False, False)
        modal.configure(fg_color=THEME["bg_card"])
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(modal, text="// SSH & SYSTEM CONFIGURATION", font=FONTS["header"], text_color=THEME["neon_green"]).pack(pady=(16, 12))

        entries = {}
        fields = [
            ("Host IP", "host", self.cfg["host"]),
            ("SSH Port", "port", str(self.cfg["port"])),
            ("Username", "user", self.cfg["user"]),
            ("Private Key Path", "key_path", self.cfg.get("key_path", "")),
            ("Project Directory", "project_dir", self.cfg["project_dir"]),
            ("Service Unit Name", "service_name", self.cfg["service_name"])
        ]

        for label_text, key, initial in fields:
            box = ctk.CTkFrame(modal, fg_color="transparent")
            box.pack(fill="x", padx=24, pady=4)
            ctk.CTkLabel(box, text=label_text, font=FONTS["mono_sm"], text_color=THEME["text_secondary"], width=130, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(box, font=FONTS["mono_sm"], height=28, fg_color=THEME["bg_input"], border_color=THEME["border_subtle"])
            ent.insert(0, initial)
            ent.pack(side="right", fill="x", expand=True)
            entries[key] = ent

        def save_and_close():
            self.cfg["host"] = entries["host"].get().strip()
            self.cfg["port"] = int(entries["port"].get().strip() or 22)
            self.cfg["user"] = entries["user"].get().strip()
            self.cfg["key_path"] = entries["key_path"].get().strip()
            self.cfg["project_dir"] = entries["project_dir"].get().strip()
            self.cfg["service_name"] = entries["service_name"].get().strip()
            save_config(self.cfg)
            modal.destroy()
            self._trigger_reconnect()

        btn_box = ctk.CTkFrame(modal, fg_color="transparent")
        btn_box.pack(fill="x", padx=24, pady=20)

        ctk.CTkButton(btn_box, text="CANCEL", width=160, fg_color="#2A2A38", command=modal.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btn_box, text="SAVE & RECONNECT", width=180, fg_color="#006629", hover_color="#008837", command=save_and_close).pack(side="right", padx=6)

    def _trigger_reconnect(self):
        self.conn_badge.set_status("RECONNECTING...", THEME["neon_gold"])
        threading.Thread(target=lambda: self.ssh.disconnect(), daemon=True).start()

    def _toggle_sound(self):
        self.sound_enabled = bool(self.sound_cb.get())
        self.cfg["sound_alerts"] = self.sound_enabled
        save_config(self.cfg)

    def _on_close(self):
        self.is_monitoring = False
        self.log_stream_stop_event.set()
        try:
            self.ssh.disconnect()
        except Exception:
            pass
        self.destroy()
        sys.exit(0)


if __name__ == "__main__":
    app = TyrellControlCenterApp()
    app.mainloop()
