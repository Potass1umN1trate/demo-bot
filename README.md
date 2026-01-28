# 🎾 RKBook Demo Bot

A modern Telegram bot for booking sports activities (padel tennis, fitness) with seamless Google Calendar integration. Built with aiogram 3.x and asyncio for high performance.

## ✨ Features

- 📱 **Interactive Telegram Bot** - Intuitive user interface with inline keyboards
- 🏓 **Multiple Services** - Support for group padel, individual padel, and fitness classes
- 📅 **Smart Scheduling** - Real-time availability checking with automatic capacity management
- 🔗 **Google Calendar Integration** - Automatic event creation and updates
- 💾 **SQLite Database** - Persistent storage with atomic transactions
- 🔐 **Admin Notifications** - Real-time booking alerts
- 📊 **Comprehensive Logging** - Debug-ready logging to stdout
- ⚡ **Async/Await** - Non-blocking operations for high concurrency

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Google Calendar API credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd demo-bot
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

   Required variables:
   - `BOT_TOKEN` - Your Telegram bot token
   - `ADMIN_ID` - Your Telegram user ID (for notifications)
   - `GCAL_CALENDAR_ID` - Google Calendar ID (or "primary")
   - `GCAL_CREDENTIALS_PATH` - Path to client_secret.json
   - `GCAL_TOKEN_PATH` - Path where token.json will be stored
   - `TZ` - Timezone (e.g., "Europe/Moscow")

5. **Set up Google Calendar API**
   - Create a project in [Google Cloud Console](https://console.cloud.google.com)
   - Enable Google Calendar API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download as `client_secret.json`

6. **Run the bot**
   ```bash
   python3 main.py
   ```

## 📂 Project Structure

```
demo-bot/
├── app/
│   ├── handlers/           # Telegram message/callback handlers
│   │   ├── start.py       # /start command
│   │   └── booking.py     # Booking flow handlers
│   ├── calendar_publisher.py  # Google Calendar integration
│   ├── config.py          # Configuration management
│   ├── db.py              # Database initialization
│   ├── gcal_client.py     # Google Calendar API client
│   ├── keyboards.py       # Inline/Reply keyboard builders
│   ├── logger.py          # Logging configuration
│   ├── repo.py            # Database repository (SQLite)
│   ├── states.py          # FSM states for booking flow
│   ├── storage.py         # External API client (optional)
│   ├── texts.py           # User-facing message templates
│   └── __init__.py
├── main.py                # Bot entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
├── bookings.sqlite3       # SQLite database
└── README.md              # This file
```

## 🎯 Booking Flow

```
/start
  ↓
📅 Choose Service (Padel Group/Individual, Fitness)
  ↓
📆 Pick Date (Today, Tomorrow, or Calendar)
  ↓
⏰ Select Time Slot (Auto-filtered by availability)
  ↓
👤 Enter Name
  ↓
📞 Enter Phone
  ↓
✅ Confirm Booking
  ↓
📱 User Confirmation + 📧 Admin Notification
  ↓
📅 Google Calendar Event Created
```

## 🔧 Configuration

### Service Capacity Settings (in database)

| Setting | Default | Description |
|---------|---------|-------------|
| `cap_padel_group` | 3 | Max participants for group padel |
| `cap_padel_ind` | 1 | Max participants for individual padel |
| `cap_fitness` | 10 | Max participants for fitness |
| `work_start_hour` | 10 | Working hours start |
| `work_end_hour` | 22 | Working hours end |
| `slot_minutes` | 60 | Duration of each booking slot |

### Environment Variables

```bash
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
ADMIN_ID=123456789
DB_PATH=./bookings.sqlite3
GCAL_CALENDAR_ID=primary
GCAL_CREDENTIALS_PATH=./client_secret.json
GCAL_TOKEN_PATH=./token.json
TZ=Europe/Moscow
LOG_LEVEL=DEBUG
```

## 📊 Database Schema

### Bookings Table
```sql
CREATE TABLE bookings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL,           -- 'active' or 'cancelled'
  service TEXT NOT NULL,          -- Service name
  date TEXT NOT NULL,             -- DD.MM.YYYY
  time TEXT NOT NULL,             -- HH:mm
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  tg_user_id TEXT,                -- Telegram user ID
  calendar_event_id TEXT          -- Google Calendar event ID
);
```

### Settings Table
```sql
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

## 🔍 Logging

All logs are output to stdout with the following format:

```
[2026-01-28 22:24:45] [app.handlers.booking] [INFO] Creating booking for user 123456789: 🏓 Падел (групповая) on 29.01.2026 at 19:00
```

Adjust log level in `.env`:
- `DEBUG` - Detailed information for debugging
- `INFO` - General information about bot operations
- `WARNING` - Warning messages for potential issues
- `ERROR` - Error messages for exceptions

## 🛠️ Development

### Code Structure

- **Handlers** (`app/handlers/`) - Telegram event handlers with FSM states
- **Repository** (`app/repo.py`) - Database operations with atomic transactions
- **Calendar** (`app/calendar_publisher.py`) - Google Calendar API wrapper
- **Keyboards** (`app/keyboards.py`) - Dynamic keyboard builders

### Adding New Services

1. Add to `SERVICE_KEYS` in `app/repo.py`
2. Add capacity setting in `app/db.py`
3. Update service labels in `app/handlers/booking.py`

### Extending the Booking Flow

FSM states are defined in `app/states.py`. Add new states and handlers in `app/handlers/booking.py`.

## 📝 Error Handling

- **Slot Full** - Gracefully handles concurrent bookings
- **Calendar API Errors** - Doesn't block booking creation
- **Admin Notification Failures** - Logged but doesn't affect user experience
- **Database Errors** - Rolled back with proper error messages

## 🔒 Security Considerations

- Tokens and credentials in `.env` (never commit!)
- Database passwords should be in `.env`
- Admin ID prevents unauthorized notifications
- Atomic transactions prevent race conditions

## 🐛 Troubleshooting

### No logs appearing?
```bash
# Check LOG_LEVEL in .env
LOG_LEVEL=DEBUG
```

### Google Calendar API errors?
```bash
# Verify credentials path
GCAL_CREDENTIALS_PATH=./client_secret.json
# Delete token.json to force re-authentication
rm token.json
python3 main.py
```

### Database locked?
```bash
# SQLite WAL mode handles concurrency
# If stuck, delete .sqlite3-wal and .sqlite3-shm files
rm bookings.sqlite3-*
```

### Bot not responding?
```bash
# Check bot token is correct
# Verify polling is running in terminal
# Check user hasn't blocked the bot
```

## 📦 Dependencies

- **aiogram** - Telegram Bot API framework
- **aiosqlite** - Async SQLite client
- **google-auth-oauthlib** - Google authentication
- **google-api-python-client** - Google Calendar API
- **python-dotenv** - Environment variable management

See `requirements.txt` for versions.

## 📜 License

This project is provided as-is for demonstration purposes.

## 👤 Author

Created by Toster

## 💬 Support

For issues or questions, refer to:
- [aiogram Documentation](https://docs.aiogram.dev/)
- [Google Calendar API](https://developers.google.com/calendar)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
