import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "Bot funcionando correctamente.\n"
        "Monitoreo de batallas: próximamente."
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "/estado - Estado del bot\n"
        "/ayuda - Ver comandos"
    )


def main():
    token = os.getenv("TELEGRAM_TOKEN")

    if not token:
        raise ValueError("No se encontró TELEGRAM_TOKEN")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("ayuda", ayuda))

    print("Bot iniciado...")
    app.run_polling()


if __name__ == "__main__":
    main()
