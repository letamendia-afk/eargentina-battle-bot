import os
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIGURACIÓN
# ============================================================

BATTLE_ID = 931105

DIVISIONES = {
    3: "D3",
    4: "D4",
    11: "AIR",
}

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
# HEADERS
# ============================================================

def get_headers():
    cookie = os.getenv("EREPUBLIK_COOKIE")

    if not cookie:
        raise ValueError("No se encontró EREPUBLIK_COOKIE")

    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": (
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{BATTLE_ID}"
        ),
        "Cookie": cookie.strip(),
    }


# ============================================================
# CONSULTAR BATTLE-STATS
# ============================================================

def consultar_stats():
    url = (
        f"https://www.erepublik.com/en/military/"
        f"battle-stats/{BATTLE_ID}"
    )

    response = requests.get(
        url,
        headers=get_headers(),
        timeout=20
    )

    try:
        data = response.json()
    except Exception:
        raise ValueError(
            f"eRepublik no devolvió JSON. "
            f"HTTP {response.status_code}"
        )

    if isinstance(data, dict) and "error" in data:
        raise ValueError(
            f"eRepublik respondió: {data['error']}"
        )

    return data


# ============================================================
# BUSCAR TODAS LAS ZONAS DE D3 / D4 / AIR
# ============================================================

def buscar_barras(obj):
    encontrados = []

    def recorrer(valor):
        if isinstance(valor, dict):

            top_damage = valor.get("top_damage")

            if isinstance(top_damage, list):
                for item in top_damage:
                    if not isinstance(item, dict):
                        continue

                    division = item.get("division")
                    zone_id = item.get("battle_zone_id")
                    country_id = item.get("side_country_id")

                    if (
                        division in DIVISIONES
                        and zone_id
                        and country_id
                    ):
                        encontrados.append({
                            "division": int(division),
                            "zone_id": int(zone_id),
                            "country_id": int(country_id),
                        })

            for subvalor in valor.values():
                recorrer(subvalor)

        elif isinstance(valor, list):
            for item in valor:
                recorrer(item)

    recorrer(obj)

    return encontrados


# ============================================================
# ELEGIR LAS ZONAS MÁS NUEVAS
# ============================================================

def zonas_actuales(encontrados):
    resultado = {}

    for item in encontrados:
        division = item["division"]

        if division not in DIVISIONES:
            continue

        actual = resultado.get(division)

        if (
            actual is None
            or item["zone_id"] > actual["zone_id"]
        ):
            resultado[division] = item

    return resultado


# ============================================================
# BUSCAR DOMINATION
# ============================================================

def buscar_domination(obj, battle_zone_id):
    objetivo = str(battle_zone_id)
    resultados = []

    def recorrer(valor):
        if isinstance(valor, dict):

            domination = valor.get("domination")

            if isinstance(domination, dict):
                if objetivo in domination:

                    dato = domination[objetivo]

                    if isinstance(dato, (int, float)):
                        resultados.append(float(dato))

            for subvalor in valor.values():
                recorrer(subvalor)

        elif isinstance(valor, list):
            for item in valor:
                recorrer(item)

    recorrer(obj)

    if not resultados:
        return None

    return resultados[0]


# ============================================================
# DETECTAR PAÍSES
# ============================================================

def detectar_paises(encontrados):
    ids = set()

    for item in encontrados:
        ids.add(item["country_id"])

    return sorted(ids)


# ============================================================
# DEBUG DE UNA BATTLE ZONE
# ============================================================

def buscar_zone_debug(obj, zone_id):
    objetivo = str(zone_id)
    resultados = []

    def recorrer(valor, path="root"):

        if isinstance(valor, dict):

            for clave, subvalor in valor.items():

                if str(clave) == objetivo:

                    contenido = repr(subvalor)

                    if len(contenido) > 1000:
                        contenido = contenido[:1000] + "..."

                    resultados.append(
                        f"{path}.{clave} = {contenido}"
                    )

                recorrer(
                    subvalor,
                    f"{path}.{clave}"
                )

        elif isinstance(valor, list):

            for i, item in enumerate(valor):

                recorrer(
                    item,
                    f"{path}[{i}]"
                )

    recorrer(obj)

    return resultados


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "Bot funcionando correctamente.\n"
        "Usá /test para analizar la batalla."
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
        f"Battle ID configurada: {BATTLE_ID}"
    )


# ============================================================
# /TEST
# ============================================================

async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        data = consultar_stats()

        encontrados = buscar_barras(data)

        if not encontrados:
            raise ValueError(
                "No encontré datos de D3/D4/AIR."
            )

        paises_ids = detectar_paises(
            encontrados
        )

        zonas = zonas_actuales(
            encontrados
        )

        # ----------------------------------------
        # DEBUG D3 / D4
        # ----------------------------------------

        debug = []

        for division in [3, 4]:

            if division not in zonas:
                continue

            zone_id = zonas[
                division
            ]["zone_id"]

            encontrados_debug = (
                buscar_zone_debug(
                    data,
                    zone_id
                )
            )

            debug.append(
                f"\n🔎 {DIVISIONES[division]} "
                f"({zone_id})"
            )

            if encontrados_debug:
                debug.extend(
                    encontrados_debug[:5]
                )
            else:
                debug.append(
                    "No encontré el Zone ID como clave."
                )

        # ----------------------------------------
        # MENSAJE
        # ----------------------------------------

        mensaje = (
            "🔎 Batalla detectada\n\n"
            f"Battle ID: {BATTLE_ID}\n\n"
        )

        mensaje += "🌎 Países detectados:\n"

        for country_id in paises_ids:

            nombre = PAISES.get(
                country_id,
                f"País {country_id}"
            )

            mensaje += (
                f"• {nombre} ({country_id})\n"
            )

        mensaje += "\n"

        # ----------------------------------------
        # DIVISIONES
        # ----------------------------------------

        for division in [3, 4, 11]:

            nombre_division = DIVISIONES[
                division
            ]

            if division not in zonas:

                mensaje += (
                    f"{nombre_division}\n"
                    "Sin datos\n\n"
                )

                continue

            zona = zonas[
                division
            ]

            zone_id = zona[
                "zone_id"
            ]

            country_id = zona[
                "country_id"
            ]

            porcentaje = buscar_domination(
                data,
                zone_id
            )

            pais = PAISES.get(
                country_id,
                f"País {country_id}"
            )

            mensaje += (
                f"{nombre_division}\n"
                f"Zone: {zone_id}\n"
                f"País asociado: {pais}\n"
            )

            if porcentaje is not None:

                mensaje += (
                    f"Barra: "
                    f"{porcentaje:.2f}% / "
                    f"{100 - porcentaje:.2f}%\n"
                )

            else:

                mensaje += (
                    "Barra: no encontrada\n"
                )

            mensaje += "\n"

        # ----------------------------------------
        # DEBUG
        # ----------------------------------------

        mensaje += "\n🧪 DEBUG\n"

        mensaje += "\n".join(
            debug
        )

        # Telegram tiene límite de longitud.
        if len(mensaje) > 3900:
            mensaje = (
                mensaje[:3900]
                + "\n\n... [mensaje recortado]"
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
        .token(token.strip())
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
