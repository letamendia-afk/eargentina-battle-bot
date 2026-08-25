import os
import html
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

EREPUBLIK_BASE_URL = "https://www.erepublik.com"

MONITORED_COUNTRY_ID = int(
    os.getenv("MONITORED_COUNTRY_ID", "27")
)

BATTLE_ID_TEST = 931103

DIVISIONES = {
    3: "D3",
    4: "D4",
    11: "A",
}


# ============================================================
# ADMINISTRADORES
# ============================================================
#
# Primero usaremos /id para obtener tu Telegram User ID.
# Después lo agregaremos acá o, mejor aún, como variable
# de entorno.
# ============================================================

ADMIN_TELEGRAM_IDS = set()


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

MONITORED_COUNTRY_NAME = PAISES.get(
    MONITORED_COUNTRY_ID,
    f"País {MONITORED_COUNTRY_ID}"
)


# ============================================================
# NORMALIZACIÓN DE NOMBRES
# ============================================================

def normalizar_texto(texto):
    return (
        texto.lower()
        .strip()
        .replace("-", " ")
        .replace("_", " ")
    )


def buscar_country_id(nombre):
    buscado = normalizar_texto(nombre)

    for country_id, country_name in PAISES.items():

        if normalizar_texto(country_name) == buscado:
            return country_id

    return None


# ============================================================
# REGLAS DE CAMPAÑA
# ============================================================
#
# Por ahora viven en memoria.
#
# Valores:
# DEFENSOR
# ATACANTE
#
# Chile queda precargado para conservar la regla actual.
# ============================================================

REGLAS_CAMPANIA = {
    64: "DEFENSOR",
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
            f"{EREPUBLIK_BASE_URL}/"
            "en/military/campaigns"
        ),
        "Cookie": obtener_cookie(),
    }


# ============================================================
# CONSULTAR CAMPAÑAS
# ============================================================

