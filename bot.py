import os
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIGURACIÓN
# ============================================================

BATTLE_ID = 931103

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
# COOKIE Y HEADERS
# ============================================================

def obtener_cookie():
    cookie = os.getenv("EREPUBLIK_COOKIE")

    if not cookie:
        raise ValueError(
            "No se encontró EREPUBLIK_COOKIE"
        )

    return cookie.strip()


def headers_ajax():

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
            "https://www.erepublik.com/"
            "en/military/campaigns"
        ),
        "Cookie": obtener_cookie(),
    }


# ============================================================
# CAMPAIGNS JSON
# ============================================================

def consultar_campanas():

    url = (
        "https://www.erepublik.com/"
        "en/military/campaignsJson/list"
    )

    response = requests.get(
        url,
        headers=headers_ajax(),
        timeout=20
    )

    try:
        data = response.json()

    except ValueError:
        raise ValueError(
            f"campaignsJson/list no devolvió JSON. "
            f"HTTP {response.status_code}"
        )

    return data


# ============================================================
# BUSCAR BATALLA
# ============================================================

def buscar_batalla(data, battle_id):

    battle_id_str = str(
        battle_id
    )

    # A veces el objeto puede venir directamente
    if (
        isinstance(data, dict)
        and battle_id_str in data
    ):
        return data[
            battle_id_str
        ]

    # Por si viene anidado
    def recorrer(valor):

        if isinstance(valor, dict):

            if battle_id_str in valor:
                candidato = valor[
                    battle_id_str
                ]

                if isinstance(
                    candidato,
                    dict
                ):
                    return candidato

            for subvalor in valor.values():

                encontrado = recorrer(
                    subvalor
                )

                if encontrado is not None:
                    return encontrado

        elif isinstance(valor, list):

            for item in valor:

                encontrado = recorrer(
                    item
                )

                if encontrado is not None:
                    return encontrado

        return None

    return recorrer(
        data
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
# LEER DIVISIONES
# ============================================================

def obtener_divisiones(batalla):

    resultado = {}

    divisiones = batalla.get(
        "div",
        {}
    )

    if not isinstance(
        divisiones,
        dict
    ):
        return resultado

    for zone_id, division_data in divisiones.items():

        if not isinstance(
            division_data,
            dict
        ):
            continue

        division_id = division_data.get(
            "div"
        )

        if division_id not in DIVISIONES:
            continue

        wall = division_data.get(
            "wall",
            {}
        )

        if not isinstance(
            wall,
            dict
        ):
            continue

        country_id = wall.get(
            "for"
        )

        porcentaje = wall.get(
            "dom"
        )

        if (
            country_id is None
            or porcentaje is None
        ):
            continue

        resultado[
            division_id
        ] = {
            "zone_id": int(
                zone_id
            ),
            "country_id": int(
                country_id
            ),
            "percentage": float(
                porcentaje
            ),
        }

    return resultado


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
        f"Battle ID de prueba: {BATTLE_ID}\n"
        "Fuente: campaignsJson/list"
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
        # CONSULTAR CAMPAÑAS
        # ----------------------------------------------------

        data = consultar_campanas()

        batalla = buscar_batalla(
            data,
            BATTLE_ID
        )

        if batalla is None:

            raise ValueError(
                f"No encontré la batalla "
                f"{BATTLE_ID} entre las "
                f"campañas activas."
            )

        # ----------------------------------------------------
        # ATACANTE / DEFENSOR
        # ----------------------------------------------------

        inv = batalla.get(
            "inv",
            {}
        )

        defender = batalla.get(
            "def",
            {}
        )

        invader_id = inv.get(
            "id"
        )

        defender_id = defender.get(
            "id"
        )

        if (
            invader_id is None
            or defender_id is None
        ):

            raise ValueError(
                "No encontré atacante "
                "y defensor."
            )

        invader_id = int(
            invader_id
        )

        defender_id = int(
            defender_id
        )

        atacante = nombre_pais(
            invader_id
        )

        defensor = nombre_pais(
            defender_id
        )

        # ----------------------------------------------------
        # DIVISIONES
        # ----------------------------------------------------

        divisiones = obtener_divisiones(
            batalla
        )

        # ----------------------------------------------------
        # MENSAJE
        # ----------------------------------------------------

        mensaje = (
            "⚔️ BATALLA\n\n"
            f"Battle ID: {BATTLE_ID}\n\n"
            f"🛡️ Defensor: {defensor}\n"
            f"⚔️ Atacante: {atacante}\n\n"
        )

        for division_id in [
            3,
            4,
            11
        ]:

            nombre_division = (
                DIVISIONES[
                    division_id
                ]
            )

            datos = divisiones.get(
                division_id
            )

            if datos is None:

                mensaje += (
                    f"{nombre_division}\n"
                    "⚠️ Sin datos\n\n"
                )

                continue

            pais_for_id = datos[
                "country_id"
            ]

            porcentaje_for = datos[
                "percentage"
            ]

            porcentaje_otro = (
                100 - porcentaje_for
            )

            # ----------------------------------------------
            # ASIGNAR PORCENTAJE A CADA PAÍS
            # ----------------------------------------------

            if (
                pais_for_id
                == defender_id
            ):

                porcentaje_defensor = (
                    porcentaje_for
                )

                porcentaje_atacante = (
                    porcentaje_otro
                )

            elif (
                pais_for_id
                == invader_id
            ):

                porcentaje_atacante = (
                    porcentaje_for
                )

                porcentaje_defensor = (
                    porcentaje_otro
                )

            else:

                raise ValueError(
                    f"{nombre_division}: "
                    f"wall.for={pais_for_id} "
                    f"no coincide con los "
                    f"países de la batalla."
                )

            mensaje += (
                f"{nombre_division}\n"
                f"🛡️ {defensor}: "
                f"{porcentaje_defensor:.2f}%\n"
                f"⚔️ {atacante}: "
                f"{porcentaje_atacante:.2f}%\n\n"
            )

        mensaje += (
            "🔗 "
            f"https://www.erepublik.com/"
            f"en/military/battlefield/"
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
