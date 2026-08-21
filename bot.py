import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


TEST_URL = "https://www.erepublik.com/en/military/battle-stats/930049/11/41368335"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest"
}


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "Bot funcionando correctamente."
    )


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(
            TEST_URL,
            headers=HEADERS,
            timeout=15
        )

        if response.status_code != 200:
            await update.message.reply_text(
                f"❌ eRepublik respondió HTTP {response.status_code}"
            )
            return

        data = response.json()

        await update.message.reply_text(
            "🧪 Respuesta recibida correctamente\n\n"
            f"Claves principales:\n"
            f"{list(data.keys())}"
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {type(e).__name__}: {e}"
        )
async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "/estado - Estado del bot\n"
        "/test - Probar conexión con eRepublik\n"
        "/ayuda - Ver comandos"
    )


def main():
    token = os.getenv("TELEGRAM_TOKEN")

    if not token:
        raise ValueError("No se encontró TELEGRAM_TOKEN")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("ayuda", ayuda))

    print("Bot iniciado...")
    app.run_polling()


if __name__ == "__main__":
    main()
