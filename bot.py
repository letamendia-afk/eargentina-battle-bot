import os
import html
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARGENTINA_ID = 27

# Batalla conocida para mantener /test como control
BATTLE_ID_TEST = 931103

DIVISIONES = {
    3: "D3",
    4: "D4",
    11: "A",
}


# ============================================================
# REGLAS DE CAMPAÑA
# ============================================================
#
# Valores posibles:
#
# "DEFENSOR" -> gana el país defensor
# "ATACANTE" -> gana el país atacante
#
# La etiqueta [AUTO] significa que GANAR/PERDER fue
# deducido automáticamente y podría quedar desactualizada
# si cambia el acuerdo.
# ============================================================

REGLAS_CAMPANIA = {
    64: "DEFENSOR",   # Chile: gana el defensor hasta nueva orden
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
# COOKIE / HEADERS
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
# CONSULTAR CAMPAÑAS
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

    if response.status_code != 200:
        raise ValueError(
            f"campaignsJson/list respondió "
            f"HTTP {response.status_code}"
        )

    try:
        return response.json()

    except ValueError:
        raise ValueError(
            "campaignsJson/list no devolvió JSON"
        )


# ============================================================
# ENCONTRAR OBJETOS DE BATALLA
# ============================================================

def obtener_batallas(data):
    resultado = {}

    def recorrer(valor):

        if isinstance(valor, dict):

            for clave, contenido in valor.items():

                if (
                    isinstance(contenido, dict)
                    and str(clave).isdigit()
                    and isinstance(
                        contenido.get("inv"),
                        dict
                    )
                    and isinstance(
                        contenido.get("def"),
                        dict
                    )
                ):

                    try:
                        resultado[
                            int(clave)
                        ] = contenido

                    except ValueError:
                        pass

                recorrer(contenido)

        elif isinstance(valor, list):

            for item in valor:
                recorrer(item)

    recorrer(data)

    return resultado


# ============================================================
# BUSCAR BATALLA
# ============================================================

def buscar_batalla(data, battle_id):
    return obtener_batallas(
        data
    ).get(
        int(battle_id)
    )


# ============================================================
# NOMBRE DE PAÍS
# ============================================================

def nombre_pais(country_id):
    return PAISES.get(
        int(country_id),
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

        try:
            division_id = int(
                division_id
            )

        except (TypeError, ValueError):
            continue

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

        try:

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

        except (TypeError, ValueError):
            continue

    return resultado


# ============================================================
# PORCENTAJE DE UN PAÍS
# ============================================================

def porcentaje_pais(
    datos_division,
    country_id
):

    pais_wall = datos_division[
        "country_id"
    ]

    porcentaje_wall = datos_division[
        "percentage"
    ]

    if pais_wall == country_id:
        return porcentaje_wall

    return 100 - porcentaje_wall


# ============================================================
# FORMATO
# ============================================================

def formatear_porcentaje(valor):

    if abs(
        valor - round(valor)
    ) < 0.005:

        return str(
            int(round(valor))
        )

    return f"{valor:.1f}"


def formatear_score(valor):

    try:
        valor_float = float(
            valor
        )

        if valor_float.is_integer():

            return str(
                int(valor_float)
            )

        return f"{valor_float:.1f}"

    except (TypeError, ValueError):

        return "?"


# ============================================================
# BUSCAR BATALLAS DE ARGENTINA
# ============================================================

def buscar_batallas_argentina(
    data
):

    todas = obtener_batallas(
        data
    )

    resultado = []

    for battle_id, batalla in todas.items():

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

        try:

            invader_id = int(
                invader_id
            )

            defender_id = int(
                defender_id
            )

        except (TypeError, ValueError):
            continue

        if (
            invader_id != ARGENTINA_ID
            and defender_id != ARGENTINA_ID
        ):
            continue

        if invader_id == ARGENTINA_ID:

            rival_id = defender_id
            rol = "atacante"

        else:

            rival_id = invader_id
            rol = "defensor"

        resultado.append({
            "battle_id":
                battle_id,

            "batalla":
                batalla,

            "rival_id":
                rival_id,

            "rol":
                rol,

            "invader_id":
                invader_id,

            "defender_id":
                defender_id,
        })

    resultado.sort(
        key=lambda x: x[
            "battle_id"
        ],
        reverse=True
    )

    return resultado


# ============================================================
# SCORE ARGENTINA / RIVAL
# ============================================================

def obtener_score_argentina(
    item
):

    batalla = item[
        "batalla"
    ]

    invader_id = item[
        "invader_id"
    ]

    inv = batalla.get(
        "inv",
        {}
    )

    defender = batalla.get(
        "def",
        {}
    )

    puntos_invader = inv.get(
        "points",
        0
    )

    puntos_defender = defender.get(
        "points",
        0
    )

    if invader_id == ARGENTINA_ID:

        return (
            puntos_invader,
            puntos_defender
        )

    return (
        puntos_defender,
        puntos_invader
    )


# ============================================================
# OBJETIVO AUTOMÁTICO
# ============================================================

def obtener_objetivo_auto(
    item
):

    rival_id = item[
        "rival_id"
    ]

    regla = REGLAS_CAMPANIA.get(
        rival_id
    )

    if regla is None:
        return None

    argentina_es_atacante = (
        item["invader_id"]
        == ARGENTINA_ID
    )

    argentina_es_defensor = (
        item["defender_id"]
        == ARGENTINA_ID
    )

    if regla == "DEFENSOR":

        if argentina_es_defensor:
            return "GANAR"

        return "PERDER"

    if regla == "ATACANTE":

        if argentina_es_atacante:
            return "GANAR"

        return "PERDER"

    return None


# ============================================================
# GANADOR SI LA DIVISIÓN TERMINARA AHORA
# ============================================================

def argentina_ganaria_division(
    porcentaje_argentina,
    porcentaje_rival,
    argentina_es_defensor
):

    # Argentina tiene más influencia
    if porcentaje_argentina > porcentaje_rival:
        return True

    # Argentina tiene menos influencia
    if porcentaje_argentina < porcentaje_rival:
        return False

    # EMPATE:
    # el punto va al defensor
    return argentina_es_defensor


# ============================================================
# COLOR DE UNA DIVISIÓN
# ============================================================

def indicador_division(
    porcentaje_argentina,
    porcentaje_rival,
    objetivo,
    argentina_es_defensor
):

    # Sin regla cargada
    if objetivo is None:
        return "⚪"

    argentina_ganaria = (
        argentina_ganaria_division(
            porcentaje_argentina,
            porcentaje_rival,
            argentina_es_defensor
        )
    )

    # Si necesitamos GANAR
    if objetivo == "GANAR":

        if argentina_ganaria:
            return "🟢"

        return "🔴"

    # Si necesitamos PERDER
    if objetivo == "PERDER":

        if argentina_ganaria:
            return "🔴"

        return "🟢"

    return "⚪"


# ============================================================
# COLOR DEL TANTEADOR TOTAL
# ============================================================

def indicador_score(
    puntos_argentina,
    puntos_rival,
    objetivo,
    argentina_es_defensor
):

    if objetivo is None:
        return "⚪"

    puntos_argentina = float(
        puntos_argentina
    )

    puntos_rival = float(
        puntos_rival
    )

    # Si Argentina va arriba
    if puntos_argentina > puntos_rival:
        argentina_favorecida = True

    # Si Argentina va abajo
    elif puntos_argentina < puntos_rival:
        argentina_favorecida = False

    # Si el score general está empatado,
    # usamos el rol de defensor como criterio
    # para no mostrar un estado neutral.
    else:
        argentina_favorecida = (
            argentina_es_defensor
        )

    if objetivo == "GANAR":

        if argentina_favorecida:
            return "🟢"

        return "🔴"

    if objetivo == "PERDER":

        if argentina_favorecida:
            return "🔴"

        return "🟢"

    return "⚪"


# ============================================================
# FORMATEAR BATALLA ARGENTINA
# ============================================================

def formatear_batalla_argentina(
    item
):

    battle_id = item[
        "battle_id"
    ]

    batalla = item[
        "batalla"
    ]

    rival_id = item[
        "rival_id"
    ]

    rol = item[
        "rol"
    ]

    rival = html.escape(
        nombre_pais(
            rival_id
        )
    )

    argentina_es_defensor = (
        item["defender_id"]
        == ARGENTINA_ID
    )

    # --------------------------------------------------------
    # ROL
    # --------------------------------------------------------

    if rol == "atacante":
        icono_rol = "⚔️"
    else:
        icono_rol = "🛡️"

    # --------------------------------------------------------
    # LINK
    # --------------------------------------------------------

    url = (
        "https://www.erepublik.com/"
        "en/military/battlefield/"
        f"{battle_id}"
    )

    rival_link = (
        f'<a href="{url}">'
        f'{rival}'
        f'</a>'
    )

    # --------------------------------------------------------
    # OBJETIVO
    # --------------------------------------------------------

    objetivo = obtener_objetivo_auto(
        item
    )

    if objetivo is None:

        etiqueta_objetivo = ""

    else:

        etiqueta_objetivo = (
            f" | <b>[AUTO] "
            f"{objetivo}</b>"
        )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    puntos_argentina, puntos_rival = (
        obtener_score_argentina(
            item
        )
    )

    score_arg = formatear_score(
        puntos_argentina
    )

    score_rival = formatear_score(
        puntos_rival
    )

    color_score = indicador_score(
        puntos_argentina,
        puntos_rival,
        objetivo,
        argentina_es_defensor
    )

    # --------------------------------------------------------
    # DIVISIONES
    # --------------------------------------------------------

    divisiones = obtener_divisiones(
        batalla
    )

    partes = []

    for division_id in [
        3,
        4,
        11
    ]:

        nombre = DIVISIONES[
            division_id
        ]

        datos = divisiones.get(
            division_id
        )

        if datos is None:

            partes.append(
                f"⚪ {nombre} --"
            )

            continue

        porcentaje_arg = porcentaje_pais(
            datos,
            ARGENTINA_ID
        )

        porcentaje_rival = (
            100
            - porcentaje_arg
        )

        color = indicador_division(
            porcentaje_arg,
            porcentaje_rival,
            objetivo,
            argentina_es_defensor
        )

        arg_txt = formatear_porcentaje(
            porcentaje_arg
        )

        rival_txt = formatear_porcentaje(
            porcentaje_rival
        )

        partes.append(
            f"{color} {nombre} "
            f"{arg_txt}%-"
            f"{rival_txt}%"
        )

    linea_divisiones = (
        " | ".join(
            partes
        )
    )

    return (
        f"{icono_rol} "
        f"{rival_link}"
        f"{etiqueta_objetivo}\n"
        f"{color_score} "
        f"T {score_arg}-{score_rival}"
        f" | "
        f"{linea_divisiones}"
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
        "/argentina - Batallas activas "
        "de Argentina\n"
        "/test - Batalla de control\n"
        "/estado - Estado del bot"
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
        "Fuente: campaignsJson/list\n"
        f"Argentina ID: {ARGENTINA_ID}\n"
        f"Battle test: {BATTLE_ID_TEST}\n\n"
        "Reglas automáticas:\n"
        "🇨🇱 Chile → gana defensor\n\n"
        "Empates de división → "
        "ganador: defensor"
    )


# ============================================================
# /ARGENTINA
# ============================================================

async def argentina(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        data = consultar_campanas()

        batallas = (
            buscar_batallas_argentina(
                data
            )
        )

        if not batallas:

            await update.message.reply_text(
                "🇦🇷 Argentina no tiene "
                "batallas activas en este momento."
            )

            return

        bloques = []

        for item in batallas:

            bloques.append(
                formatear_batalla_argentina(
                    item
                )
            )

        mensaje = (
            "🇦🇷 <b>BATALLAS DE ARGENTINA</b>\n"
            f"Activas: {len(batallas)}\n\n"
            + "\n\n".join(
                bloques
            )
            + "\n\n"
            + "ℹ️ <b>[AUTO]</b>: objetivo "
              "deducido automáticamente de la "
              "regla cargada; puede estar "
              "equivocado si cambió el acuerdo."
        )

        await update.message.reply_text(
            mensaje,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:

        await update.message.reply_text(
            "❌ Error en /argentina\n\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# /TEST
# ============================================================

async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        data = consultar_campanas()

        batalla = buscar_batalla(
            data,
            BATTLE_ID_TEST
        )

        if batalla is None:

            raise ValueError(
                f"No encontré la batalla "
                f"{BATTLE_ID_TEST} entre "
                f"las campañas activas."
            )

        inv = batalla.get(
            "inv",
            {}
        )

        defender = batalla.get(
            "def",
            {}
        )

        invader_id = int(
            inv["id"]
        )

        defender_id = int(
            defender["id"]
        )

        atacante = nombre_pais(
            invader_id
        )

        defensor = nombre_pais(
            defender_id
        )

        puntos_atacante = inv.get(
            "points",
            0
        )

        puntos_defensor = defender.get(
            "points",
            0
        )

        divisiones = obtener_divisiones(
            batalla
        )

        mensaje = (
            "🧪 BATALLA DE CONTROL\n\n"
            f"Battle ID: "
            f"{BATTLE_ID_TEST}\n"
            f"🛡️ {defensor}: "
            f"{formatear_score(puntos_defensor)}\n"
            f"⚔️ {atacante}: "
            f"{formatear_score(puntos_atacante)}\n\n"
        )

        for division_id in [
            3,
            4,
            11
        ]:

            nombre = DIVISIONES[
                division_id
            ]

            datos = divisiones.get(
                division_id
            )

            if datos is None:

                mensaje += (
                    f"{nombre}: "
                    f"sin datos\n"
                )

                continue

            porcentaje_defensor = (
                porcentaje_pais(
                    datos,
                    defender_id
                )
            )

            porcentaje_atacante = (
                100
                - porcentaje_defensor
            )

            mensaje += (
                f"{nombre}: "
                f"{defensor} "
                f"{porcentaje_defensor:.2f}% | "
                f"{atacante} "
                f"{porcentaje_atacante:.2f}%\n"
            )

        await update.message.reply_text(
            mensaje
        )

    except Exception as e:

        await update.message.reply_text(
            "❌ Error en /test\n\n"
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

    app.add_handler(
        CommandHandler(
            "argentina",
            argentina
        )
    )

    print(
        "eArgentina Battle Bot iniciado"
    )

    app.run_polling()


if __name__ == "__main__":
    main()
