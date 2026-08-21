import os
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


TEST_URL = (
    "https://www.erepublik.com/en/military/"
    "battle-stats/930049/11/41368335"
)

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.erepublik.com/en/military/battlefield/930049",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "Bot iniciado correctamente.\n"
        "Usá /estado para comprobar el bot.\n"
        "Usá /test para probar eRepublik."
    )


async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "✅ Bot funcionando correctamente."
    )


async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        cookie = os.getenv("EREPUBLIK_COOKIE")

        if not cookie:
            await update.message.reply_text(
                "❌ No se encontró EREPUBLIK_COOKIE."
            )
            return

        headers = HEADERS_BASE.copy()
        headers["Cookie"] = cookie.strip()

        response = requests.get(
            TEST_URL,
            headers=headers,
            timeout=15
        )

        try:
            data = response.json()
        except ValueError:
            await update.message.reply_text(
                "❌ eRepublik no devolvió JSON.\n\n"
                f"HTTP: {response.status_code}\n"
                f"Respuesta: {response.text[:500]}"
            )
            return

        if "error" in data:
            await update.message.reply_text(
                "❌ eRepublik devolvió un error.\n\n"
                f"HTTP: {response.status_code}\n"
                f"Error: {data['error']}"
            )
            return

        domination = data.get("domination", {})

        if not domination:
            await update.message.reply_text(
                "⚠️ Conexión autenticada, pero no encontré domination.\n\n"
                f"Claves: {list(data.keys())}"
            )
            return

        porcentaje = list(domination.values())[0]
        contrario = 100 - porcentaje

        await update.message.reply_text(
            "✅ Conexión autenticada con eRepublik\n\n"
            "🧪 Batalla de prueba\n"
            "División: AIR\n\n"
            f"🔵 {porcentaje:.2f}%\n"
            f"🔴 {contrario:.2f}%"
        )

    except requests.RequestException as e:
        await update.message.reply_text(
            "❌ Error de conexión con eRepublik\n\n"
            f"{type(e).__name__}: {e}"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Error inesperado\n\n"
            f"{type(e).__name__}: {e}"
        )


async def ayuda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "/start - Iniciar bot\n"
        "/estado - Estado del bot\n"
        "/test - Probar conexión con eRepublik\n"
        "/ayuda - Ver comandos"
    )


def main():
    token = os.getenv("TELEGRAM_TOKEN")

    if not token:
        raise ValueError("No se encontró TELEGRAM_TOKEN")

    token = token.strip()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("ayuda", ayuda))

    print("eArgentina Battle Bot iniciado...")

    app.run_polling()


if __name__ == "__main__":
    main()
