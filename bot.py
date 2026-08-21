import os
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# Batalla de prueba:
# EAU vs Japón
# Battle ID: 930049
# Division 11 = Air
# Battle Zone ID: 41368335
TEST_URL = (
    "https://www.erepublik.com/en/military/"
    "battle-stats/930049/11/41368335"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
}


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "Bot iniciado correctamente.\n"
        "Usá /estado para comprobar el bot.\n"
        "Usá /test para probar la conexión con eRepublik."
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

        response = requests.get(
            TEST_URL,
            headers=HEADERS,
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

        await update.message.reply_text(
            "🧪 Respuesta de eRepublik\n\n"
            f"HTTP: {response.status_code}\n"
            f"JSON: {data}"
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
        "Comandos disponibles:\n\n"
        "/start - Iniciar bot\n"
        "/estado - Comprobar estado\n"
        "/test - Probar conexión con eRepublik\n"
        "/ayuda - Mostrar esta ayuda"
    )


def main():

    token = os.getenv("TELEGRAM_TOKEN")

    if not token:
        raise ValueError(
            "No se encontró la variable TELEGRAM_TOKEN"
        )

    # Evita problemas si el Secret tiene espacios
    # o saltos de línea accidentales.
    token = token.strip()

    app = Application.builder().token(token).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("estado", estado)
    )

    app.add_handler(
        CommandHandler("test", test)
    )

    app.add_handler(
        CommandHandler("ayuda", ayuda)
    )

    print("eArgentina Battle Bot iniciado...")

    app.run_polling()


if __name__ == "__main__":
    main()
