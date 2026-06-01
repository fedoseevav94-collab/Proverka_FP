# Damage Charge Control Bot

Telegram bot for matching FP damage reports with PV return messages and reminding managers to close damage cases.

## Quick Start

1. Create `.env` from `.env.example`.
2. Put the fleet Excel file at `CARS_EXCEL_PATH`.
3. Install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

4. Run tests:

```bash
pytest
```

5. Start the bot:

```bash
python -m damage_bot.main
```

## Deploy

Do not commit `.env` or bot tokens to GitHub. Add environment variables in the hosting control panel.

Suggested start command:

```bash
python -m damage_bot.main
```

For MVP hosting with SQLite, make sure the host keeps the working directory or database file between restarts. For production, prefer PostgreSQL and set `DATABASE_URL` accordingly.

## Notes

- Chat IDs are matched exactly as configured, with support for both plain `100...` IDs and Telegram `-100...` supergroup IDs.
- Most business behavior lives in pure modules under `damage_bot/core`, so parser and workflow rules can be adjusted after real screenshots arrive.
- PV messages with `Аренда | Сдача` and `Аренда | Пересадка` both trigger return matching for the returned car.
- Reminder and FP escalation messages are sent as replies to the original FP message (`сдал`, `осмотр`, or `пересадка`) so the whole chain stays attached to the source report.
- SQLite is used by default for MVP. Use an async SQLAlchemy URL such as `postgresql+asyncpg://...` for production.
