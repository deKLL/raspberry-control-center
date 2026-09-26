import customtkinter as ctk
import subprocess

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

app = ctk.CTk()
app.title("Tyrell Dashboard")
app.geometry("340x550")
app.resizable(False, False)
app.attributes("-alpha", 0.95)

def launch_ssh(cmd=None, keep_open=True):
    if cmd:
        # Используем && bash вместо ; exec bash, чтобы не триггерить разделитель команд в Windows Terminal
        remote_cmd = f"{cmd} && bash" if keep_open else cmd
        subprocess.Popen(["wt", "-p", "Command Prompt", "ssh", "-t", "tyrell@192.168.0.108", remote_cmd])
    else:
        subprocess.Popen(["wt", "-p", "Command Prompt", "ssh", "tyrell@192.168.0.108"])

# --- ЗАГОЛОВОК ---
ctk.CTkLabel(app, text="TYRELL // ADMIN", font=("Consolas", 20, "bold"), text_color="#00FF41").pack(pady=(20, 10))
btn_style = {"width": 260, "height": 32, "font": ("Consolas", 12), "corner_radius": 6}

# --- БЛОК 1: RASPBERRY PI (СИСТЕМА) ---
frame_sys = ctk.CTkFrame(app, fg_color="#1a1a1a", corner_radius=10)
frame_sys.pack(pady=5, padx=20, fill="x")
ctk.CTkLabel(frame_sys, text="🍓 Система", font=("Consolas", 14, "bold")).pack(pady=(10, 5))

ctk.CTkButton(frame_sys, text="💻 Чистый терминал", fg_color="#2b2b2b", hover_color="#404040", command=lambda: launch_ssh(keep_open=False), **btn_style).pack(pady=5)
ctk.CTkButton(frame_sys, text="🌡️ Температура CPU", command=lambda: launch_ssh("vcgencmd measure_temp"), **btn_style).pack(pady=5)
ctk.CTkButton(frame_sys, text="💾 Память диска (SD)", command=lambda: launch_ssh("df -h /"), **btn_style).pack(pady=5)
ctk.CTkButton(frame_sys, text="📦 Обновить систему", command=lambda: launch_ssh("sudo apt update && sudo apt upgrade -y"), **btn_style).pack(pady=5)

# --- БЛОК 2: ПРОЕКТЫ (БОТ) ---
frame_bot = ctk.CTkFrame(app, fg_color="#1a1a1a", corner_radius=10)
frame_bot.pack(pady=5, padx=20, fill="x")
ctk.CTkLabel(frame_bot, text="🤖 Resale Bot", font=("Consolas", 14, "bold")).pack(pady=(10, 5))

ctk.CTkButton(frame_bot, text="📂 Открыть папку с кодом", command=lambda: launch_ssh("cd ~/resale-agent"), **btn_style).pack(pady=5)
ctk.CTkButton(frame_bot, text="📋 Логи (Live)", command=lambda: launch_ssh("journalctl -u resale_bot.service -f", keep_open=False), **btn_style).pack(pady=5)
ctk.CTkButton(frame_bot, text="🔄 Рестарт службы", command=lambda: launch_ssh("sudo systemctl restart resale_bot.service && echo 'Bot Restarted!'"), **btn_style).pack(pady=5)

# --- БЛОК 3: ПИТАНИЕ ---
frame_pwr = ctk.CTkFrame(app, fg_color="transparent")
frame_pwr.pack(pady=10, fill="x")

ctk.CTkButton(frame_pwr, text="⚡ Reboot", width=120, fg_color="#8b8b00", hover_color="#606000", command=lambda: launch_ssh("sudo reboot", keep_open=False)).pack(side="left", padx=(40, 5))
ctk.CTkButton(frame_pwr, text="🛑 Shutdown", width=120, fg_color="#8b0000", hover_color="#600000", command=lambda: launch_ssh("sudo shutdown now", keep_open=False)).pack(side="right", padx=(5, 40))

app.mainloop()