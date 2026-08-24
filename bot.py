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
# CONSEGUIR UNA RESPUESTA VÁLIDA
# ============================================================

def obtener_respuesta_inicial(battle_id, zone_id):
    """
    Probamos D3, D4 y AIR hasta conseguir una respuesta
    que contenga datos útiles de la batalla.
    """

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
# LEER UNA DIVISIÓN
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
            f"No encontré país asociado a la barra {zone_id}"
        )

    porcentaje = float(porcentaje)
    pais_barra = int(pais_barra)

    # Dentro de division aparecen claves numéricas
    # correspondientes a los países.
    paises = []

    for clave in division_data.keys():

        try:
            country_id = int(clave)
        except (ValueError, TypeError):
            continue

        if country_id not in paises:
            paises.append(country_id)

    # Si encontramos el país contrario
    pais_contrario = None

    for country_id in paises:
        if country_id != pais_barra:
            pais_contrario = country_id
            break

    return {
        "division": division_id,
        "zone_id": zone_id,
        "pais_barra": pais_barra,
        "pais_contrario": pais_contrario,
        "porcentaje_barra": porcentaje,
        "porcentaje_contrario": 100 - porcentaje,
        "paises_detectados": paises,
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

        # Obtener respuesta general
        data_inicial = obtener_respuesta_inicial(
            BATTLE_ID,
            INITIAL_ZONE_ID,
        )

        # Encontrar automáticamente D3 / D4 / AIR
        zonas = buscar_zonas(data_inicial)

        mensaje = (
            "🔎 Batalla detectada\n\n"
            f"Battle ID: {BATTLE_ID}\n\n"
        )

        paises_globales = set()

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
                datos = obtener_datos_division(
                    BATTLE_ID,
                    division_id,
                    zone_id,
                )

                pais_a = datos["pais_barra"]
                pais_b = datos["pais_contrario"]

                porcentaje_a = (
                    datos["porcentaje_barra"]
                )

                porcentaje_b = (
                    datos["porcentaje_contrario"]
                )

                paises_globales.update(
                    datos["paises_detectados"]
                )

                mensaje += f"{nombre}\n"

                mensaje += (
                    f"País {pais_a}: "
                    f"{porcentaje_a:.2f}%\n"
                )

                if pais_b is not None:
                    mensaje += (
                        f"País {pais_b}: "
                        f"{porcentaje_b:.2f}%\n"
                    )
                else:
                    mensaje += (
                        f"Otro país: "
                        f"{porcentaje_b:.2f}%\n"
                    )

                mensaje += (
                    f"Zone: {zone_id}\n\n"
                )

            except Exception as e:
                mensaje += (
                    f"❌ {nombre}: {e}\n\n"
                )

        mensaje += (
            "Países detectados: "
            f"{sorted(paises_globales)}\n\n"
        )

        mensaje += (
            "🔗 "
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{BATTLE_ID}"
        )

        await update.message.reply_text(
            mensaje
        )

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
