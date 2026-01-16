#!/usr/bin/env python
# -*- coding: utf-8 -*-

content = """# Telegram Bot Configuration
# Получите токен бота у @BotFather в Telegram
BOT_TOKEN=your_bot_token_here

# Telegram ID администратора
# Узнайте свой ID у @userinfobot в Telegram
ADMIN_TELEGRAM_ID=your_telegram_id_here

# Database URL (по умолчанию SQLite)
# Для PostgreSQL используйте: postgresql+asyncpg://user:password@localhost/dbname
DATABASE_URL=sqlite+aiosqlite:///data/bot.db

# Log Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
"""

with open('.env.example', 'w', encoding='utf-8') as f:
    f.write(content)

print(".env.example created successfully!")


