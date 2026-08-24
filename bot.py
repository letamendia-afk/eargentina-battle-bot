import os
import re
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIGURACIÓN
# ============================================================

BATTLE_ID = 930844

DIVISIONES = {
    3: "D3",
    4: "D4",
    11: "AIR",
}


# ============================================================
# PAÍSES
# ============================================================

PAISES = {
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
    34: "Czech Republic",
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
    84: "New Zealand",
    170: "Nigeria",
    73: "North Korea",
    79: "North Macedonia",
    37: "Norway",
    57: "Pakistan",
    75: "Paraguay",
    77: "Peru",
    67: "Philippines",
    35: "Poland",
    53: "Portugal",
    81: "Republic of China Taiwan",
    52: "Republic of Moldova",
    1: "Romania",
    41: "Russia",
    164: "Saudi Arabia",
    65: "Serbia",
    68: "Singapore",
    36: "Slovakia",
    61: "Slovenia",
    51: "South Africa",
    47: "South Korea",
    15: "Spain",
    38: "Sweden",
    30: "Switzerland",
    59: "Thailand",
    43: "Turkey",
    40: "Ukraine",
    166: "United Arab Emirates",
    29: "United Kingdom",
    74: "Uruguay",
    24: "USA",
    28: "Venezuela",
}


# ============================================================
# COOKIE
# ============================================================

def obtener_cookie():
    cookie = os.getenv("EREPUBLIK_COOKIE")

    if not cookie:
        raise ValueError(
            "No se encontró EREPUBLIK_COOKIE"
        )

    return cookie.strip()


# ============================================================
# HEADERS AJAX
# ============================================================

def headers_ajax(battle_id):

    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "application/json, "
            "text/javascript, */*; q=0.01"
        ),
        "X-Requested-With": "XMLHttpRequest",
        "Referer": (
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{battle_id}"
        ),
        "Cookie": obtener_cookie(),
    }


# ============================================================
# HEADERS HTML
# ============================================================

def headers_html():

    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": (
            "es-AR,es;q=0.9,en;q=0.8"
        ),
        "Cookie": obtener_cookie(),
    }


# ============================================================
# BATTLE-STATS GENERAL
# ============================================================

def consultar_stats_general(battle_id):

    url = (
        f"https://www.erepublik.com/en/military/"
        f"battle-stats/{battle_id}"
    )

    response = requests.get(
        url,
        headers=headers_ajax(battle_id),
        timeout=20
    )

    try:
        data = response.json()

    except ValueError:
        raise ValueError(
            f"battle-stats general no devolvió JSON. "
            f"HTTP {response.status_code}"
        )

    if (
        isinstance(data, dict)
        and "error" in data
    ):
        raise ValueError(
            f"eRepublik respondió: {data['error']}"
        )

    return data


# ============================================================
# BUSCAR ZONAS
# ============================================================

def buscar_zonas(obj):

    encontrados = []

    def recorrer(valor):

        if isinstance(valor, dict):

            if (
                "battle_zone_id" in valor
                and "division" in valor
            ):

                division = valor.get(
                    "division"
                )

                zone_id = valor.get(
                    "battle_zone_id"
                )

                country_id = valor.get(
                    "side_country_id"
                )

                if (
                    division in DIVISIONES
                    and zone_id
                ):

                    encontrados.append({
                        "division": int(
                            division
                        ),
                        "zone_id": int(
                            zone_id
                        ),
                        "country_id": (
                            int(country_id)
                            if country_id
                            is not None
                            else None
                        )
                    })

            for subvalor in valor.values():
                recorrer(subvalor)

        elif isinstance(valor, list):

            for item in valor:
                recorrer(item)

    recorrer(obj)

    return encontrados


# ============================================================
# ZONAS ACTUALES
# ============================================================

def zonas_actuales(encontrados):

    resultado = {}

    for item in encontrados:

        division = item[
            "division"
        ]

        actual = resultado.get(
            division
        )

        if (
            actual is None
            or item["zone_id"]
            > actual["zone_id"]
        ):

            resultado[
                division
            ] = item

    return resultado


# ============================================================
# PAÍSES DETECTADOS
# ============================================================

def detectar_paises(encontrados):

    resultado = set()

    for item in encontrados:

        country_id = item.get(
            "country_id"
        )

        if country_id:
            resultado.add(
                country_id
            )

    return sorted(resultado)


# ============================================================
# SERVER DATA
# ============================================================

