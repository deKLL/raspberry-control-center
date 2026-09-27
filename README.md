# ⚡ TYRELL // CONTROL CENTER v2.0
### Cyberpunk Superapp for Remote Command & Telemetry (Raspberry Pi Zero 2 W)

![Python](https://img.shields.io/badge/Python-3.10+-00FF66?style=for-the-badge&logo=python&logoColor=black)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-00E5FF?style=for-the-badge)
![Paramiko](https://img.shields.io/badge/SSH-Paramiko-E2B93B?style=for-the-badge)
![Status](https://img.shields.io/badge/System-Operational-00FF66?style=for-the-badge)

---

## 🌌 Архитектура и дизайн
**TYRELL // CONTROL CENTER v2.0** — автономная десктопная панель управления в глубоком стиле Киберпанк, разработанная специально для взаимодействия с Raspberry Pi Zero 2 W по SSH и SFTP. Все сетевые операции и сбор телеметрии вынесены в неблокирующие асинхронные потоки, обеспечивая мгновенную отзывчивость интерфейса.

- **Цветовая палитра**: Глубокий обсидиановый фон (`#0B0C10`, `#171822`), неоновый зелёный акцент (`#00FF66`), кибернетический циан (`#00E5FF`), предупреждающий золотой (`#E2B93B`) и критический красный (`#FF3333`).
- **Скругления карточек**: `corner_radius=8`.
- **Шрифты**: Моноширинный хакерский `Consolas` для логов, кода и телеметрии.

---

## 🛠 Структура проекта

```text
Raspberry/
├── main.py               # Главный интерфейс CustomTkinter, потоки и логика
├── ssh_client.py         # Thread-safe SSH & SFTP менеджер (Paramiko)
├── ui_components.py      # Киберпанк-виджеты: карточки, лог-терминал с подсветкой, IDE
├── config.py             # Настройки по умолчанию, цветовая схема, шрифты
├── network_scanner.py    # Сканер локальной сети и ARP-радар
├── bot_widget.pyw        # Безоконный быстрый запуск (pythonw)
├── run.bat               # Консольный лаунчер для Windows
└── tyrell_config.json    # Сохранённый конфиг подключения (создаётся автоматически)
```

---

## 🚀 Возможности и модули

### 1. 📊 SYSTEM HEALTH (Телеметрия железа)
- Фоновый опрос каждые 3 секунды через комбинированный легковесный запрос (без спама процессами).
- Карточки с динамическими прогресс-барами, меняющими цвет (зелёный → золотой → красный):
  - **CPU Load (%)** (расчёт дельты тиков `/proc/stat` на 4 ядрах ARM Cortex-A53).
  - **RAM Memory (%)** (использовано / всего в MB, кэш).
  - **SD Storage (%)** (занято / свободно в GB на `/dev/mmcblk0p2`).
  - **CPU Temperature (°C)** (чтение через `vcgencmd measure_temp` с градацией нагрева).
- Монитор активных процессов (топ-5 процессов по загрузке CPU/RAM в реальном времени).
- Системные действия: System Update (`apt upgrade`), очистка RAM кэшей, диагностика вольтажа и троттлинга.

### 2. 🤖 RESALE AGENT MANAGER (Управление ботом)
- Статус службы `resale_bot.service` (Active / Inactive / Failed) с неоновым светящимся индикатором.
- Кнопки управления: **"Запустить"**, **"Остановить"**, **"Перезапуск"**.
- **Live Terminal логов**: Непрерывный стриминг `journalctl -u resale_bot -n 100 -f` через отдельный канал Paramiko.
- **Парсер ошибок**:
  - `401 Unauthorized` подсвечивается неоново-красным на тёмно-бордовом фоне.
  - `404 Not Found` подсвечивается янтарно-оранжевым.
  - Ошибки `ERROR`, `CRITICAL` и предупреждения `WARNING`.
  - Счётчики найденных ошибок `[401: X]` и `[404: Y]` в шапке терминала.
  - Живой поиск/фильтрация по регулярным выражениям или тексту, автоскролл, копирование.

### 3. 💻 QUICK IDE & DEPLOYER (Встроенный редактор кода)
- Селектор файлов проекта:
  - `scrapers/vinted.py`
  - `scrapers/bazos.py`
  - `scrapers/base.py`
  - `.env`
  - `main.py`, `config.py`, `handlers.py`, `database.py` и др.
- **"Загрузить код"**: Скачивание выбранного файла по SFTP и отображение в редакторе с поддержкой отмены (Undo/Redo).
- **"Save & Reload"**: Автоматическое создание бэкапа (`.bak`), запись файла по SFTP и моментальный перезапуск службы `sudo systemctl restart resale_bot.service`.

### 4. ⚡ QUICK MACROS & INTERACTIVE SHELL (Авторская фича)
- **Интерактивный BASH-терминал**: ввод любых команд на Raspberry Pi с выводом в киберпанк-консоль.
- **Quick Macros Bar**: быстрые кнопки в один клик:
  - Просмотр хвоста лога бота (`tail -n 80 resale_agent.log`).
  - `git status` и `git pull origin`.
  - Сетевые интерфейсы и маршрутизация (`ip -br addr`).
  - Проверка установленных пакетов в virtualenv.
  - Дерево процессов Python.
  - Проверка троттлинга питания (`vcgencmd get_throttled`).

### 5. 📡 LAN RADAR & RESALE ANALYTICS (Авторская фича)
- **Resale Lot Analytics**: Прямой опрос базы данных SQLite `bazos_monitor.db`:
  - Общее количество проиндексированных товаров.
  - Активные поисковые подписки.
  - Карточка последнего найденного лота (название, цена, время).
- **LAN Radar (Сканер сети)**:
  - Чтение ARP-таблицы и опрос портов (22, 80, 443 и др.) в параллельных потоках.
  - Автоматическое распознавание Raspberry Pi Zero 2 W в сети и подсветка неоновым цветом.
- **Audio Sentinel Alert**: Звуковой и визуальный сигнал при падении службы бота.

---

## 🚦 Запуск приложения

```bash
# Запуск через Python
python main.py

# Или двойной клик по bot_widget.pyw (без лишнего черного окна консоли)
# Или через run.bat
```
