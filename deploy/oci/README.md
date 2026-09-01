# Oracle Cloud Always Free deployment

This bot is designed to run continuously on a small Oracle Cloud Linux VM, with PostgreSQL provided by your existing database or a PostgreSQL service you control.

## Recommended setup

1. Create an Oracle Cloud Always Free VM in your home region.
2. Install Python 3, Git, and `systemd` support on the VM.
3. Clone this repository to `/opt/eargentina-battle-bot`.
4. Create a virtual environment and install `requirements.txt`.
5. Copy [eargentina-battle-bot.env.example](eargentina-battle-bot.env.example) to `/etc/eargentina-battle-bot.env` and fill in the secrets.
6. Install [eargentina-battle-bot.service](eargentina-battle-bot.service) into `/etc/systemd/system/`.
7. Enable and start the service.

## Files

- `eargentina-battle-bot.service` - systemd service definition for always-on operation.
- `eargentina-battle-bot.env.example` - template for runtime environment variables.

## Notes

- Keep `MONITORED_COUNTRY_ID=27` for Argentina.
- The bot will keep using Telegram, eRepublik session cookies, and the PostgreSQL connection string you provide.
- GitHub Actions can remain as CI while the Oracle VM becomes the always-on runtime.
