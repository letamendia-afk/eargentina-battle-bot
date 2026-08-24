import os
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# BATALLA DE PRUEBA
# ============================================================

BATTLE_ID = 931105
INITIAL_ZONE_ID = 41419149

DIVISIONES = {
    3: "D3",
    4: "D4",
    11: "AIR",
}


# ============================================================
# EREPUBLIK
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

    try:
        data = response.json()
    except ValueError:
        raise ValueError(
            f"eRepublik no devolvió JSON. HTTP {response.status_code}"
        )

    if "error" in data:
        raise ValueError(data["error"])

    return data


# ============================================================
# ENCONTRAR LA DIVISIÓN DE LA ZONA INICIAL
# ============================================================

def obtener_respuesta_inicial(battle_id, zone_id):
    errores = []

    for division_id in [3, 4, 11]:

        try:
            data = consultar_zona(
                battle_id,
                division_id,
                zone_id,
            )

            # Si devuelve datos de división,
            # consideramos válida la consulta.
            if "division" in data:
                return data, division_id

        except Exception as e:
            errores.append(
                f"{DIVISIONES[division_id]}: {e}"
            )

    raise ValueError(
        "No pude identificar la división de la zona inicial.\n"
        + " | ".join(errores)
    )


# ============================================================
# BUSCAR D3 / D4 / AIR
# ============================================================

def buscar_zonas(objeto, zonas=None):
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
                zonas[division] = int(zone_id)

        for valor in objeto.values():
            buscar_zonas(valor, zonas)

    elif isinstance(objeto, list):

        for elemento in objeto:
            buscar_zonas(elemento, zonas)

    return zonas


# ============================================================
# OBTENER BARRA
# ============================================================

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
        "/test - Analizar batalla\n"
        "/ayuda - Ver comandos"
    )


async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "✅ Bot funcionando\n"
        "✅ Lectura mediante battle-stats"
    )


async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:

        # 1. Averiguar qué división corresponde
        #    a la Battle Zone que tenemos.
        data_inicial, division_inicial = (
            obtener_respuesta_inicial(
                BATTLE_ID,
                INITIAL_ZONE_ID,
            )
        )

        # 2. Buscar automáticamente los Zone ID
        #    de D3, D4 y Air.
        zonas = buscar_zonas(data_inicial)

        mensaje = (
            "🔎 Batalla detectada\n\n"
            f"Battle ID: {BATTLE_ID}\n"
            f"Zona inicial: {INITIAL_ZONE_ID}\n"
            f"División inicial: "
            f"{DIVISIONES[division_inicial]}\n\n"
        )

        # 3. Leer las tres barras.
        for division_id in [3, 4, 11]:

            nombre = DIVISIONES[division_id]
            zone_id = zonas.get(division_id)

            if not zone_id:
                mensaje += (
                    f"⚠️ {nombre}: "
                    "zona no encontrada\n\n"
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
