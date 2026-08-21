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

BATTLE_ID = 930049
DIVISION_ID = 11
BATTLE_ZONE_ID = 41368335

TEST_URL = (
    f"https://www.erepublik.com/en/military/"
    f"battle-stats/{BATTLE_ID}/{DIVISION_ID}/{BATTLE_ZONE_ID}"
)

REFERER_URL = (
    f"https://www.erepublik.com/en/military/"
    f"battlefield/{BATTLE_ID}"
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
# /start
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
        "/test - Probar lectura de eRepublik\n"
        "/ayuda - Ver comandos"
    )


# ============================================================
# /estado
# ============================================================

async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "✅ Bot funcionando correctamente.\n"
        "✅ Sesión de eRepublik configurada."
    )


# ============================================================
# /test
# ============================================================

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
                f"Error: {data['error']}"
            )
            return

        division = data.get("division", {})
        domination = division.get("domination", {})

        porcentaje = domination.get(str(BATTLE_ZONE_ID))

        if porcentaje is None:
            await update.message.reply_text(
                "⚠️ No encontré el porcentaje de dominación.\n\n"
                f"Contenido de domination:\n{domination}"
            )
            return

        porcentaje_otro = 100 - float(porcentaje)

        await update.message.reply_text(
            "✅ Lectura real de eRepublik\n\n"
            "✈️ AIR\n\n"
            f"🔵 Lado A: {float(porcentaje):.2f}%\n"
            f"🔴 Lado B: {porcentaje_otro:.2f}%\n\n"
            f"Battle ID: {BATTLE_ID}\n"
            f"Battle Zone ID: {BATTLE_ZONE_ID}"
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
# /ayuda
# ============================================================

async def ayuda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "/start - Iniciar bot\n"
        "/estado - Estado del bot\n"
        "/test - Leer batalla de prueba\n"
        "/ayuda - Ver comandos"
    )


# ============================================================
# INICIO
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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("ayuda", ayuda))

    print("eArgentina Battle Bot iniciado...")

    app.run_polling()


if __name__ == "__main__":
    main()
