"""
TYRELL // CONTROL CENTER v2.0 - Configuration Module
Cyberpunk styling parameters, SSH connection defaults, and paths.
"""
import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tyrell_config.json")

# Default SSH Configuration
DEFAULT_CONFIG = {
    "host": "192.168.0.108",
    "port": 22,
    "user": "tyrell",
    "password": "",
    "key_path": os.path.expanduser("~/.ssh/id_ed25519"),
    "project_dir": "/home/tyrell/resale-agent",
    "service_name": "resale_bot.service",
    "poll_interval_sec": 3.0,
    "sound_alerts": True,
    "auto_reconnect": True,
    "network_subnet": "192.168.0"
}

def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                config.update(user_cfg)
        except Exception:
            pass
    return config

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save config: {e}")

# Color Palette - High-tech Cyberpunk
THEME = {
    "bg_dark": "#0B0C10",         # Deep obsidian void
    "bg_sidebar": "#111218",      # Navigation frame
    "bg_card": "#171822",         # Card background
    "bg_card_alt": "#1E202C",     # Inner container / input field
    "bg_input": "#13141C",        # Text entry / console background
    "border_subtle": "#252738",   # Subtle borders
    "border_accent": "#00FF66",   # Neon green glow border
    
    # Neon Accent Colors
    "neon_green": "#00FF66",      # Operational / Primary accent
    "neon_green_dim": "#00993D",  # Muted green
    "neon_cyan": "#00E5FF",       # Telemetry / Secondary accent
    "neon_gold": "#E2B93B",       # Warning / Notice
    "neon_red": "#FF3333",        # Critical / Alarm
    "neon_purple": "#BD00FF",     # Special / AI / Scanner
    
    # Text
    "text_primary": "#F2F4F8",    # Bright cyber white
    "text_secondary": "#8A8D9F",  # Technical grey
    "text_muted": "#55586D",      # Low-priority hints
    "text_green": "#00FF66",
    "text_cyan": "#00E5FF",
    "text_gold": "#E2B93B",
    "text_red": "#FF3333",
}

# Typography
FONTS = {
    "title": ("Consolas", 18, "bold"),
    "header": ("Consolas", 14, "bold"),
    "sub": ("Consolas", 11, "bold"),
    "mono": ("Consolas", 11),
    "mono_sm": ("Consolas", 10),
    "mono_lg": ("Consolas", 13),
    "metric_val": ("Consolas", 24, "bold"),
    "metric_val_lg": ("Consolas", 32, "bold"),
    "label": ("Segoe UI", 11),
    "button": ("Consolas", 12, "bold"),
    "button_sm": ("Consolas", 10, "bold")
}

# Quick Editor Preset Files
PRESET_FILES = [
    "scrapers/vinted.py",
    "scrapers/bazos.py",
    "scrapers/base.py",
    ".env",
    "main.py",
    "monitor.py",
    "config.py",
    "handlers.py",
    "database.py",
    "notifier.py",
    "pipeline.py",
    "resale_bot.service"
]
