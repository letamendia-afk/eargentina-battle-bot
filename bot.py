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

# Cualquier Battle Zone válida de esta batalla.
# En este caso usamos una que sabemos que pertenece a la batalla.
PAGE_ZONE_ID = 41421720

DIVISIONES = {
    3: "D3",
    4: "D4",
    11: "AIR",
}


# ============================================================
# TABLA DE PAÍSES - RESPALDO
# ============================================================

PAISES_FALLBACK = {
    167: "Albania",
    27: "Argentina",
    169: "Armenia",
    50: "Australia",
    33: "Austria",
    83: "Belarus",
    32: "Belgium",
    76: "Bolivia",
    69: "Bosnia-Herzegovina",
    9: "Brazil",
    42: "Bulgaria",
    23: "Canada",
    64: "Chile",
    14: "China",
    78: "Colombia",
    63: "Croatia",
    171: "Cuba",
    82: "Cyprus",
    34: "Czech-Republic",
    55: "Denmark",
    165: "Egypt",
    70: "Estonia",
    39: "Finland",
    11: "France",
    168: "Georgia",
    12: "Germany",
    44: "Greece",
    13: "Hungary",
    48: "India",
    49: "Indonesia",
    56: "Iran",
    54: "Ireland",
    58: "Israel",
    10: "Italy",
    45: "Japan",
    71: "Latvia",
    72: "Lithuania",
    66: "Malaysia",
    26: "Mexico",
    80: "Montenegro",
    31: "Netherlands",
    84: "New-Zealand",
    170: "Nigeria",
    73: "North-Korea",
    79: "North-Macedonia",
    37: "Norway",
    57: "Pakistan",
    75: "Paraguay",
    77: "Peru",
    67: "Philippines",
    35: "Poland",
    53: "Portugal",
    81: "Republic-of-China-Taiwan",
    52: "Republic-of-Moldova",
    1: "Romania",
    41: "Russia",
    164: "Saudi-Arabia",
    65: "Serbia",
    68: "Singapore",
    36: "Slovakia",
    61: "Slovenia",
    51: "South-Africa",
    47: "South-Korea",
    15: "Spain",
    38: "Sweden",
    30: "Switzerland",
    59: "Thailand",
    43: "Turkey",
    40: "Ukraine",
    166: "United-Arab-Emirates",
    29: "United-Kingdom",
    74: "Uruguay",
    24: "USA",
    28: "Venezuela",
}


# ============================================================
# HEADERS
# ============================================================

def obtener_cookie():
    cookie = os.getenv("EREPUBLIK_COOKIE")

    if not cookie:
        raise ValueError("No se encontró EREPUBLIK_COOKIE")

    return cookie.strip()


def headers_html():
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
        "Cookie": obtener_cookie(),
    }


def headers_ajax(battle_id):
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
        "Cookie": obtener_cookie(),
    }


# ============================================================
# LEER INFORMACIÓN GENERAL DEL HTML
# ============================================================

def obtener_info_batalla(battle_id, page_zone_id):
    url = (
        f"https://www.erepublik.com/en/military/"
        f"battlefield/{battle_id}/{page_zone_id}"
    )

    response = requests.get(
        url,
        headers=headers_html(),
        timeout=15,
    )

    if response.status_code != 200:
        raise ValueError(
            f"No pude abrir battlefield. HTTP {response.status_code}"
        )

    html = response.text

    # --------------------------------------------------------
    # Atacante
    # --------------------------------------------------------

    match_invader = re.search(
        r'"invaderId"\s*:\s*(\d+)',
        html
    )

    if not match_invader:
        raise ValueError(
            "No encontré invaderId en battlefield"
        )

    invader_id = int(match_invader.group(1))

    # --------------------------------------------------------
    # Defensor
    # --------------------------------------------------------

    match_defender = re.search(
        r'"defenderId"\s*:\s*(\d+)',
        html
    )

    if not match_defender:
        raise ValueError(
            "No encontré defenderId en battlefield"
        )

    defender_id = int(match_defender.group(1))

    # --------------------------------------------------------
    # Nombres de países
    # --------------------------------------------------------

    countries = {}

    match_countries = re.search(
        r'"countries"\s*:\s*(\{[^}]+\})',
        html
    )

    if match_countries:
        try:
            countries = json.loads(
                match_countries.group(1)
            )
        except json.JSONDecodeError:
            countries = {}

    # --------------------------------------------------------
    # Battle Zones activas
    # --------------------------------------------------------

    zonas = {}

    for division_id in [3, 4, 11]:

        patron = (
            rf'"battleZoneId"\s*:\s*(\d+),'
            rf'"zoneId"\s*:\s*\d+,'
            rf'"division"\s*:\s*{division_id}'
        )

        matches = re.findall(
            patron,
            html
        )

        if matches:
            # Tomamos la última coincidencia porque suele ser
            # la ronda activa más reciente.
            zonas[division_id] = int(
                matches[-1]
            )

    if len(zonas) < 3:
        raise ValueError(
            f"No encontré todas las zonas activas: {zonas}"
        )

    # --------------------------------------------------------
    # Tiempo
    # --------------------------------------------------------

    zone_elapsed = None

    match_elapsed = re.search(
        r'"zoneElapsedTime"\s*:\s*"([^"]+)"',
        html
    )

    if match_elapsed:
        zone_elapsed = match_elapsed.group(1)

    # --------------------------------------------------------
    # RW
    # --------------------------------------------------------

    is_resistance = False

    match_rw = re.search(
        r'"isResistance"\s*:\s*(true|false)',
        html
    )

    if match_rw:
        is_resistance = (
            match_rw.group(1) == "true"
        )

    return {
        "invader_id": invader_id,
        "defender_id": defender_id,
        "countries": countries,
        "zonas": zonas,
        "zone_elapsed": zone_elapsed,
        "is_resistance": is_resistance,
    }


