import os
import re
import json
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
# HEADERS PARA BATTLE-STATS
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


# ============================================================
# HEADERS PARA LEER EL HTML NORMAL
# ============================================================

def crear_headers_html(battle_id):
    cookie = os.getenv("EREPUBLIK_COOKIE")

    if not cookie:
        raise ValueError("No se encontró EREPUBLIK_COOKIE")

    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        "Referer": "https://www.erepublik.com/",
        "Cookie": cookie.strip(),
    }


# ============================================================
# INFORMACIÓN GENERAL DE LA BATALLA
# ============================================================

def obtener_info_batalla(battle_id):

    url = (
        f"https://www.erepublik.com/en/military/"
        f"battlefield/{battle_id}"
    )

    response = requests.get(
        url,
        headers=crear_headers_html(battle_id),
        timeout=15,
    )

    if response.status_code != 200:
        raise ValueError(
            f"No pude abrir battlefield. "
            f"HTTP {response.status_code}"
        )

    html = response.text

    # ------------------------------------------
    # INVADER ID
    # ------------------------------------------

    match_invader = re.search(
        r'"invaderId"\s*:\s*(\d+)',
        html
    )

    if not match_invader:
        raise ValueError(
            "No encontré invaderId en battlefield"
        )

    invader_id = int(
        match_invader.group(1)
    )

    # ------------------------------------------
    # COUNTRY ID
    # ------------------------------------------

    match_country = re.search(
        r'"countryId"\s*:\s*(\d+)',
        html
    )

    country_id = None

    if match_country:
        country_id = int(
            match_country.group(1)
        )

    # ------------------------------------------
    # LISTA DE PAÍSES
    # ------------------------------------------

    match_countries = re.search(
        r'"countries"\s*:\s*(\{[^}]+\})',
        html
    )

    if not match_countries:
        raise ValueError(
            "No encontré countries en battlefield"
        )

    try:
        countries = json.loads(
            match_countries.group(1)
        )

    except json.JSONDecodeError as e:
        raise ValueError(
            f"No pude leer countries: {e}"
        )

    return {
        "battle_id": battle_id,
        "country_id": country_id,
        "invader_id": invader_id,
        "countries": countries,
    }


# ============================================================
# BATTLE-STATS
# ============================================================

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
            f"eRepublik no devolvió JSON. "
            f"HTTP {response.status_code}"
        )

    if "error" in data:
        raise ValueError(data["error"])

    return data


# ============================================================
# RESPUESTA INICIAL
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

            if "division" in data:
                return data

        except Exception as e:

            errores.append(
                f"{DIVISIONES[division_id]}: {e}"
            )

    raise ValueError(
        "No pude obtener información de la batalla.\n"
        + " | ".join(errores)
    )


# ============================================================
# ENCONTRAR ZONAS D3 / D4 / AIR
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
# DATOS DE UNA DIVISIÓN
# ============================================================

def obtener_datos_division(
    battle_id,
    division_id,
    zone_id
):

    data = consultar_zona(
        battle_id,
        division_id,
        zone_id,
    )

    division_data = data.get("division", {})

    domination = division_data.get(
        "domination",
        {}
    )

    bar = division_data.get(
        "bar",
        {}
    )

    porcentaje = domination.get(
        str(zone_id)
    )

    pais_barra = bar.get(
        str(zone_id)
    )

    if porcentaje is None:
        raise ValueError(
            f"No encontré domination para {zone_id}"
        )

    if pais_barra is None:
        raise ValueError(
            f"No encontré país de la barra {zone_id}"
        )

    porcentaje = float(porcentaje)
    pais_barra = int(pais_barra)

    paises = []

    for clave in division_data.keys():

        try:
            country_id = int(clave)

        except (ValueError, TypeError):
            continue

        if country_id not in paises:
            paises.append(country_id)

    pais_contrario = None

    for country_id in paises:

        if country_id != pais_barra:
            pais_contrario = country_id
            break

    return {
        "pais_barra": pais_barra,
        "pais_contrario": pais_contrario,
        "porcentaje_barra": porcentaje,
        "porcentaje_contrario": 100 - porcentaje,
        "zone_id": zone_id,
    }


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

        # ----------------------------------------
        # INFORMACIÓN GENERAL
        # ----------------------------------------

        info = obtener_info_batalla(
            BATTLE_ID
        )

        countries = info["countries"]

        invader_id = int(
            info["invader_id"]
        )

        # ----------------------------------------
        # BATTLE-STATS
        # ----------------------------------------

        data_inicial = obtener_respuesta_inicial(
            BATTLE_ID,
            INITIAL_ZONE_ID,
        )

        zonas = buscar_zonas(
            data_inicial
        )

        resultados = {}
        paises = set()

        for division_id in [3, 4, 11]:

            zone_id = zonas.get(
                division_id
            )

            if not zone_id:
                continue

            datos = obtener_datos_division(
                BATTLE_ID,
                division_id,
                zone_id,
            )

            resultados[division_id] = datos

            paises.add(
                datos["pais_barra"]
            )

            if datos["pais_contrario"] is not None:
                paises.add(
                    datos["pais_contrario"]
                )

        if len(paises) != 2:
            raise ValueError(
                f"Esperaba 2 países y encontré: {paises}"
            )

        # ----------------------------------------
        # ATACANTE / DEFENSOR
        # ----------------------------------------

        if invader_id not in paises:
            raise ValueError(
                f"Invader ID {invader_id} "
                f"no coincide con {paises}"
            )

        defender_id = next(
            p for p in paises
            if p != invader_id
        )

        atacante = countries.get(
            str(invader_id),
            f"País {invader_id}"
        )

        defensor = countries.get(
            str(defender_id),
            f"País {defender_id}"
        )

        # ----------------------------------------
        # MENSAJE
        # ----------------------------------------

        mensaje = (
            "⚔️ BATALLA\n\n"
            f"🛡️ Defensor: {defensor}\n"
            f"⚔️ Atacante: {atacante}\n\n"
        )

        for division_id in [3, 4, 11]:

            nombre = DIVISIONES[
                division_id
            ]

            datos = resultados.get(
                division_id
            )

            if not datos:

                mensaje += (
                    f"⚠️ {nombre}: "
                    "sin datos\n\n"
                )

                continue

            porcentajes = {
                datos["pais_barra"]:
                    datos["porcentaje_barra"],

                datos["pais_contrario"]:
                    datos["porcentaje_contrario"],
            }

            porcentaje_defensor = (
                porcentajes.get(
                    defender_id,
                    0
                )
            )

            porcentaje_atacante = (
                porcentajes.get(
                    invader_id,
                    0
                )
            )

            mensaje += (
                f"{nombre}\n"
                f"🛡️ {defensor}: "
                f"{porcentaje_defensor:.2f}%\n"
                f"⚔️ {atacante}: "
                f"{porcentaje_atacante:.2f}%\n\n"
            )

        mensaje += (
            f"Battle ID: {BATTLE_ID}\n\n"
            "🔗 "
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{BATTLE_ID}"
        )

        await update.message.reply_text(
            mensaje
        )

    except Exception as e:

        await update.message.reply_text(
            "❌ Error\n\n"
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
        "/test - Analizar batalla\n"
        "/ayuda - Ver ayuda"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    telegram_token = os.getenv(
        "TELEGRAM_TOKEN"
    )

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

    print(
        "eArgentina Battle Bot iniciado..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