def consultar_campanas():
    url = (
        f"{EREPUBLIK_BASE_URL}/"
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
# ENCONTRAR BATALLAS
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
                        resultado[int(clave)] = contenido
                    except ValueError:
                        pass

                recorrer(contenido)

        elif isinstance(valor, list):

            for item in valor:
                recorrer(item)

    recorrer(data)

    return resultado


def buscar_batalla(data, battle_id):
    return obtener_batallas(data).get(
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

    if not isinstance(divisiones, dict):
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

        if not isinstance(wall, dict):
            continue

        country_id = wall.get("for")
        porcentaje = wall.get("dom")

        if (
            country_id is None
            or porcentaje is None
        ):
            continue

        try:
            resultado[division_id] = {
                "zone_id": int(zone_id),
                "country_id": int(country_id),
                "percentage": float(porcentaje),
            }

        except (TypeError, ValueError):
            continue

    return resultado


# ============================================================
# PORCENTAJE
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
        valor_float = float(valor)

        if valor_float.is_integer():
            return str(
                int(valor_float)
            )

        return f"{valor_float:.1f}"

    except (TypeError, ValueError):
        return "?"


# ============================================================
# BUSCAR BATALLAS DEL PAÍS
# ============================================================

def buscar_batallas_pais(
    data,
    country_id
):
    todas = obtener_batallas(data)

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

        invader_id = inv.get("id")
        defender_id = defender.get("id")

        try:
            invader_id = int(invader_id)
            defender_id = int(defender_id)

        except (TypeError, ValueError):
            continue

        if (
            invader_id != country_id
            and defender_id != country_id
        ):
            continue

        if invader_id == country_id:

            rival_id = defender_id
            rol = "atacante"

        else:

            rival_id = invader_id
            rol = "defensor"

        resultado.append({
            "battle_id": battle_id,
            "batalla": batalla,
            "country_id": country_id,
            "rival_id": rival_id,
            "rol": rol,
            "invader_id": invader_id,
            "defender_id": defender_id,
        })

    resultado.sort(
        key=lambda x: x[
            "battle_id"
        ],
        reverse=True
    )

    return resultado


# ============================================================
# SCORE PAÍS / RIVAL
# ============================================================

def obtener_score_pais(item):

    batalla = item[
        "batalla"
    ]

    country_id = item[
        "country_id"
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

    if invader_id == country_id:

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

def obtener_objetivo_auto(item):

    rival_id = item[
        "rival_id"
    ]

    country_id = item[
        "country_id"
    ]

    regla = REGLAS_CAMPANIA.get(
        rival_id
    )

    if regla is None:
        return None

    pais_es_atacante = (
        item["invader_id"]
        == country_id
    )

    pais_es_defensor = (
        item["defender_id"]
        == country_id
    )

    if regla == "DEFENSOR":

        if pais_es_defensor:
            return "GANAR"

        return "PERDER"

    if regla == "ATACANTE":

        if pais_es_atacante:
            return "GANAR"

        return "PERDER"

    return None


# ============================================================
# GANADOR DE DIVISIÓN
# ============================================================

def pais_ganaria_division(
    porcentaje_pais_actual,
    porcentaje_rival,
    pais_es_defensor
):

    if (
        porcentaje_pais_actual
        > porcentaje_rival
    ):
        return True

    if (
        porcentaje_pais_actual
        < porcentaje_rival
    ):
        return False

    # Empate:
    # gana el defensor.
    return pais_es_defensor


# ============================================================
# INDICADORES
# ============================================================

def indicador_division(
    porcentaje_pais_actual,
    porcentaje_rival,
    objetivo,
    pais_es_defensor
):

    if objetivo is None:
        return ""

    pais_ganaria = (
        pais_ganaria_division(
            porcentaje_pais_actual,
            porcentaje_rival,
            pais_es_defensor
        )
    )

    if objetivo == "GANAR":

        if pais_ganaria:
            return "🟢"

        return "🔴"

    if objetivo == "PERDER":

        if pais_ganaria:
            return "🔴"

        return "🟢"

    return ""


def indicador_score(
    puntos_pais,
    puntos_rival,
    objetivo
):

    if objetivo is None:
        return ""

    puntos_pais = float(
        puntos_pais
    )

    puntos_rival = float(
        puntos_rival
    )

    # Empate general:
    # neutral.
    if puntos_pais == puntos_rival:
        return ""

    pais_gana = (
        puntos_pais
        > puntos_rival
    )

    if objetivo == "GANAR":

        return (
            "🟢"
            if pais_gana
            else "🔴"
        )

    if objetivo == "PERDER":

        return (
            "🔴"
            if pais_gana
            else "🟢"
        )

    return ""


# ============================================================
# FORMATEAR BATALLA
# ============================================================

def formatear_batalla_pais(item):

    battle_id = item[
        "battle_id"
    ]

    batalla = item[
        "batalla"
    ]

    country_id = item[
        "country_id"
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

    pais_es_defensor = (
        item["defender_id"]
        == country_id
    )

    # Rol
    if rol == "atacante":
        icono_rol = "⚔️"
    else:
        icono_rol = "🛡️"

    # Link
    url = (
        f"{EREPUBLIK_BASE_URL}/"
        "en/military/battlefield/"
        f"{battle_id}"
    )

    rival_link = (
        f'<a href="{url}">'
        f'{rival}'
        f'</a>'
    )

    # Objetivo
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

    # Score
    puntos_pais, puntos_rival = (
        obtener_score_pais(
            item
        )
    )

    score_pais = formatear_score(
        puntos_pais
    )

    score_rival = formatear_score(
        puntos_rival
    )

    color_score = indicador_score(
        puntos_pais,
        puntos_rival,
        objetivo
    )

    if color_score:

        texto_score = (
            f"{color_score} "
            f"T {score_pais}-{score_rival}"
        )

    else:

        texto_score = (
            f"T {score_pais}-{score_rival}"
        )

    # Divisiones
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
                f"{nombre} --"
            )

            continue

        porcentaje_monitoreado = (
            porcentaje_pais(
                datos,
                country_id
            )
        )

        porcentaje_rival = (
            100
            - porcentaje_monitoreado
        )

        color = indicador_division(
            porcentaje_monitoreado,
            porcentaje_rival,
            objetivo,
            pais_es_defensor
        )

        pais_txt = formatear_porcentaje(
            porcentaje_monitoreado
        )

        rival_txt = formatear_porcentaje(
            porcentaje_rival
        )

        texto_division = (
            f"{nombre} "
            f"{pais_txt}%-"
            f"{rival_txt}%"
        )

        if color:

            texto_division = (
                f"{color} "
                f"{texto_division}"
            )

        partes.append(
            texto_division
        )

    return (
        f"{icono_rol} "
        f"{rival_link}"
        f"{etiqueta_objetivo}\n"
        f"{texto_score}"
        f" | "
        + " | ".join(partes)
    )


# ============================================================
# PERMISOS
# ============================================================

def es_admin(update: Update):

    if not update.effective_user:
        return False

    return (
        update.effective_user.id
        in ADMIN_TELEGRAM_IDS
    )


# ============================================================
# /ID
# ============================================================

async def mostrar_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = (
        update.effective_user.id
        if update.effective_user
        else None
    )

    chat_id = (
        update.effective_chat.id
        if update.effective_chat
        else None
    )

    await update.message.reply_text(
        "🆔 Datos de Telegram\n\n"
        f"User ID: {user_id}\n"
        f"Chat ID: {chat_id}"
    )


# ============================================================
# /ORDEN
# ============================================================

async def orden(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not es_admin(update):

        await update.message.reply_text(
            "⛔ Este comando está reservado "
            "a administradores."
        )

        return

    if len(context.args) < 2:

        await update.message.reply_text(
            "Uso:\n"
            "/orden Chile defensor\n"
            "/orden Chile atacante"
        )

        return

    regla = context.args[-1].upper()

    if regla not in {
        "DEFENSOR",
        "ATACANTE"
    }:

        await update.message.reply_text(
            "La orden debe terminar en:\n"
            "defensor o atacante"
        )

        return

    nombre = " ".join(
        context.args[:-1]
    )

    country_id = buscar_country_id(
        nombre
    )

    if country_id is None:

        await update.message.reply_text(
            f"❌ No encontré el país: {nombre}"
        )

        return

    if country_id == MONITORED_COUNTRY_ID:

        await update.message.reply_text(
            "❌ No corresponde cargar una "
            "regla contra el propio país monitoreado."
        )

        return

    REGLAS_CAMPANIA[
        country_id
    ] = regla

    await update.message.reply_text(
        "✅ Orden actualizada\n\n"
        f"{nombre_pais(country_id)} → "
        f"gana {regla}"
    )


# ============================================================
# /SINORDEN
# ============================================================

async def sinorden(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not es_admin(update):

        await update.message.reply_text(
            "⛔ Este comando está reservado "
            "a administradores."
        )

        return

    if not context.args:

        await update.message.reply_text(
            "Uso:\n"
            "/sinorden Chile"
        )

        return

    nombre = " ".join(
        context.args
    )

    country_id = buscar_country_id(
        nombre
    )

    if country_id is None:

        await update.message.reply_text(
            f"❌ No encontré el país: {nombre}"
        )

        return

    if country_id not in REGLAS_CAMPANIA:

        await update.message.reply_text(
            f"{nombre_pais(country_id)} "
            "no tiene una orden cargada."
        )

        return

    del REGLAS_CAMPANIA[
        country_id
    ]

    await update.message.reply_text(
        "✅ Orden eliminada\n\n"
        f"{nombre_pais(country_id)}"
    )


# ============================================================
# /ORDENES
# ============================================================

async def ordenes(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not REGLAS_CAMPANIA:

        await update.message.reply_text(
            "📋 No hay órdenes cargadas."
        )

        return

    lineas = [
        "📋 ÓRDENES ACTIVAS",
        ""
    ]

    for country_id, regla in sorted(
        REGLAS_CAMPANIA.items(),
        key=lambda x: nombre_pais(
            x[0]
        )
    ):

        lineas.append(
            f"• {nombre_pais(country_id)} "
            f"→ {regla}"
        )

    lineas.extend([
        "",
        "⚠️ Las órdenes actuales viven "
        "en memoria y todavía no sobreviven "
        "a un reinicio del bot."
    ])

    await update.message.reply_text(
        "\n".join(lineas)
    )


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🌎 eRepublik Country Monitor\n\n"
        "/batallas - Batallas activas\n"
        "/ordenes - Órdenes actuales\n"
        "/id - Ver IDs de Telegram\n"
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
        f"País monitoreado: "
        f"{MONITORED_COUNTRY_NAME} "
        f"({MONITORED_COUNTRY_ID})\n"
        f"Órdenes cargadas: "
        f"{len(REGLAS_CAMPANIA)}\n\n"
        "Empate de división → defensor\n"
        "Empate de score total → neutral"
    )


# ============================================================
# /BATALLAS
# ============================================================

async def mostrar_batallas(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        data = consultar_campanas()

        batallas = buscar_batallas_pais(
            data,
            MONITORED_COUNTRY_ID
        )

        if not batallas:

            await update.message.reply_text(
                f"{MONITORED_COUNTRY_NAME} "
                "no tiene batallas activas."
            )

            return

        bloques = [
            formatear_batalla_pais(item)
            for item in batallas
        ]

        mensaje = (
            f"🌎 <b>BATALLAS DE "
            f"{html.escape(MONITORED_COUNTRY_NAME.upper())}"
            f"</b>\n"
            f"Activas: {len(batallas)}\n\n"
            + "\n\n".join(bloques)
            + "\n\n"
            + "ℹ️ <b>[AUTO]</b>: objetivo "
              "deducido de la regla cargada; "
              "puede estar equivocado si "
              "cambió el acuerdo."
        )

        await update.message.reply_text(
            mensaje,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:

        await update.message.reply_text(
            "❌ Error en /batallas\n\n"
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
                f"{BATTLE_ID_TEST}."
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

        await update.message.reply_text(
            "🧪 BATALLA DE CONTROL\n\n"
            f"Battle ID: {BATTLE_ID_TEST}\n"
            f"🛡️ {nombre_pais(defender_id)}\n"
            f"⚔️ {nombre_pais(invader_id)}"
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
            "id",
            mostrar_id
        )
    )

    app.add_handler(
        CommandHandler(
            "orden",
            orden
        )
    )

    app.add_handler(
        CommandHandler(
            "sinorden",
            sinorden
        )
    )

    app.add_handler(
        CommandHandler(
            "ordenes",
            ordenes
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
            "batallas",
            mostrar_batallas
        )
    )

    app.add_handler(
        CommandHandler(
            "argentina",
            mostrar_batallas
        )
    )

    print(
        "eRepublik Country Monitor iniciado"
    )

    app.run_polling()


if __name__ == "__main__":
    main()
