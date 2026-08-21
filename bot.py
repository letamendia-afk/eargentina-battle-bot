import os
import re
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIGURACIÓN DE PRUEBA
# ============================================================

BATTLE_ID = 930049

DIVISIONES = {
    3: "D3",
    4: "D4",
    11: "AIR",
}


# ============================================================
# SESIÓN EREPUBLIK
# ============================================================

def crear_sesion():
    cookie = os.getenv("EREPUBLIK_COOKIE")

    if not cookie:
        raise ValueError("No se encontró EREPUBLIK_COOKIE")

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie.strip(),
    })

    return session


# ============================================================
# OBTENER CSRF TOKEN
# ============================================================

def obtener_csrf_token(session, battle_id):
    url = (
        f"https://www.erepublik.com/en/military/"
        f"battlefield/{battle_id}"
    )

    response = session.get(
        url,
        timeout=15
    )

    if response.status_code != 200:
        raise ValueError(
            f"No pude abrir la batalla. HTTP {response.status_code}"
        )

    html = response.text

    patron = r"var csrfToken\s*=\s*'([^']+)'"
    match = re.search(patron, html)

    if not match:
        raise ValueError(
            "No encontré csrfToken en la página."
        )

    return match.group(1)


# ============================================================
# BUSCAR BATTLE ZONE INICIAL
# ============================================================

def obtener_battle_zone_inicial(session, battle_id):
    """
    Busca una battle zone desde la página principal.
    La idea es obtener un ID válido para poder llamar
    battle-console.
    """

    url = (
        f"https://www.erepublik.com/en/military/"
        f"battlefield/{battle_id}"
    )

    response = session.get(
        url,
        timeout=15
    )

    html = response.text

    # Busca posibles battleZoneId en el HTML
    candidatos = re.findall(
        r'"battleZoneId"\s*:\s*(\d+)',
        html
    )

    if candidatos:
        return int(candidatos[0])

    # Segunda forma posible
    candidatos = re.findall(
        r'battleZoneId["\']?\s*[:=]\s*["\']?(\d+)',
        html
    )

    if candidatos:
        return int(candidatos[0])

    raise ValueError(
        "No encontré battleZoneId en la página."
    )


# ============================================================
# LLAMAR BATTLE CONSOLE
# ============================================================

def consultar_battle_console(
    session,
    battle_id,
    battle_zone_id,
    csrf_token
):
    url = (
        "https://www.erepublik.com/en/military/"
        "battle-console"
    )

    payload = {
        "battleId": battle_id,
        "zoneId": 7,
        "action": "battleConsole",
        "battleZoneId": battle_zone_id,
        "_token": csrf_token,
    }

    headers = {
        "Referer": (
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{battle_id}/0/currentBattleZone"
        ),
        "Content-Type": (
            "application/x-www-form-urlencoded"
        ),
    }

    response = session.post(
        url,
        data=payload,
        headers=headers,
        timeout=15
    )

    try:
        data = response.json()
    except ValueError:
        raise ValueError(
            "battle-console no devolvió JSON."
        )

    if "error" in data:
        raise ValueError(
            f"battle-console devolvió: {data['error']}"
        )

    return data


# ============================================================
# EXTRAER DIVISIONES
# ============================================================

def extraer_divisiones(data):
    resultado = {}

    divisiones = data.get("division", [])

    if not isinstance(divisiones, list):
        raise ValueError(
            "La estructura de 'division' no es una lista."
        )

    for item in divisiones:
        division_id = item.get("division")

        if division_id not in DIVISIONES:
            continue

        countries = item.get("countries", {})

        if len(countries) < 2:
            continue

        paises = []

        for country_id, info in countries.items():
            wall = info.get("wall")

            if wall is None:
                continue

            paises.append({
                "country_id": int(country_id),
                "wall": float(wall),
            })

        if len(paises) != 2:
            continue

        resultado[division_id] = {
            "nombre": DIVISIONES[division_id],
            "paises": paises,
            "dominating_country": (
                item.get("dominatingCountry")
            ),
            "battle_zone_id": item.get("id"),
        }

    return resultado


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
        "/test - Leer batalla completa\n"
        "/ayuda - Ver comandos"
    )


async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🇦🇷 eArgentina Battle Bot\n\n"
        "✅ Bot funcionando\n"
        "✅ eRepublik autenticado\n"
        "✅ battle-console configurado"
    )


async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        session = crear_sesion()

        csrf_token = obtener_csrf_token(
            session,
            BATTLE_ID
        )

        battle_zone_id = obtener_battle_zone_inicial(
            session,
            BATTLE_ID
        )

        data = consultar_battle_console(
            session,
            BATTLE_ID,
            battle_zone_id,
            csrf_token
        )

        divisiones = extraer_divisiones(data)

        mensaje = (
            "🧪 Lectura battle-console\n\n"
            f"Battle ID: {BATTLE_ID}\n\n"
        )

        for division_id in [3, 4, 11]:
            division = divisiones.get(division_id)

            if not division:
                mensaje += (
                    f"⚠️ {DIVISIONES[division_id]} "
                    "no encontrada\n\n"
                )
                continue

            nombre = division["nombre"]
            paises = division["paises"]

            mensaje += f"{nombre}\n"

            for pais in paises:
                mensaje += (
                    f"País {pais['country_id']}: "
                    f"{pais['wall']:.2f}%\n"
                )

            mensaje += (
                f"Dominando: "
                f"{division['dominating_country']}\n"
                f"Zone: "
                f"{division['battle_zone_id']}\n\n"
            )

        mensaje += (
            "🔗 "
            f"https://www.erepublik.com/en/military/"
            f"battlefield/{BATTLE_ID}"
        )

        await update.message.reply_text(mensaje)

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
        "/test - Leer battle-console\n"
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

    print("eArgentina Battle Bot iniciado...")

    app.run_polling()


if __name__ == "__main__":
    main()