def obtener_server_data(
    battle_id,
    zone_id
):

    # Probamos distintas variantes por robustez.
    urls = [
        (
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{battle_id}/{zone_id}"
        ),
        (
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{battle_id}/0/"
            f"fighterStatistics"
        ),
        (
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{battle_id}"
        ),
    ]

    html = None

    for url in urls:

        try:

            response = requests.get(
                url,
                headers=headers_html(),
                timeout=20
            )

            if response.status_code != 200:
                continue

            contenido = response.text

            if (
                '"realInvaderId"'
                in contenido
                and '"realDefenderId"'
                in contenido
            ):

                html = contenido
                break

        except requests.RequestException:
            continue

    if html is None:

        raise ValueError(
            "No encontré SERVER_DATA "
            "con atacante y defensor."
        )

    # --------------------------------------------------------
    # REAL INVADER
    # --------------------------------------------------------

    match = re.search(
        r'"realInvaderId"\s*:\s*(\d+)',
        html
    )

    if not match:

        raise ValueError(
            "No encontré realInvaderId"
        )

    real_invader_id = int(
        match.group(1)
    )

    # --------------------------------------------------------
    # REAL DEFENDER
    # --------------------------------------------------------

    match = re.search(
        r'"realDefenderId"\s*:\s*(\d+)',
        html
    )

    if not match:

        raise ValueError(
            "No encontré realDefenderId"
        )

    real_defender_id = int(
        match.group(1)
    )

    # --------------------------------------------------------
    # INVADER NORMAL
    # --------------------------------------------------------

    match = re.search(
        r'"invaderId"\s*:\s*(\d+)',
        html
    )

    invader_id = (
        int(match.group(1))
        if match
        else None
    )

    # --------------------------------------------------------
    # DEFENDER NORMAL
    # --------------------------------------------------------

    match = re.search(
        r'"defenderId"\s*:\s*(\d+)',
        html
    )

    defender_id = (
        int(match.group(1))
        if match
        else None
    )

    # --------------------------------------------------------
    # MUST INVERT
    # --------------------------------------------------------

    match = re.search(
        r'"mustInvert"\s*:\s*'
        r'(true|false)',
        html
    )

    must_invert = (
        match.group(1) == "true"
        if match
        else False
    )

    # --------------------------------------------------------
    # RESISTANCE WAR
    # --------------------------------------------------------

    match = re.search(
        r'"isResistance"\s*:\s*'
        r'(true|false)',
        html
    )

    is_resistance = (
        match.group(1) == "true"
        if match
        else False
    )

    # --------------------------------------------------------
    # TIEMPO TRANSCURRIDO
    # --------------------------------------------------------

    match = re.search(
        r'"zoneElapsedTime"\s*:\s*"([^"]+)"',
        html
    )

    zone_elapsed_time = (
        match.group(1)
        if match
        else None
    )

    return {
        "real_invader_id":
            real_invader_id,

        "real_defender_id":
            real_defender_id,

        "invader_id":
            invader_id,

        "defender_id":
            defender_id,

        "must_invert":
            must_invert,

        "is_resistance":
            is_resistance,

        "zone_elapsed_time":
            zone_elapsed_time,
    }


# ============================================================
# BATTLE-STATS INDIVIDUAL
# ============================================================

def consultar_division(
    battle_id,
    division_id,
    zone_id
):

    url = (
        f"https://www.erepublik.com/en/military/"
        f"battle-stats/"
        f"{battle_id}/"
        f"{division_id}/"
        f"{zone_id}"
    )

    response = requests.get(
        url,
        headers=headers_ajax(battle_id),
        timeout=20
    )

    try:
        data = response.json()

    except ValueError:
        raise ValueError(
            f"{DIVISIONES[division_id]} "
            f"no devolvió JSON."
        )

    if (
        isinstance(data, dict)
        and "error" in data
    ):

        raise ValueError(
            f"{DIVISIONES[division_id]}: "
            f"{data['error']}"
        )

    return data


# ============================================================
# LEER DOMINATION
# ============================================================

def obtener_domination(
    data,
    zone_id
):

    division_data = data.get(
        "division",
        {}
    )

    if not isinstance(
        division_data,
        dict
    ):

        raise ValueError(
            "division no es un diccionario"
        )

    domination = division_data.get(
        "domination",
        {}
    )

    if not isinstance(
        domination,
        dict
    ):

        raise ValueError(
            "domination no es un diccionario"
        )

    porcentaje = domination.get(
        str(zone_id)
    )

    if porcentaje is None:

        raise ValueError(
            f"No encontré domination "
            f"para {zone_id}"
        )

    return float(
        porcentaje
    )


# ============================================================
# NOMBRE DE PAÍS
# ============================================================

def nombre_pais(country_id):

    return PAISES.get(
        country_id,
        f"País {country_id}"
    )


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "Bot funcionando.\n"
        "Usá /test para analizar "
        "la batalla configurada."
    )


# ============================================================
# /ESTADO
# ============================================================

