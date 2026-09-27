"""
TYRELL // CONTROL CENTER v2.0 - Cyberpunk UI Components
Reusable widgets, metric cards with sparkline history, log terminal with error parser,
toast notification system, and code editor with line counter.
"""
import re
import os
import time
import math
from typing import Callable, Optional, Dict, List
import customtkinter as ctk
from config import THEME, FONTS


class CyberCard(ctk.CTkFrame):
    """Futuristic card container with header and subtle neon border."""
    def __init__(self, master, title: str = "", subtitle: str = "", header_color: str = THEME["neon_green"], **kwargs):
        super().__init__(
            master,
            fg_color=THEME["bg_card"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border_subtle"],
            **kwargs
        )
        self.header_color = header_color
        
        if title:
            self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.header_frame.pack(fill="x", padx=14, pady=(10, 4))
            
            self.title_lbl = ctk.CTkLabel(
                self.header_frame,
                text=title,
                font=FONTS["sub"],
                text_color=self.header_color,
                anchor="w"
            )
            self.title_lbl.pack(side="left")
            
            if subtitle:
                self.sub_lbl = ctk.CTkLabel(
                    self.header_frame,
                    text=subtitle,
                    font=FONTS["mono_sm"],
                    text_color=THEME["text_secondary"],
                    anchor="e"
                )
                self.sub_lbl.pack(side="right")
                
            self.divider = ctk.CTkFrame(self, fg_color=THEME["border_subtle"], height=1)
            self.divider.pack(fill="x", padx=12, pady=(0, 8))


class SparklineCanvas(ctk.CTkFrame):
    """Mini sparkline chart showing last N data points as a glowing line graph."""
    def __init__(self, master, max_points: int = 40, height: int = 36, line_color: str = THEME["neon_green"], **kwargs):
        super().__init__(master, fg_color="transparent", height=height, **kwargs)
        self.max_points = max_points
        self.line_color = line_color
        self.data_points: List[float] = []
        
        import tkinter as tk
        self.canvas = tk.Canvas(
            self,
            bg=THEME["bg_card"],
            highlightthickness=0,
            height=height
        )
        self.canvas.pack(fill="x", expand=True)
        self.bind("<Configure>", self._on_resize)

    def add_point(self, value: float):
        self.data_points.append(value)
        if len(self.data_points) > self.max_points:
            self.data_points.pop(0)
        self._redraw()

    def _on_resize(self, event=None):
        self._redraw()

    def _redraw(self):
        self.canvas.delete("all")
        pts = self.data_points
        if len(pts) < 2:
            return

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 5:
            return

        min_v = min(pts) * 0.9
        max_v = max(pts) * 1.1 if max(pts) > 0 else 1.0
        if max_v == min_v:
            max_v = min_v + 1.0

        pad_y = 3
        step_x = w / (len(pts) - 1)

        coords = []
        for i, v in enumerate(pts):
            x = i * step_x
            y = pad_y + (1.0 - (v - min_v) / (max_v - min_v)) * (h - 2 * pad_y)
            coords.append((x, y))

        # Draw subtle fill under the line
        fill_coords = list(coords) + [(w, h), (0, h)]
        flat_fill = [c for pt in fill_coords for c in pt]
        # Dim version of line color for fill
        dim_color = self._dim_color(self.line_color, 0.12)
        self.canvas.create_polygon(flat_fill, fill=dim_color, outline="")

        # Draw line segments
        flat_line = [c for pt in coords for c in pt]
        self.canvas.create_line(flat_line, fill=self.line_color, width=1.5, smooth=True)

        # Draw latest point dot
        if coords:
            lx, ly = coords[-1]
            self.canvas.create_oval(lx - 2, ly - 2, lx + 2, ly + 2, fill=self.line_color, outline="")

    @staticmethod
    def _dim_color(hex_color: str, alpha: float) -> str:
        """Blend hex color with dark background at given opacity."""
        bg_r, bg_g, bg_b = 0x17, 0x18, 0x22  # THEME bg_card
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        nr = int(bg_r * (1 - alpha) + r * alpha)
        ng = int(bg_g * (1 - alpha) + g * alpha)
        nb = int(bg_b * (1 - alpha) + b * alpha)
        return f"#{nr:02x}{ng:02x}{nb:02x}"


class CyberMetricCard(CyberCard):
    """High-tech telemetry card with large readout, color-morphing progress bar, and sparkline history."""
    def __init__(self, master, title: str, unit: str = "%", max_val: float = 100.0, icon: str = "⚡",
                 sparkline_color: str = "", **kwargs):
        super().__init__(master, title=f"{icon} {title}", **kwargs)
        self.unit = unit
        self.max_val = max_val
        
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        
        # Top row: Big Readout + Timestamp
        self.readout_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.readout_frame.pack(fill="x")
        
        self.val_label = ctk.CTkLabel(
            self.readout_frame,
            text=f"-- {self.unit}",
            font=FONTS["metric_val"],
            text_color=THEME["text_muted"],
            anchor="w"
        )
        self.val_label.pack(side="left")
        
        self.ts_label = ctk.CTkLabel(
            self.readout_frame,
            text="",
            font=("Consolas", 8),
            text_color=THEME["text_muted"],
            anchor="e"
        )
        self.ts_label.pack(side="right", pady=(8, 0))
        
        # Cyber Progress Bar
        self.progress = ctk.CTkProgressBar(
            self.content_frame,
            orientation="horizontal",
            height=10,
            corner_radius=4,
            fg_color=THEME["bg_card_alt"],
            progress_color=THEME["neon_green"]
        )
        self.progress.set(0.0)
        self.progress.pack(fill="x", pady=(4, 3))
        
        # Sparkline mini-chart
        spark_color = sparkline_color or THEME["neon_green"]
        self.sparkline = SparklineCanvas(self.content_frame, max_points=40, height=32, line_color=spark_color)
        self.sparkline.pack(fill="x", pady=(2, 2))
        
        # Extra telemetry detail line
        self.sub_detail = ctk.CTkLabel(
            self.content_frame,
            text="ACQUIRING TELEMETRY...",
            font=FONTS["mono_sm"],
            text_color=THEME["text_secondary"],
            anchor="w"
        )
        self.sub_detail.pack(anchor="w")

    def update_val(self, val: float, detail: str = "", custom_text: str = ""):
        ratio = max(0.0, min(1.0, val / self.max_val))
        self.progress.set(ratio)
        
        # Determine warning/critical thresholds
        if ratio >= 0.85:
            color = THEME["neon_red"]
        elif ratio >= 0.65:
            color = THEME["neon_gold"]
        else:
            color = THEME["neon_green"]
            
        self.progress.configure(progress_color=color)
        display_str = custom_text if custom_text else f"{val:.1f} {self.unit}"
        self.val_label.configure(text=display_str, text_color=color)
        
        if detail:
            self.sub_detail.configure(text=detail)
        
        # Feed sparkline with current value
        self.sparkline.add_point(val)
        
        # Update timestamp
        now = time.strftime("%H:%M:%S")
        self.ts_label.configure(text=now)


class CyberStatusBadge(ctk.CTkFrame):
    """Pill badge showing connection or service state with pulse animation."""
    def __init__(self, master, initial_text: str = "OFFLINE", initial_color: str = THEME["neon_red"], **kwargs):
        super().__init__(
            master,
            fg_color=THEME["bg_card_alt"],
            corner_radius=12,
            border_width=1,
            border_color=initial_color,
            **kwargs
        )
        self._current_color = initial_color
        self._pulse_phase = 0
        self._pulse_active = False
        
        self.dot = ctk.CTkLabel(
            self,
            text="●",
            font=("Consolas", 14, "bold"),
            text_color=initial_color
        )
        self.dot.pack(side="left", padx=(8, 4), pady=2)
        
        self.lbl = ctk.CTkLabel(
            self,
            text=initial_text,
            font=FONTS["mono_sm"],
            text_color=THEME["text_primary"]
        )
        self.lbl.pack(side="left", padx=(0, 10), pady=2)

    def set_status(self, text: str, color: str):
        self._current_color = color
        self.configure(border_color=color)
        self.dot.configure(text_color=color)
        self.lbl.configure(text=text)
        
        # Enable pulse animation for "ONLINE" state
        if "ONLINE" in text.upper() or "ACTIVE" in text.upper():
            if not self._pulse_active:
                self._pulse_active = True
                self._animate_pulse()
        else:
            self._pulse_active = False

    def _animate_pulse(self):
        """Soft breathing glow pulse on the status dot."""
        if not self._pulse_active:
            self.dot.configure(text_color=self._current_color)
            return
        self._pulse_phase = (self._pulse_phase + 1) % 60
        t = self._pulse_phase / 60.0
        # Sinusoidal brightness modulation
        brightness = 0.55 + 0.45 * math.sin(t * 2 * math.pi)
        pulsed_color = self._modulate_color(self._current_color, brightness)
        self.dot.configure(text_color=pulsed_color)
        self.after(50, self._animate_pulse)

    @staticmethod
    def _modulate_color(hex_color: str, factor: float) -> str:
        try:
            r = int(int(hex_color[1:3], 16) * factor)
            g = int(int(hex_color[3:5], 16) * factor)
            b = int(int(hex_color[5:7], 16) * factor)
            return f"#{min(r, 255):02x}{min(g, 255):02x}{min(b, 255):02x}"
        except Exception:
            return hex_color


class CyberToast(ctk.CTkFrame):
    """Floating notification toast that auto-dismisses after a timeout."""
    def __init__(self, master, message: str, level: str = "info", duration_ms: int = 4000):
        colors = {
            "info":    (THEME["neon_green"], "#0D2818"),
            "warn":    (THEME["neon_gold"], "#2D2211"),
            "error":   (THEME["neon_red"], "#2D1115"),
            "success": (THEME["neon_cyan"], "#0D1F28"),
        }
        fg, bg = colors.get(level, colors["info"])
        
        super().__init__(
            master,
            fg_color=bg,
            corner_radius=8,
            border_width=1,
            border_color=fg
        )
        
        icon_map = {"info": "ℹ", "warn": "⚠", "error": "✖", "success": "✓"}
        
        ctk.CTkLabel(
            self,
            text=icon_map.get(level, "ℹ"),
            font=("Consolas", 14, "bold"),
            text_color=fg,
            width=20
        ).pack(side="left", padx=(10, 4), pady=6)
        
        ctk.CTkLabel(
            self,
            text=message,
            font=FONTS["mono_sm"],
            text_color=THEME["text_primary"],
            anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=(0, 10), pady=6)
        
        ts = time.strftime("%H:%M:%S")
        ctk.CTkLabel(
            self,
            text=ts,
            font=("Consolas", 8),
            text_color=THEME["text_muted"]
        ).pack(side="right", padx=10, pady=6)
        
        # Schedule auto-dismiss
        self.after(duration_ms, self._dismiss)
    
    def _dismiss(self):
        try:
            self.pack_forget()
            self.destroy()
        except Exception:
            pass


class CyberLogViewer(ctk.CTkFrame):
    """
    Live terminal log viewer with automatic error parsing:
    Highlights 401 Unauthorized, 404 Not Found in neon red, warnings in gold.
    Includes search/filter, autoscroll toggle, error counters, and total error badge.
    """
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=THEME["bg_card"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border_subtle"],
            **kwargs
        )
        self.auto_scroll = True
        self.filter_query = ""
        self.count_401 = 0
        self.count_404 = 0
        self.count_errors = 0
        self.total_lines = 0
        self.raw_lines = []

        # Top Control Bar
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=10, pady=8)

        # Title
        self.title_lbl = ctk.CTkLabel(
            self.top_bar,
            text=">_ LIVE JOURNAL TERMINAL",
            font=FONTS["sub"],
            text_color=THEME["neon_green"]
        )
        self.title_lbl.pack(side="left", padx=(0, 10))

        # Error stat badges
        self.badge_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.badge_frame.pack(side="left", padx=5)

        self.stat_lines_lbl = ctk.CTkLabel(
            self.badge_frame,
            text="[LINES: 0]",
            font=FONTS["mono_sm"],
            text_color=THEME["neon_cyan"]
        )
        self.stat_lines_lbl.pack(side="left", padx=4)

        self.stat_401_lbl = ctk.CTkLabel(
            self.badge_frame,
            text="[401: 0]",
            font=FONTS["mono_sm"],
            text_color=THEME["neon_red"]
        )
        self.stat_401_lbl.pack(side="left", padx=4)

        self.stat_404_lbl = ctk.CTkLabel(
            self.badge_frame,
            text="[404: 0]",
            font=FONTS["mono_sm"],
            text_color=THEME["neon_gold"]
        )
        self.stat_404_lbl.pack(side="left", padx=4)

        self.stat_err_lbl = ctk.CTkLabel(
            self.badge_frame,
            text="[ERR: 0]",
            font=FONTS["mono_sm"],
            text_color="#FF6666"
        )
        self.stat_err_lbl.pack(side="left", padx=4)

        # Actions (Right side)
        self.clear_btn = ctk.CTkButton(
            self.top_bar,
            text="CLEAR",
            width=65,
            height=26,
            font=FONTS["button_sm"],
            fg_color="#2A2A38",
            hover_color="#3A3A4E",
            command=self.clear_logs
        )
        self.clear_btn.pack(side="right", padx=3)

        self.copy_btn = ctk.CTkButton(
            self.top_bar,
            text="COPY",
            width=65,
            height=26,
            font=FONTS["button_sm"],
            fg_color="#2A2A38",
            hover_color="#3A3A4E",
            command=self.copy_to_clipboard
        )
        self.copy_btn.pack(side="right", padx=3)

        self.scroll_cb = ctk.CTkCheckBox(
            self.top_bar,
            text="AUTOSCROLL",
            font=FONTS["mono_sm"],
            text_color=THEME["text_secondary"],
            fg_color=THEME["neon_green"],
            hover_color=THEME["neon_green_dim"],
            checkmark_color="#000000",
            width=18,
            height=18,
            command=self._on_scroll_toggle
        )
        self.scroll_cb.select()
        self.scroll_cb.pack(side="right", padx=10)

        # Search / Filter Bar
        self.search_entry = ctk.CTkEntry(
            self.top_bar,
            placeholder_text="Filter logs...",
            width=160,
            height=26,
            font=FONTS["mono_sm"],
            fg_color=THEME["bg_input"],
            border_color=THEME["border_subtle"]
        )
        self.search_entry.pack(side="right", padx=5)
        self.search_entry.bind("<KeyRelease>", self._on_filter_changed)

        # Text Box Container
        self.textbox = ctk.CTkTextbox(
            self,
            font=FONTS["mono"],
            fg_color=THEME["bg_dark"],
            text_color=THEME["text_primary"],
            wrap="none",
            corner_radius=6,
            border_width=1,
            border_color=THEME["border_subtle"]
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Setup Tag Styles
        self._configure_tags()

    def _configure_tags(self):
        """Configure color tags for log parsing."""
        tb = self.textbox
        tb.tag_config("tag_401", foreground="#FF4D4D", background="#3D1117")
        tb.tag_config("tag_404", foreground="#FF9933", background="#3D2611")
        tb.tag_config("tag_error", foreground="#FF3333")
        tb.tag_config("tag_warn", foreground="#E2B93B")
        tb.tag_config("tag_info", foreground="#00FF66")
        tb.tag_config("tag_dim", foreground="#5E6377")

    def append_log_line(self, line: str):
        """Append line, analyze errors, and apply formatting."""
        self.raw_lines.append(line)
        self.total_lines += 1
        if len(self.raw_lines) > 2000:
            self.raw_lines.pop(0)

        # Error counter increments
        lower = line.lower()
        if "401" in line and ("unauthorized" in lower or "got 401" in lower or "401 response" in lower):
            self.count_401 += 1
            self.stat_401_lbl.configure(text=f"[401: {self.count_401}]")
        if "404" in lower and ("not found" in lower or "404" in lower):
            self.count_404 += 1
            self.stat_404_lbl.configure(text=f"[404: {self.count_404}]")
        if "error" in lower or "exception" in lower or "traceback" in lower or "critical" in lower:
            self.count_errors += 1
            self.stat_err_lbl.configure(text=f"[ERR: {self.count_errors}]")
        
        self.stat_lines_lbl.configure(text=f"[LINES: {self.total_lines}]")

        # Check filter
        if self.filter_query and (self.filter_query.lower() not in line.lower()):
            return

        self._render_line(line)

    def _render_line(self, line: str):
        tb = self.textbox
        tag = None
        lower_line = line.lower()

        if "401 unauthorized" in lower_line or "got 401" in lower_line or "401 response" in lower_line:
            tag = "tag_401"
        elif "404 not found" in lower_line or "404" in lower_line:
            tag = "tag_404"
        elif "error" in lower_line or "critical" in lower_line or "exception" in lower_line or "traceback" in lower_line:
            tag = "tag_error"
        elif "warning" in lower_line or "warn" in lower_line:
            tag = "tag_warn"
        elif "info" in lower_line:
            tag = "tag_info"

        if tag:
            tb.insert("end", line + "\n", tag)
        else:
            tb.insert("end", line + "\n")

        if self.auto_scroll:
            tb.see("end")

    def _on_scroll_toggle(self):
        self.auto_scroll = bool(self.scroll_cb.get())

    def _on_filter_changed(self, event=None):
        self.filter_query = self.search_entry.get().strip()
        self.textbox.delete("1.0", "end")
        for line in self.raw_lines[-500:]:
            if not self.filter_query or self.filter_query.lower() in line.lower():
                self._render_line(line)

    def clear_logs(self):
        self.textbox.delete("1.0", "end")
        self.raw_lines.clear()
        self.count_401 = 0
        self.count_404 = 0
        self.count_errors = 0
        self.total_lines = 0
        self.stat_401_lbl.configure(text="[401: 0]")
        self.stat_404_lbl.configure(text="[404: 0]")
        self.stat_err_lbl.configure(text="[ERR: 0]")
        self.stat_lines_lbl.configure(text="[LINES: 0]")

    def copy_to_clipboard(self):
        content = self.textbox.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(content)


class CyberCodeEditor(ctk.CTkFrame):
    """
    In-app IDE for Quick Editing & One-Click Deploy over SFTP.
    Features: file selector, keyboard shortcuts (Ctrl+S), byte counter, diff indicator.
    """
    def __init__(self, master, on_load_file: Callable[[str], None], on_save_file: Callable[[str, str], None], **kwargs):
        super().__init__(
            master,
            fg_color=THEME["bg_card"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border_subtle"],
            **kwargs
        )
        self.on_load_file = on_load_file
        self.on_save_file = on_save_file
        self.current_file = ""
        self._original_content = ""
        self._is_modified = False

        # Top Control Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=12, pady=10)

        # File Select OptionMenu
        self.file_label = ctk.CTkLabel(self.header, text="TARGET FILE:", font=FONTS["sub"], text_color=THEME["neon_cyan"])
        self.file_label.pack(side="left", padx=(0, 8))

        from config import PRESET_FILES
        self.file_picker = ctk.CTkOptionMenu(
            self.header,
            values=PRESET_FILES,
            width=200,
            height=28,
            font=FONTS["mono_sm"],
            fg_color=THEME["bg_card_alt"],
            button_color=THEME["border_subtle"],
            button_hover_color="#36394D",
            command=self._on_preset_picked
        )
        self.file_picker.pack(side="left", padx=(0, 10))

        # Load Button
        self.load_btn = ctk.CTkButton(
            self.header,
            text="📥 ЗАГРУЗИТЬ КОД",
            font=FONTS["button_sm"],
            width=140,
            height=28,
            fg_color="#232738",
            hover_color="#333952",
            border_width=1,
            border_color=THEME["neon_cyan"],
            text_color=THEME["neon_cyan"],
            command=self._handle_load
        )
        self.load_btn.pack(side="left", padx=4)

        # Save & Reload Button
        self.save_btn = ctk.CTkButton(
            self.header,
            text="⚡ SAVE & RELOAD",
            font=FONTS["button_sm"],
            width=150,
            height=28,
            fg_color="#006629",
            hover_color="#008837",
            border_width=1,
            border_color=THEME["neon_green"],
            text_color="#FFFFFF",
            command=self._handle_save
        )
        self.save_btn.pack(side="left", padx=4)

        # Modified indicator
        self.mod_lbl = ctk.CTkLabel(
            self.header,
            text="",
            font=("Consolas", 10, "bold"),
            text_color=THEME["neon_gold"]
        )
        self.mod_lbl.pack(side="left", padx=4)

        # Status / Path label
        self.status_lbl = ctk.CTkLabel(
            self.header,
            text="READY",
            font=FONTS["mono_sm"],
            text_color=THEME["text_secondary"]
        )
        self.status_lbl.pack(side="right", padx=10)

        # Info bar (line count, byte size)
        self.info_bar = ctk.CTkFrame(self, fg_color="transparent", height=20)
        self.info_bar.pack(fill="x", padx=12)
        
        self.line_count_lbl = ctk.CTkLabel(
            self.info_bar,
            text="LINES: 0 | BYTES: 0",
            font=("Consolas", 9),
            text_color=THEME["text_muted"]
        )
        self.line_count_lbl.pack(side="left")

        self.encoding_lbl = ctk.CTkLabel(
            self.info_bar,
            text="UTF-8 | LF",
            font=("Consolas", 9),
            text_color=THEME["text_muted"]
        )
        self.encoding_lbl.pack(side="right")

        # Editor Textbox
        self.editor = ctk.CTkTextbox(
            self,
            font=FONTS["mono"],
            fg_color=THEME["bg_dark"],
            text_color=THEME["text_primary"],
            wrap="none",
            corner_radius=6,
            border_width=1,
            border_color=THEME["border_subtle"],
            undo=True
        )
        self.editor.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        
        # Keyboard shortcut: Ctrl+S to save
        self.editor.bind("<Control-s>", lambda e: self._handle_save())
        
        # Track modifications
        self.editor.bind("<KeyRelease>", self._on_content_changed)

    def _on_preset_picked(self, choice: str):
        self.current_file = choice

    def _handle_load(self):
        target = self.file_picker.get()
        if target:
            self.current_file = target
            self.status_lbl.configure(text=f"FETCHING {target}...", text_color=THEME["neon_gold"])
            self.on_load_file(target)

    def _handle_save(self):
        target = self.current_file or self.file_picker.get()
        content = self.editor.get("1.0", "end-1c")
        if target:
            self.status_lbl.configure(text="DEPLOYING TO PI...", text_color=THEME["neon_gold"])
            self.on_save_file(target, content)

    def _on_content_changed(self, event=None):
        """Track if editor content differs from the loaded original."""
        current = self.editor.get("1.0", "end-1c")
        line_count = current.count("\n") + 1
        byte_count = len(current.encode("utf-8"))
        self.line_count_lbl.configure(text=f"LINES: {line_count} | BYTES: {byte_count:,}")
        
        modified = (current != self._original_content) if self._original_content else False
        if modified and not self._is_modified:
            self._is_modified = True
            self.mod_lbl.configure(text="● MODIFIED")
        elif not modified and self._is_modified:
            self._is_modified = False
            self.mod_lbl.configure(text="")

    def set_content(self, filename: str, content: str):
        self.current_file = filename
        self._original_content = content
        self._is_modified = False
        self.mod_lbl.configure(text="")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        size_kb = len(content.encode('utf-8')) / 1024.0
        line_count = content.count("\n") + 1
        self.status_lbl.configure(text=f"LOADED: {filename} ({size_kb:.1f} KB)", text_color=THEME["neon_green"])
        self.line_count_lbl.configure(text=f"LINES: {line_count} | BYTES: {len(content.encode('utf-8')):,}")

    def set_deploy_status(self, success: bool, msg: str):
        color = THEME["neon_green"] if success else THEME["neon_red"]
        self.status_lbl.configure(text=msg.upper(), text_color=color)
        if success:
            # Reset modification tracking after successful deploy
            self._original_content = self.editor.get("1.0", "end-1c")
            self._is_modified = False
            self.mod_lbl.configure(text="")
