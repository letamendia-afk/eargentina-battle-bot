import os
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIGURACIÓN DE PRUEBA
# ============================================================

# Batalla de prueba:
# Battle ID: 930049
# Division 11 = AIR
# Battle Zone ID: 41368335

TEST_URL = (
    "https://www.erepublik.com/en/military/"
    "battle-stats/930049/11/41368335"
)

REFERER_URL = (
    "https://www.erepublik.com/en/military/"
    "battlefield/930049"
)


# ============================================================
# HEADERS PARA EREPUBLIK
# ============================================================

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Referer": REFERER_URL,
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


# ============================================================
# COMANDO /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "Bot iniciado correctamente.\n\n"
        "Comandos:\n"
        "/estado - Estado del bot\n"
        "/test - Probar conexión con eRepublik\n"
        "/ayuda - Ver comandos"
    )


# ============================================================
# COMANDO /estado
# ============================================================

async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "✅ Bot funcionando correctamente.\n"
        "🔎 Conexión con eRepublik disponible."
    )


# ============================================================
# COMANDO /test
# ============================================================

async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:

        # Obtener cookie guardada en GitHub Secrets
        cookie = os.getenv("EREPUBLIK_COOKIE")

        if not cookie:
            await update.message.reply_text(
                "❌ No se encontró EREPUBLIK_COOKIE."
            )
            return

        # Preparar headers
        headers = HEADERS_BASE.copy()
        headers["Cookie"] = cookie.strip()

        # Consultar eRepublik
        response = requests.get(
            TEST_URL,
            headers=headers,
            timeout=15
        )

        # Comprobar que devuelve JSON
        try:
            data = response.json()

        except ValueError:
            await update.message.reply_text(
                "❌ eRepublik no devolvió JSON.\n\n"
                f"HTTP: {response.status_code}\n"
                f"Respuesta:\n{response.text[:500]}"
            )
            return

        # Comprobar autenticación
        if "error" in data:
            await update.message.reply_text(
                "❌ eRepublik devolvió un error.\n\n"
                f"HTTP: {response.status_code}\n"
                f"Error: {data['error']}"
            )
            return

        # Obtener la sección division
        division = data.get("division")

        if division is None:
            await update.message.reply_text(
                "⚠️ No encontré la sección 'division'.\n\n"
                f"Claves principales:\n"
                f"{list(data.keys())}"
            )
            return

        # Comprobar que division es un diccionario
        if not isinstance(division, dict):
            await update.message.reply_text(
                "⚠️ Encontré 'division', pero no tiene "
                "la estructura esperada.\n\n"
                f"Tipo: {type(division).__name__}\n"
                f"Contenido: {str(division)[:500]}"
            )
            return

        # Mostrar las claves que contiene division
        await update.message.reply_text(
            "✅ Conexión autenticada con eRepublik\n\n"
            "🧪 Analizando batalla de prueba\n\n"
            "Battle ID: 930049\n"
            "División: AIR (11)\n"
            "Battle Zone ID: 41368335\n\n"
            "Claves dentro de 'division':\n"
            f"{list(division.keys())}"
        )

    except requests.Timeout:

        await update.message.reply_text(
            "❌ eRepublik tardó demasiado en responder."
        )

    except requests.RequestException as e:

        await update.message.reply_text(
            "❌ Error de conexión con eRepublik.\n\n"
            f"{type(e).__name__}: {e}"
        )

    except Exception as e:

        await update.message.reply_text(
            "❌ Error inesperado.\n\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# COMANDO /ayuda
# ============================================================

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
        "/ayuda - Mostrar ayuda"
    )


# ============================================================
# INICIO DEL BOT
# ============================================================

def main():

    telegram_token = os.getenv("TELEGRAM_TOKEN")

    if not telegram_token:
        raise ValueError(
            "No se encontró TELEGRAM_TOKEN."
        )

    telegram_token = telegram_token.strip()

    app = (
        Application
        .builder()
        .token(telegram_token)
        .build()
    )

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

    print("===================================")
    print("eArgentina Battle Bot iniciado")
    print("===================================")

    app.run_polling()


if __name__ == "__main__":
    main()