async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "✅ Bot funcionando\n\n"
        f"Battle ID: {BATTLE_ID}"
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
        # 1. INFORMACIÓN GENERAL
        # ----------------------------------------------------

        data_general = (
            consultar_stats_general(
                BATTLE_ID
            )
        )

        encontrados = buscar_zonas(
            data_general
        )

        if not encontrados:

            raise ValueError(
                "No encontré zonas "
                "de D3/D4/AIR."
            )

        zonas = zonas_actuales(
            encontrados
        )

        paises_detectados = (
            detectar_paises(
                encontrados
            )
        )

        # ----------------------------------------------------
        # 2. ELEGIMOS UNA ZONA ACTUAL PARA SERVER_DATA
        # ----------------------------------------------------

        zone_para_html = None

        for division_id in [
            4,
            11,
            3
        ]:

            if division_id in zonas:

                zone_para_html = (
                    zonas[
                        division_id
                    ]["zone_id"]
                )

                break

        if zone_para_html is None:

            raise ValueError(
                "No encontré una zona "
                "para leer SERVER_DATA."
            )

        server = obtener_server_data(
            BATTLE_ID,
            zone_para_html
        )

        real_invader_id = server[
            "real_invader_id"
        ]

        real_defender_id = server[
            "real_defender_id"
        ]

        atacante = nombre_pais(
            real_invader_id
        )

        defensor = nombre_pais(
            real_defender_id
        )

        # ----------------------------------------------------
        # 3. CONSULTAR D3 / D4 / AIR
        # ----------------------------------------------------

        resultados = {}

        for division_id in [
            3,
            4,
            11
        ]:

            if division_id not in zonas:
                continue

            zone_id = zonas[
                division_id
            ]["zone_id"]

            data_division = (
                consultar_division(
                    BATTLE_ID,
                    division_id,
                    zone_id
                )
            )

            domination = (
                obtener_domination(
                    data_division,
                    zone_id
                )
            )

            # ----------------------------------------------
            # REGLA CONFIRMADA EN LAS PRUEBAS:
            #
            # domination = realDefender
            # resto      = realInvader
            # ----------------------------------------------

            porcentaje_defensor = (
                domination
            )

            porcentaje_atacante = (
                100 - domination
            )

            resultados[
                division_id
            ] = {
                "zone_id":
                    zone_id,

                "defensor":
                    porcentaje_defensor,

                "atacante":
                    porcentaje_atacante,
            }

        # ----------------------------------------------------
        # 4. MENSAJE
        # ----------------------------------------------------

        if server[
            "is_resistance"
        ]:

            tipo = "RW"

        else:

            tipo = "Batalla normal"

        mensaje = (
            "⚔️ BATALLA\n\n"
            f"Battle ID: {BATTLE_ID}\n"
            f"Tipo: {tipo}\n\n"
            f"🛡️ Defensor real: "
            f"{defensor}\n"
            f"⚔️ Atacante real: "
            f"{atacante}\n\n"
        )

        if (
            server[
                "zone_elapsed_time"
            ]
        ):

            mensaje += (
                "⏱️ Tiempo transcurrido: "
                f"{server['zone_elapsed_time']}"
                "\n\n"
            )

        for division_id in [
            3,
            4,
            11
        ]:

            nombre = DIVISIONES[
                division_id
            ]

            resultado = resultados.get(
                division_id
            )

            if not resultado:

                mensaje += (
                    f"{nombre}\n"
                    "⚠️ Sin datos\n\n"
                )

                continue

            mensaje += (
                f"{nombre}\n"
                f"🛡️ {defensor}: "
                f"{resultado['defensor']:.2f}%\n"
                f"⚔️ {atacante}: "
                f"{resultado['atacante']:.2f}%\n"
                f"Zone: "
                f"{resultado['zone_id']}\n\n"
            )

        # DEBUG mínimo, por ahora útil
        mensaje += (
            "🔧 Datos internos\n"
            f"mustInvert: "
            f"{server['must_invert']}\n"
            f"invaderId: "
            f"{server['invader_id']}\n"
            f"defenderId: "
            f"{server['defender_id']}\n"
            f"realInvaderId: "
            f"{real_invader_id}\n"
            f"realDefenderId: "
            f"{real_defender_id}\n\n"
        )

        mensaje += (
            "🔗 "
            f"https://www.erepublik.com/en/"
            f"military/battlefield/"
            f"{BATTLE_ID}"
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
# MAIN
# ============================================================

def main():

    token = os.getenv(
        "TELEGRAM_TOKEN"
    )

    if not token:

        raise ValueError(
            "No se encontró TELEGRAM_TOKEN"
        )

    app = (
        Application
        .builder()
        .token(
            token.strip()
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

    print(
        "eArgentina Battle Bot iniciado"
    )

    app.run_polling()


if __name__ == "__main__":
    main()
