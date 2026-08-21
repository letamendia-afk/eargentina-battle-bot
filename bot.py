import os
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIGURACIÓN DE PRUEBA
# ============================================================

BATTLE_ID = 930049

# Solo necesitamos una zona conocida para obtener
# inicialmente la información de la batalla.
INITIAL_DIVISION = 11
INITIAL_ZONE_ID = 41368335

DIVISIONES = {
    3: "D3",
    4: "D4",
    11: "AIR",
}


# ============================================================
# FUNCIONES EREPUBLIK
# ============================================================

def crear_headers(battle_id):
    cookie = os.getenv("EREPUBLIK_COOKIE")

    if not cookie:
        raise ValueError("No se encontró EREPUBLIK_COOKIE")

    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "X-Requested-With": "XMLHttpRequest",
        "Referer": (
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{battle_id}"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Cookie": cookie.strip(),
    }


def consultar_zona(battle_id, division, zone_id):
    url = (
        f"https://www.erepublik.com/en/military/"
        f"battle-stats/{battle_id}/{division}/{zone_id}"
    )

    response = requests.get(
        url,
        headers=crear_headers(battle_id),
        timeout=15,
    )

    data = response.json()

    if "error" in data:
        raise ValueError(
            f"eRepublik devolvió: {data['error']}"
        )

    return data


def buscar_zonas(objeto, zonas=None):
    """
    Recorre recursivamente todo el JSON buscando objetos
    que tengan battle_zone_id y division.
    """

    if zonas is None:
        zonas = {}

    if isinstance(objeto, dict):

        if (
            "battle_zone_id" in objeto
            and "division" in objeto
        ):
            division = objeto.get("division")
            zone_id = objeto.get("battle_zone_id")

            if division in DIVISIONES:
                zonas[division] = zone_id

        for valor in objeto.values():
            buscar_zonas(valor, zonas)

    elif isinstance(objeto, list):

        for elemento in objeto:
            buscar_zonas(elemento, zonas)

    return zonas


def obtener_porcentaje(battle_id, division, zone_id):
    data = consultar_zona(
        battle_id,
        division,
        zone_id,
    )

    division_data = data.get("division", {})
    domination = division_data.get("domination", {})

    porcentaje = domination.get(str(zone_id))

    if porcentaje is None:
        raise ValueError(
            f"No encontré domination para {zone_id}"
        )

    return float(porcentaje)


# ============================================================
# TELEGRAM
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "/estado - Estado del bot\n"
        "/test - Analizar batalla de prueba\n"
        "/ayuda - Ver comandos"
    )


async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "✅ Bot funcionando\n"
        "✅ Conexión con eRepublik configurada"
    )


async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:

        # 1. Obtenemos una respuesta de la batalla
        data_inicial = consultar_zona(
            BATTLE_ID,
            INITIAL_DIVISION,
            INITIAL_ZONE_ID,
        )

        # 2. Buscamos automáticamente D3, D4 y AIR
        zonas = buscar_zonas(data_inicial)

        mensaje = (
            "🔎 Batalla detectada\n\n"
            f"Battle ID: {BATTLE_ID}\n\n"
        )

        # 3. Consultamos cada división encontrada
        for division_id in [3, 4, 11]:

            nombre = DIVISIONES[division_id]

            zone_id = zonas.get(division_id)

            if not zone_id:
                mensaje += (
                    f"⚠️ {nombre}: "
                    "zona no encontrada\n"
                )
                continue

            try:
                porcentaje_a = obtener_porcentaje(
                    BATTLE_ID,
                    division_id,
                    zone_id,
                )

                porcentaje_b = 100 - porcentaje_a

                mensaje += (
                    f"{nombre}\n"
                    f"🔵 {porcentaje_a:.2f}%"
                    f" | "
                    f"🔴 {porcentaje_b:.2f}%\n"
                    f"Zone: {zone_id}\n\n"
                )

            except Exception as e:
                mensaje += (
                    f"❌ {nombre}: {e}\n\n"
                )

        mensaje += (
            "🔗 "
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{BATTLE_ID}"
        )

        await update.message.reply_text(mensaje)

    except Exception as e:

        await update.message.reply_text(
            "❌ Error analizando la batalla\n\n"
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
        "/test - Leer D3, D4 y Air\n"
        "/ayuda - Ver ayuda"
    )


# ============================================================
# INICIO
# ============================================================

def main():

    telegram_token = os.getenv("TELEGRAM_TOKEN")

    if not telegram_token:
        raise ValueError(
            "No se encontró TELEGRAM_TOKEN"
        )

    app = (
        Application
        .builder()
        .token(telegram_token.strip())
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