# ============================================================
# BATTLE-STATS
# ============================================================

def consultar_zona(
    battle_id,
    division_id,
    battle_zone_id
):
    url = (
        f"https://www.erepublik.com/en/military/"
        f"battle-stats/{battle_id}/"
        f"{division_id}/{battle_zone_id}"
    )

    response = requests.get(
        url,
        headers=headers_ajax(battle_id),
        timeout=15,
    )

    try:
        data = response.json()

    except ValueError:
        raise ValueError(
            f"battle-stats no devolvió JSON. "
            f"HTTP {response.status_code}"
        )

    if "error" in data:
        raise ValueError(
            f"eRepublik: {data['error']}"
        )

    return data


# ============================================================
# LEER BARRA DE UNA DIVISIÓN
# ============================================================

def obtener_barra(
    battle_id,
    division_id,
    battle_zone_id
):
    data = consultar_zona(
        battle_id,
        division_id,
        battle_zone_id,
    )

    division_data = data.get(
        "division",
        {}
    )

    domination = division_data.get(
        "domination",
        {}
    )

    bar = division_data.get(
        "bar",
        {}
    )

    porcentaje = domination.get(
        str(battle_zone_id)
    )

    country_id = bar.get(
        str(battle_zone_id)
    )

    if porcentaje is None:
        raise ValueError(
            f"No encontré domination "
            f"para {battle_zone_id}"
        )

    if country_id is None:
        raise ValueError(
            f"No encontré country ID "
            f"para {battle_zone_id}"
        )

    return {
        "country_id": int(country_id),
        "percentage": float(porcentaje),
    }


# ============================================================
# NOMBRE DE PAÍS
# ============================================================

def nombre_pais(country_id, countries):
    nombre = countries.get(
        str(country_id)
    )

    if nombre:
        return nombre.replace("-", " ")

    nombre = PAISES_FALLBACK.get(
        country_id
    )

    if nombre:
        return nombre.replace("-", " ")

    return f"País {country_id}"


# ============================================================
# /START
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


# ============================================================
# /ESTADO
# ============================================================

async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "✅ Bot funcionando\n"
        "✅ battlefield + battle-stats"
    )


# ============================================================
# /TEST
# ============================================================

async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:

        # ----------------------------------------------------
        # Información general
        # ----------------------------------------------------

        info = obtener_info_batalla(
            BATTLE_ID,
            PAGE_ZONE_ID,
        )

        invader_id = info[
            "invader_id"
        ]

        defender_id = info[
            "defender_id"
        ]

        countries = info[
            "countries"
        ]

        zonas = info[
            "zonas"
        ]

        atacante = nombre_pais(
            invader_id,
            countries
        )

        defensor = nombre_pais(
            defender_id,
            countries
        )

        # ----------------------------------------------------
        # Barras
        # ----------------------------------------------------

        resultados = {}

        for division_id in [3, 4, 11]:

            zone_id = zonas[
                division_id
            ]

            barra = obtener_barra(
                BATTLE_ID,
                division_id,
                zone_id,
            )

            country_barra = barra[
                "country_id"
            ]

            porcentaje_barra = barra[
                "percentage"
            ]

            otro_porcentaje = (
                100 - porcentaje_barra
            )

            if (
                country_barra
                == defender_id
            ):

                porcentaje_defensor = (
                    porcentaje_barra
                )

                porcentaje_atacante = (
                    otro_porcentaje
                )

            elif (
                country_barra
                == invader_id
            ):

                porcentaje_atacante = (
                    porcentaje_barra
                )

                porcentaje_defensor = (
                    otro_porcentaje
                )

            else:
                raise ValueError(
                    "El país asociado a la barra "
                    "no coincide con atacante "
                    "ni defensor."
                )

            resultados[
                division_id
            ] = {
                "defensor":
                    porcentaje_defensor,
                "atacante":
                    porcentaje_atacante,
                "zone_id":
                    zone_id,
            }

        # ----------------------------------------------------
        # MENSAJE
        # ----------------------------------------------------

        tipo = (
            "RW"
            if info["is_resistance"]
            else "Batalla normal"
        )

        mensaje = (
            "⚔️ BATALLA\n\n"
            f"🛡️ Defensor: {defensor}\n"
            f"⚔️ Atacante: {atacante}\n"
            f"Tipo: {tipo}\n"
        )

        if info["zone_elapsed"]:
            mensaje += (
                f"⏱️ Tiempo de ronda: "
                f"{info['zone_elapsed']}\n"
            )

        mensaje += "\n"

        for division_id in [3, 4, 11]:

            nombre = DIVISIONES[
                division_id
            ]

            resultado = resultados[
                division_id
            ]

            mensaje += (
                f"{nombre}\n"
                f"🛡️ {defensor}: "
                f"{resultado['defensor']:.2f}%\n"
                f"⚔️ {atacante}: "
                f"{resultado['atacante']:.2f}%\n\n"
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


# ============================================================
# /AYUDA
# ============================================================

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
        .token(
            telegram_token.strip()
        )
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "estado",
            estado
        )
    )

    app.add_handler(
        CommandHandler(
            "test",
            test
        )
    )

    app.add_handler(
        CommandHandler(
            "ayuda",
            ayuda
        )
    )

    print(
        "eArgentina Battle Bot iniciado..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
