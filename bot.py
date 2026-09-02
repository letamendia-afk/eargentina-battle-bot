import os
import re
import html
import asyncio
from functools import partial
from datetime import datetime, timezone

import psycopg
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

EREPUBLIK_BASE_URL = "https://www.erepublik.com"
MONITORED_COUNTRY_ID = int(os.getenv("MONITORED_COUNTRY_ID", "27"))
BATTLE_ID_TEST = 931103
DEFAULT_MONITOR_INTERVAL_SECONDS = 300
LEGACY_DEFAULT_MONITOR_INTERVAL_SECONDS = 60
MIN_MONITOR_INTERVAL_SECONDS = 30
MAX_MONITOR_INTERVAL_SECONDS = 3600
GENERAL_SCORE_ALERT_THRESHOLDS = (50, 100, 130)
BATTLE_WINNING_SCORE = 150

DIVISIONES = {
    3: "D3",
    4: "D4",
    11: "A",
}

DB_TO_APP_RULE = {
    "DEFENDER": "DEFENSOR",
    "ATTACKER": "ATACANTE",
}

APP_TO_DB_RULE = {
    "DEFENSOR": "DEFENDER",
    "ATACANTE": "ATTACKER",
}

REGLAS_ORDEN = {
    "DEFENSOR": "DEFENSOR",
    "DEFENDER": "DEFENSOR",
    "DEF": "DEFENSOR",
    "ATACANTE": "ATACANTE",
    "ATTACKER": "ATACANTE",
    "ATAQUE": "ATACANTE",
    "ATTACK": "ATACANTE",
}


# ============================================================
# PAÍSES
# ============================================================

PAISES = {
    167: "Albania", 27: "Argentina", 169: "Armenia", 50: "Australia",
    33: "Austria", 83: "Belarus", 32: "Belgium", 76: "Bolivia",
    69: "Bosnia-Herzegovina", 9: "Brazil", 42: "Bulgaria", 23: "Canada",
    64: "Chile", 14: "China", 78: "Colombia", 63: "Croatia", 171: "Cuba",
    82: "Cyprus", 34: "Czech Republic", 55: "Denmark", 165: "Egypt",
    70: "Estonia", 39: "Finland", 11: "France", 168: "Georgia",
    12: "Germany", 44: "Greece", 13: "Hungary", 48: "India",
    49: "Indonesia", 56: "Iran", 54: "Ireland", 58: "Israel", 10: "Italy",
    45: "Japan", 71: "Latvia", 72: "Lithuania", 66: "Malaysia",
    26: "Mexico", 80: "Montenegro", 31: "Netherlands", 84: "New Zealand",
    170: "Nigeria", 73: "North Korea", 79: "North Macedonia", 37: "Norway",
    57: "Pakistan", 75: "Paraguay", 77: "Peru", 67: "Philippines",
    35: "Poland", 53: "Portugal", 81: "Republic of China Taiwan",
    52: "Republic of Moldova", 1: "Romania", 41: "Russia",
    164: "Saudi Arabia", 65: "Serbia", 68: "Singapore", 36: "Slovakia",
    61: "Slovenia", 51: "South Africa", 47: "South Korea", 15: "Spain",
    38: "Sweden", 30: "Switzerland", 59: "Thailand", 43: "Turkey",
    40: "Ukraine", 166: "United Arab Emirates", 29: "United Kingdom",
    74: "Uruguay", 24: "USA", 28: "Venezuela",
}


# ============================================================
# UTILIDADES
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


def nombre_pais(country_id):
    return PAISES.get(int(country_id), f"País {country_id}")


def formatear_porcentaje(valor):
    if abs(valor - round(valor)) < 0.005:
        return str(int(round(valor)))
    return f"{valor:.1f}"


def formatear_score(valor):
    try:
        valor_float = float(valor)
        if valor_float.is_integer():
            return str(int(valor_float))
        return f"{valor_float:.1f}"
    except (TypeError, ValueError):
        return "?"


def formatear_intervalo(segundos):
    segundos = int(segundos)
    if segundos % 60 == 0:
        minutos = segundos // 60
        if minutos == 1:
            return "1 minuto"
        return f"{minutos} minutos"
    if segundos == 1:
        return "1 segundo"
    return f"{segundos} segundos"


def valor_bool(texto, default=False):
    if texto is None:
        return default
    return str(texto).strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def fila_a_monitor(row):
    return {
        "id": int(row[0]),
        "erepublik_country_id": int(row[1]),
        "name": str(row[2]),
        "telegram_command": str(row[3]),
    }


def obtener_monitor_por_id(monitor_id):
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    erepublik_country_id,
                    name,
                    telegram_command
                FROM monitored_countries
                WHERE id = %s
                  AND active = TRUE
                LIMIT 1
                """,
                (int(monitor_id),),
            )
            row = cur.fetchone()
    return fila_a_monitor(row) if row else None


def obtener_monitor_por_country_id(country_id):
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    erepublik_country_id,
                    name,
                    telegram_command
                FROM monitored_countries
                WHERE erepublik_country_id = %s
                  AND active = TRUE
                LIMIT 1
                """,
                (int(country_id),),
            )
            row = cur.fetchone()
    return fila_a_monitor(row) if row else None


def obtener_monitores_activos():
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    erepublik_country_id,
                    name,
                    telegram_command
                FROM monitored_countries
                WHERE active = TRUE
                ORDER BY name, erepublik_country_id
                """
            )
            return [fila_a_monitor(row) for row in cur.fetchall()]


def obtener_monitor_por_alias(alias):
    alias_normalizado = normalizar_texto(alias).replace(" ", "")

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    erepublik_country_id,
                    name,
                    telegram_command
                FROM monitored_countries
                WHERE active = TRUE
                """
            )
            for row in cur.fetchall():
                monitor = fila_a_monitor(row)
                if normalizar_texto(monitor["telegram_command"]).replace(" ", "") == alias_normalizado:
                    return monitor
                if normalizar_texto(monitor["name"]).replace(" ", "") == alias_normalizado:
                    return monitor

    return None


def resolver_pais_orden(texto):
    """Resuelve un rival por nombre o por ID de eRepublik."""
    texto_limpio = str(texto).strip()
    if texto_limpio.isdigit():
        country_id = int(texto_limpio)
        return country_id if country_id in PAISES else None
    return buscar_country_id(texto_limpio)


def normalizar_regla_orden(texto):
    """Acepta las formas más comunes y devuelve el nombre de la app."""
    if texto is None:
        return None
    return REGLAS_ORDEN.get(normalizar_texto(texto).upper())


def obtener_monitor_predeterminado():
    monitor = obtener_monitor_por_country_id(MONITORED_COUNTRY_ID)
    if monitor:
        return monitor

    monitores = obtener_monitores_activos()
    if monitores:
        return monitores[0]

    raise ValueError("No hay países monitoreados activos en monitored_countries")


def obtener_preferencia_chat(chat_id):
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT monitored_country_id
                FROM chat_country_preferences
                WHERE chat_id = %s
                LIMIT 1
                """,
                (int(chat_id),),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return obtener_monitor_por_id(row[0])


def guardar_preferencia_chat(chat_id, monitor_id):
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_country_preferences (
                    chat_id,
                    monitored_country_id,
                    updated_at
                )
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (chat_id)
                DO UPDATE SET
                    monitored_country_id = EXCLUDED.monitored_country_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (int(chat_id), int(monitor_id)),
            )


def borrar_preferencia_chat(chat_id):
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM chat_country_preferences
                WHERE chat_id = %s
                """,
                (int(chat_id),),
            )


def resolver_monitor_por_texto(texto):
    if texto is None:
        return None

    texto_limpio = str(texto).strip()
    if not texto_limpio:
        return None

    if texto_limpio.isdigit():
        numero = int(texto_limpio)
        monitor = obtener_monitor_por_id(numero)
        if monitor:
            return monitor
        monitor = obtener_monitor_por_country_id(numero)
        if monitor:
            return monitor

    pais_id = buscar_country_id(texto_limpio)
    if pais_id is not None:
        monitor = obtener_monitor_por_country_id(pais_id)
        if monitor:
            return monitor

    monitor = obtener_monitor_por_alias(texto_limpio)
    if monitor:
        return monitor

    return None


def resolver_monitor_contexto(update, context=None):
    if update and update.effective_chat:
        preferido = obtener_preferencia_chat(update.effective_chat.id)
        if preferido:
            return preferido

    return obtener_monitor_predeterminado()


def obtener_monitor_actual():
    return obtener_monitor_predeterminado()


# ============================================================
# POSTGRESQL
# ============================================================

def obtener_database_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("No se encontró DATABASE_URL")
    return database_url.strip()


def conectar_db():
    return psycopg.connect(
        obtener_database_url(),
        connect_timeout=10,
    )


def asegurar_esquema_monitor():
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_country_preferences (
                    chat_id BIGINT PRIMARY KEY,
                    monitored_country_id BIGINT NOT NULL
                        REFERENCES monitored_countries(id)
                        ON DELETE CASCADE,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_alert_state (
                    monitored_country_id BIGINT NOT NULL
                        REFERENCES monitored_countries(id)
                        ON DELETE CASCADE,
                    battle_id BIGINT NOT NULL,
                    status_signature TEXT NOT NULL,
                    had_problem BOOLEAN NOT NULL DEFAULT FALSE,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (monitored_country_id, battle_id)
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_monitor_alert_state_updated
                ON monitor_alert_state (updated_at)
                """
            )


def es_admin(update: Update, monitor_id=None):
    if not update.effective_user:
        return False

    monitor = (
        obtener_monitor_por_id(monitor_id)
        if monitor_id is not None
        else resolver_monitor_contexto(update)
    )
    user_id = int(update.effective_user.id)

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM country_admins
                WHERE monitored_country_id = %s
                  AND telegram_user_id = %s
                  AND active = TRUE
                LIMIT 1
                """,
                (monitor["id"], user_id),
            )
            return cur.fetchone() is not None


def obtener_admin_chat_default(monitor_id):
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT telegram_user_id
                FROM country_admins
                WHERE monitored_country_id = %s
                  AND active = TRUE
                ORDER BY id
                LIMIT 1
                """,
                (monitor_id,),
            )
            row = cur.fetchone()
    return int(row[0]) if row else None


def guardar_admin(monitor_id, telegram_user_id, telegram_username=None):
    """Activa o crea un administrador para el país indicado."""
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO country_admins (
                    monitored_country_id,
                    telegram_user_id,
                    telegram_username,
                    active
                )
                VALUES (%s, %s, %s, TRUE)
                ON CONFLICT (monitored_country_id, telegram_user_id)
                DO UPDATE SET
                    telegram_username = EXCLUDED.telegram_username,
                    active = TRUE
                """,
                (
                    int(monitor_id),
                    int(telegram_user_id),
                    telegram_username,
                ),
            )


def quitar_admin(monitor_id, telegram_user_id):
    """Desactiva un administrador sin dejar el país sin administradores."""
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM country_admins
                WHERE monitored_country_id = %s
                  AND active = TRUE
                """,
                (int(monitor_id),),
            )
            cantidad_admins = int(cur.fetchone()[0])

            if cantidad_admins <= 1:
                return False

            cur.execute(
                """
                UPDATE country_admins
                SET active = FALSE
                WHERE monitored_country_id = %s
                  AND telegram_user_id = %s
                  AND active = TRUE
                """,
                (int(monitor_id), int(telegram_user_id)),
            )
            return cur.rowcount > 0


def obtener_setting(monitor_id, key, default=None):
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT setting_value
                FROM country_settings
                WHERE monitored_country_id = %s
                  AND setting_key = %s
                LIMIT 1
                """,
                (monitor_id, key),
            )
            row = cur.fetchone()
    return str(row[0]) if row else default


def guardar_setting(monitor_id, key, value):
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO country_settings (
                    monitored_country_id,
                    setting_key,
                    setting_value,
                    updated_at
                )
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (monitored_country_id, setting_key)
                DO UPDATE SET
                    setting_value = EXCLUDED.setting_value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (monitor_id, key, str(value)),
            )


def obtener_config_monitor(monitor_id=None):
    monitor = (
        obtener_monitor_por_id(monitor_id)
        if monitor_id is not None
        else resolver_monitor_contexto(None)
    )

    if monitor is None:
        raise ValueError("No se encontró el país monitoreado")

    enabled = valor_bool(
        obtener_setting(monitor["id"], "alerts_enabled", "true"),
        default=True,
    )

    try:
        interval = int(
            obtener_setting(
                monitor["id"],
                "monitor_interval_seconds",
                str(DEFAULT_MONITOR_INTERVAL_SECONDS),
            )
        )
    except (TypeError, ValueError):
        interval = DEFAULT_MONITOR_INTERVAL_SECONDS

    interval = max(
        MIN_MONITOR_INTERVAL_SECONDS,
        min(MAX_MONITOR_INTERVAL_SECONDS, interval),
    )

    chat_raw = obtener_setting(monitor["id"], "alert_chat_id")
    if chat_raw:
        try:
            chat_id = int(chat_raw)
        except (TypeError, ValueError):
            chat_id = None
    else:
        chat_id = obtener_admin_chat_default(monitor["id"])

    return {
        "monitor": monitor,
        "enabled": enabled,
        "interval": interval,
        "chat_id": chat_id,
        "last_check": obtener_setting(monitor["id"], "last_monitor_check"),
        "last_error": obtener_setting(monitor["id"], "last_monitor_error"),
    }


def normalizar_intervalo_monitor(monitor_id):
    raw = obtener_setting(
        monitor_id,
        "monitor_interval_seconds",
        None,
    )

    if raw is None:
        guardar_setting(
            monitor_id,
            "monitor_interval_seconds",
            DEFAULT_MONITOR_INTERVAL_SECONDS,
        )
        return

    try:
        actual = int(raw)
    except (TypeError, ValueError):
        guardar_setting(
            monitor_id,
            "monitor_interval_seconds",
            DEFAULT_MONITOR_INTERVAL_SECONDS,
        )
        return

    if actual == LEGACY_DEFAULT_MONITOR_INTERVAL_SECONDS:
        guardar_setting(
            monitor_id,
            "monitor_interval_seconds",
            DEFAULT_MONITOR_INTERVAL_SECONDS,
        )


def obtener_reglas_campania(monitor_id=None):
    monitor = (
        obtener_monitor_por_id(monitor_id)
        if monitor_id is not None
        else resolver_monitor_contexto(None)
    )

    if monitor is None:
        raise ValueError("No se encontró el país monitoreado")

    reglas = {}

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT opponent_country_id, winner_side
                FROM campaign_orders
                WHERE monitored_country_id = %s
                  AND active = TRUE
                """,
                (monitor["id"],),
            )
            for opponent_country_id, winner_side in cur.fetchall():
                regla_app = DB_TO_APP_RULE.get(str(winner_side).upper())
                if regla_app:
                    reglas[int(opponent_country_id)] = regla_app

    return reglas


def guardar_orden(monitor_id, opponent_country_id, regla_app, telegram_user_id):
    monitor = obtener_monitor_por_id(monitor_id)
    if monitor is None:
        raise ValueError("No se encontró el país monitoreado")

    winner_side = APP_TO_DB_RULE[regla_app]

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO campaign_orders (
                    monitored_country_id,
                    opponent_country_id,
                    winner_side,
                    active,
                    created_by_telegram_id,
                    updated_at
                )
                VALUES (%s, %s, %s, TRUE, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (
                    monitored_country_id,
                    opponent_country_id
                )
                DO UPDATE SET
                    winner_side = EXCLUDED.winner_side,
                    active = TRUE,
                    created_by_telegram_id = EXCLUDED.created_by_telegram_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    monitor["id"],
                    int(opponent_country_id),
                    winner_side,
                    int(telegram_user_id),
                ),
            )


def desactivar_orden(monitor_id, opponent_country_id):
    monitor = obtener_monitor_por_id(monitor_id)
    if monitor is None:
        raise ValueError("No se encontró el país monitoreado")

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE campaign_orders
                SET
                    active = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE monitored_country_id = %s
                  AND opponent_country_id = %s
                  AND active = TRUE
                """,
                (monitor["id"], int(opponent_country_id)),
            )
            return cur.rowcount > 0


# ============================================================
# EREPUBLIK
# ============================================================

def obtener_cookie():
    cookie = os.getenv("EREPUBLIK_COOKIE")
    if not cookie:
        raise ValueError("No se encontró EREPUBLIK_COOKIE")
    return cookie.strip()


def headers_ajax():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{EREPUBLIK_BASE_URL}/en/military/campaigns",
        "Cookie": obtener_cookie(),
    }


def consultar_campanas():
    response = requests.get(
        f"{EREPUBLIK_BASE_URL}/en/military/campaignsJson/list",
        headers=headers_ajax(),
        timeout=20,
    )

    if response.status_code != 200:
        raise ValueError(
            f"campaignsJson/list respondió HTTP {response.status_code}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise ValueError(
            "campaignsJson/list no devolvió JSON"
        ) from exc


def obtener_batallas(data):
    resultado = {}

    def recorrer(valor):
        if isinstance(valor, dict):
            for clave, contenido in valor.items():
                if (
                    isinstance(contenido, dict)
                    and str(clave).isdigit()
                    and isinstance(contenido.get("inv"), dict)
                    and isinstance(contenido.get("def"), dict)
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
    return obtener_batallas(data).get(int(battle_id))


def obtener_divisiones(batalla):
    resultado = {}
    divisiones = batalla.get("div", {})

    if not isinstance(divisiones, dict):
        return resultado

    for zone_id, division_data in divisiones.items():
        if not isinstance(division_data, dict):
            continue

        try:
            division_id = int(division_data.get("div"))
        except (TypeError, ValueError):
            continue

        if division_id not in DIVISIONES:
            continue

        wall = division_data.get("wall", {})
        if not isinstance(wall, dict):
            continue

        country_id = wall.get("for")
        porcentaje = wall.get("dom")

        if country_id is None or porcentaje is None:
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


def porcentaje_pais(datos_division, country_id):
    if datos_division["country_id"] == country_id:
        return datos_division["percentage"]
    return 100 - datos_division["percentage"]


def buscar_batallas_pais(data, country_id):
    resultado = []

    for battle_id, batalla in obtener_batallas(data).items():
        inv = batalla.get("inv", {})
        defender = batalla.get("def", {})

        try:
            invader_id = int(inv.get("id"))
            defender_id = int(defender.get("id"))
        except (TypeError, ValueError):
            continue

        if country_id not in {invader_id, defender_id}:
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

    resultado.sort(key=lambda x: x["battle_id"], reverse=True)
    return resultado


def obtener_score_pais(item):
    batalla = item["batalla"]
    inv = batalla.get("inv", {})
    defender = batalla.get("def", {})

    puntos_invader = inv.get("points", 0)
    puntos_defender = defender.get("points", 0)

    if item["invader_id"] == item["country_id"]:
        return puntos_invader, puntos_defender

    return puntos_defender, puntos_invader


# ============================================================
# OBJETIVOS / INDICADORES
# ============================================================

def obtener_objetivo_auto(item, reglas_campania):
    regla = reglas_campania.get(item["rival_id"])
    if regla is None:
        return None

    pais_es_atacante = item["invader_id"] == item["country_id"]
    pais_es_defensor = item["defender_id"] == item["country_id"]

    if regla == "DEFENSOR":
        return "GANAR" if pais_es_defensor else "PERDER"

    if regla == "ATACANTE":
        return "GANAR" if pais_es_atacante else "PERDER"

    return None


def pais_ganaria_division(
    porcentaje_pais_actual,
    porcentaje_rival,
    pais_es_defensor,
):
    if porcentaje_pais_actual > porcentaje_rival:
        return True
    if porcentaje_pais_actual < porcentaje_rival:
        return False
    return pais_es_defensor


def indicador_division(
    porcentaje_pais_actual,
    porcentaje_rival,
    objetivo,
    pais_es_defensor,
):
    if objetivo is None:
        return ""

    pais_ganaria = pais_ganaria_division(
        porcentaje_pais_actual,
        porcentaje_rival,
        pais_es_defensor,
    )

    if objetivo == "GANAR":
        return "" if pais_ganaria else "🔴"

    if objetivo == "PERDER":
        return "🔴" if pais_ganaria else ""

    return ""


def indicador_score(puntos_pais, puntos_rival, objetivo):
    if objetivo is None:
        return ""

    puntos_pais = float(puntos_pais)
    puntos_rival = float(puntos_rival)

    if puntos_pais == puntos_rival:
        return ""

    pais_gana = puntos_pais > puntos_rival

    if objetivo == "GANAR":
        return "" if pais_gana else "🔴"

    if objetivo == "PERDER":
        return "🔴" if pais_gana else ""

    return ""


def alerta_score_general_alcanzada(
    puntos_pais,
    puntos_rival,
    objetivo,
    umbral=GENERAL_SCORE_ALERT_THRESHOLDS[0],
):
    """Indica si el lado que contradice la orden alcanzó el umbral."""
    puntos_pais = float(puntos_pais)
    puntos_rival = float(puntos_rival)
    umbral = float(umbral)

    umbral_alcanzado = obtener_umbral_score_general(
        puntos_pais,
        puntos_rival,
        objetivo,
        (umbral,),
    )
    return umbral_alcanzado is not None


def obtener_umbral_score_general(
    puntos_pais,
    puntos_rival,
    objetivo,
    umbrales=GENERAL_SCORE_ALERT_THRESHOLDS,
):
    """Devuelve el mayor escalón alcanzado por el lado equivocado."""
    puntos_pais = float(puntos_pais)
    puntos_rival = float(puntos_rival)

    if objetivo == "GANAR" and puntos_pais < puntos_rival:
        puntaje_equivocado = puntos_rival
    elif objetivo == "PERDER" and puntos_pais > puntos_rival:
        puntaje_equivocado = puntos_pais
    else:
        return None

    alcanzados = [
        int(umbral)
        for umbral in umbrales
        if puntaje_equivocado >= float(umbral)
    ]
    return max(alcanzados) if alcanzados else None


# ============================================================
# FORMATO DE BATALLAS
# ============================================================

def datos_visuales_batalla(item, reglas_campania):
    objetivo = obtener_objetivo_auto(item, reglas_campania)
    pais_es_defensor = item["defender_id"] == item["country_id"]
    puntos_pais, puntos_rival = obtener_score_pais(item)
    divisiones = obtener_divisiones(item["batalla"])

    detalle_divisiones = {}
    for division_id in (3, 4, 11):
        datos = divisiones.get(division_id)
        if datos is None:
            continue

        pct_pais = porcentaje_pais(datos, item["country_id"])
        pct_rival = 100 - pct_pais

        detalle_divisiones[division_id] = {
            "pais": pct_pais,
            "rival": pct_rival,
            "indicador": indicador_division(
                pct_pais,
                pct_rival,
                objetivo,
                pais_es_defensor,
            ),
        }

    return {
        "objetivo": objetivo,
        "puntos_pais": puntos_pais,
        "puntos_rival": puntos_rival,
        "indicador_score": indicador_score(
            puntos_pais,
            puntos_rival,
            objetivo,
        ),
        "divisiones": detalle_divisiones,
    }


def formatear_batalla_pais(item, reglas_campania):
    battle_id = item["battle_id"]
    rival = html.escape(nombre_pais(item["rival_id"]))
    icono_rol = "⚔️" if item["rol"] == "atacante" else "🛡️"

    url = f"{EREPUBLIK_BASE_URL}/en/military/battlefield/{battle_id}"
    rival_link = f'<a href="{url}">{rival}</a>'

    visual = datos_visuales_batalla(item, reglas_campania)
    objetivo = visual["objetivo"]

    etiqueta_objetivo = (
        f" | <b>[AUTO] {objetivo}</b>"
        if objetivo
        else ""
    )

    score_pais = formatear_score(visual["puntos_pais"])
    score_rival = formatear_score(visual["puntos_rival"])
    color_score = visual["indicador_score"]

    texto_score = f"T {score_pais}-{score_rival}"
    if color_score:
        texto_score = f"{color_score} {texto_score}"

    partes = []
    for division_id in (3, 4, 11):
        nombre = DIVISIONES[division_id]
        detalle = visual["divisiones"].get(division_id)

        if detalle is None:
            partes.append(f"{nombre} --")
            continue

        texto = (
            f"{nombre} "
            f"{formatear_porcentaje(detalle['pais'])}%-"
            f"{formatear_porcentaje(detalle['rival'])}%"
        )

        if detalle["indicador"]:
            texto = f"{detalle['indicador']} {texto}"

        partes.append(texto)

    return (
        f"{icono_rol} {rival_link}{etiqueta_objetivo}\n"
        f"{texto_score} | {' | '.join(partes)}"
    )


# ============================================================
# MONITOR AUTOMÁTICO
# ============================================================

def evaluar_batalla_para_alerta(item, reglas_campania):
    visual = datos_visuales_batalla(item, reglas_campania)
    objetivo = visual["objetivo"]

    if objetivo is None:
        return None

    # Las alertas se basan en el resultado general; las divisiones solo
    # detallan el problema cuando el tanteador general ya está equivocado.
    if visual["indicador_score"] != "🔴":
        return None

    problemas = []
    problemas.append("T")

    umbral_score = obtener_umbral_score_general(
        visual["puntos_pais"],
        visual["puntos_rival"],
        objetivo,
    )
    if umbral_score is not None:
        problemas.append(f"T≥{umbral_score}")

    for division_id in (3, 4, 11):
        detalle = visual["divisiones"].get(division_id)
        if detalle and detalle["indicador"] == "🔴":
            problemas.append(DIVISIONES[division_id])

    partes = [
        f"T {formatear_score(visual['puntos_pais'])}-"
        f"{formatear_score(visual['puntos_rival'])}"
    ]

    for division_id in (3, 4, 11):
        detalle = visual["divisiones"].get(division_id)
        if detalle:
            partes.append(
                f"{DIVISIONES[division_id]} "
                f"{formatear_porcentaje(detalle['pais'])}%-"
                f"{formatear_porcentaje(detalle['rival'])}%"
            )

    return {
        "battle_id": item["battle_id"],
        "rival_id": item["rival_id"],
        "objetivo": objetivo,
        "problemas": problemas,
        "signature": ",".join(problemas) if problemas else "OK",
        "criticidad": "critica" if umbral_score in {100, 130} else "normal",
        "umbral_score": umbral_score,
        "nivel_alerta": (
            "PRIMERA ALERTA"
            if umbral_score == 50
            else "ALERTA CRÍTICA"
            if umbral_score in {100, 130}
            else None
        ),
        "resumen": " | ".join(partes),
    }


def procesar_estados_alerta(monitor_id, evaluaciones):
    eventos = []

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT battle_id, status_signature, had_problem
                FROM monitor_alert_state
                WHERE monitored_country_id = %s
                """,
                (monitor_id,),
            )

            previos = {
                int(battle_id): {
                    "signature": str(signature),
                    "had_problem": bool(had_problem),
                }
                for battle_id, signature, had_problem in cur.fetchall()
            }

            for ev in evaluaciones:
                battle_id = int(ev["battle_id"])
                actual_problem = bool(ev["problemas"])
                previo = previos.get(battle_id)

                debe_notificar = False
                tipo = None

                if previo is None:
                    if actual_problem:
                        debe_notificar = True
                        tipo = (
                            "critica"
                            if ev.get("criticidad") == "critica"
                            else "alerta"
                        )
                elif previo["signature"] != ev["signature"]:
                    debe_notificar = True
                    if not actual_problem:
                        tipo = "recuperado"
                    elif ev.get("criticidad") == "critica":
                        tipo = "critica"
                    else:
                        tipo = "alerta"

                if debe_notificar:
                    eventos.append({
                        **ev,
                        "tipo": tipo,
                    })

                cur.execute(
                    """
                    INSERT INTO monitor_alert_state (
                        monitored_country_id,
                        battle_id,
                        status_signature,
                        had_problem,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (monitored_country_id, battle_id)
                    DO UPDATE SET
                        status_signature = EXCLUDED.status_signature,
                        had_problem = EXCLUDED.had_problem,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        monitor_id,
                        battle_id,
                        ev["signature"],
                        actual_problem,
                    ),
                )

            cur.execute(
                """
                DELETE FROM monitor_alert_state
                WHERE monitored_country_id = %s
                  AND updated_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
                """,
                (monitor_id,),
            )

    return eventos


def evaluar_monitor_sync(monitor_id=None):
    config = obtener_config_monitor(monitor_id)
    monitor = config["monitor"]

    if not config["enabled"]:
        return {
            "config": config,
            "events": [],
            "checked": False,
        }

    reglas = obtener_reglas_campania(monitor["id"])

    data = consultar_campanas()
    batallas = buscar_batallas_pais(
        data,
        monitor["erepublik_country_id"],
    )

    evaluaciones = []
    for item in batallas:
        if item["rival_id"] not in reglas:
            continue

        evaluacion = evaluar_batalla_para_alerta(
            item,
            reglas,
        )
        if evaluacion:
            evaluaciones.append(evaluacion)

    eventos = procesar_estados_alerta(
        monitor["id"],
        evaluaciones,
    )

    guardar_setting(
        monitor["id"],
        "last_monitor_check",
        datetime.now(timezone.utc).isoformat(),
    )
    guardar_setting(
        monitor["id"],
        "last_monitor_error",
        "",
    )

    return {
        "config": config,
        "events": eventos,
        "checked": True,
        "relevant_battles": len(evaluaciones),
    }


def formatear_evento_alerta(evento):
    rival = html.escape(nombre_pais(evento["rival_id"]))
    url = (
        f"{EREPUBLIK_BASE_URL}/en/military/battlefield/"
        f"{evento['battle_id']}"
    )

    if evento["tipo"] == "recuperado":
        titulo = f"✅ <b>RECUPERADO — {rival}</b>"
        estado = "Todo vuelve a estar alineado con la orden."
    elif evento["tipo"] == "critica":
        titulo = (
            f"⚠️ <b>{evento.get('nivel_alerta', 'ALERTA CRÍTICA')}"
            f" — {rival}</b>"
        )
        estado = (
            f"El lado incorrecto alcanzó "
            f"{evento.get('umbral_score')} puntos."
        )
    elif evento.get("nivel_alerta") == "PRIMERA ALERTA":
        titulo = f"🚨 <b>PRIMERA ALERTA — {rival}</b>"
        estado = (
            f"El lado incorrecto alcanzó "
            f"{evento.get('umbral_score')} puntos."
        )
    else:
        titulo = f"🚨 <b>ALERTA — {rival}</b>"
        estado = (
            "Fuera de objetivo: "
            + ", ".join(evento["problemas"])
        )

    return (
        f"{titulo}\n"
        f"Objetivo: <b>{evento['objetivo']}</b>\n"
        f"{estado}\n"
        f"{html.escape(evento['resumen'])}\n"
        f'<a href="{url}">Abrir batalla</a>'
    )


def formatear_evento_alerta_resumen(evento):
    rival = html.escape(nombre_pais(evento["rival_id"]))
    url = (
        f"{EREPUBLIK_BASE_URL}/en/military/battlefield/"
        f"{evento['battle_id']}"
    )
    tipo = (
        "⚠️"
        if evento["tipo"] == "critica"
        else "🚨"
        if evento["tipo"] == "alerta"
        else "✅"
    )
    problemas = ", ".join(evento["problemas"]) if evento["problemas"] else "OK"

    return (
        f"• {tipo} <a href=\"{url}\">{rival}</a> "
        f"({html.escape(evento['objetivo'])}) - "
        f"{html.escape(problemas)}"
    )


def dividir_texto_por_limite(texto, limite=3600):
    if len(texto) <= limite:
        return [texto]

    bloques = []
    actual = []
    longitud_actual = 0

    for linea in texto.splitlines():
        incremento = len(linea) + (1 if actual else 0)
        if actual and longitud_actual + incremento > limite:
            bloques.append("\n".join(actual))
            actual = [linea]
            longitud_actual = len(linea)
        else:
            actual.append(linea)
            longitud_actual += incremento

    if actual:
        bloques.append("\n".join(actual))

    return bloques


def formatear_bloques_eventos(monitor, eventos):
    if not eventos:
        return []

    bloques = []
    for tipo, titulo in (
        ("critica", "⚠️ ALERTAS CRÍTICAS"),
        ("alerta", "🚨 ALERTAS"),
        ("recuperado", "✅ RECUPERACIONES"),
    ):
        filtrados = [evento for evento in eventos if evento["tipo"] == tipo]
        if not filtrados:
            continue

        lineas = [
            f"{titulo} - {html.escape(monitor['name'])}",
            "",
        ]
        lineas.extend(
            formatear_evento_alerta_resumen(evento)
            for evento in filtrados
        )

        bloques.extend(dividir_texto_por_limite("\n".join(lineas)))

    return bloques


def parsear_timestamp_utc(valor):
    if not valor:
        return None

    try:
        fecha = datetime.fromisoformat(str(valor))
    except ValueError:
        return None

    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)

    return fecha.astimezone(timezone.utc)


def monitor_debe_evaluarse(config, ahora=None):
    if not config["enabled"]:
        return False

    ultimo_chequeo = parsear_timestamp_utc(config["last_check"])
    if ultimo_chequeo is None:
        return True

    ahora = ahora or datetime.now(timezone.utc)
    transcurrido = (ahora - ultimo_chequeo).total_seconds()
    return transcurrido >= config["interval"]


async def monitor_loop(application: Application):
    await asyncio.sleep(5)

    while True:
        intervalo = DEFAULT_MONITOR_INTERVAL_SECONDS

        try:
            monitores = await asyncio.to_thread(
                obtener_monitores_activos
            )

            if not monitores:
                await asyncio.sleep(intervalo)
                continue

            configs = []
            for monitor in monitores:
                configs.append(
                    await asyncio.to_thread(
                        obtener_config_monitor,
                        monitor["id"],
                    )
                )

            intervalo = min(
                (
                    config["interval"]
                    for config in configs
                    if config["enabled"]
                ),
                default=DEFAULT_MONITOR_INTERVAL_SECONDS,
            )

            ahora = datetime.now(timezone.utc)

            for config in configs:
                if not monitor_debe_evaluarse(config, ahora):
                    continue

                monitor = config["monitor"]

                try:
                    resultado = await asyncio.to_thread(
                        evaluar_monitor_sync,
                        monitor["id"],
                    )

                    chat_id = resultado["config"]["chat_id"]
                    if chat_id:
                        bloques = formatear_bloques_eventos(
                            monitor,
                            resultado["events"],
                        )

                        for bloque in bloques:
                            try:
                                await application.bot.send_message(
                                    chat_id=chat_id,
                                    text=bloque,
                                    parse_mode="HTML",
                                    disable_web_page_preview=True,
                                )
                            except Exception as send_error:
                                print(
                                    "Error enviando alerta:",
                                    type(send_error).__name__,
                                    send_error,
                                )

                except Exception as exc:
                    print(
                        "Error evaluando monitor:",
                        monitor["name"],
                        type(exc).__name__,
                        exc,
                    )
                    try:
                        await asyncio.to_thread(
                            guardar_setting,
                            monitor["id"],
                            "last_monitor_error",
                            f"{type(exc).__name__}: {exc}",
                        )
                    except Exception:
                        pass

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            print(
                "Error en monitor automático:",
                type(exc).__name__,
                exc,
            )
            try:
                monitor = await asyncio.to_thread(
                    obtener_monitor_actual
                )
                await asyncio.to_thread(
                    guardar_setting,
                    monitor["id"],
                    "last_monitor_error",
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                pass

        await asyncio.sleep(intervalo)


async def post_init(application: Application):
    await asyncio.to_thread(asegurar_esquema_monitor)
    for monitor in await asyncio.to_thread(obtener_monitores_activos):
        await asyncio.to_thread(
            normalizar_intervalo_monitor,
            monitor["id"],
        )
    application.bot_data["monitor_task"] = asyncio.create_task(
        monitor_loop(application)
    )


async def post_shutdown(application: Application):
    task = application.bot_data.get("monitor_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# ============================================================
# COMANDOS
# ============================================================

AYUDA_USUARIOS = (
    "🌎 <b>AYUDA — eRepublik Battle Tracker</b>\n\n"
    "El bot muestra batallas activas y aplica las órdenes guardadas "
    "por los administradores. Las órdenes aparecen como [AUTO] y "
    "se conservan entre reinicios.\n\n"
    "<b>Comandos para usuarios</b>\n"
    "/paises — Lista los países disponibles.\n"
    "/pais — Muestra el país seleccionado.\n"
    "/pais &lt;país&gt; — Cambia el país del chat.\n"
    "/pais reset — Vuelve al país predeterminado.\n"
    "/ordenes — Muestra las órdenes activas.\n"
    "/batallas — Muestra las batallas y los objetivos [AUTO].\n"
    "/monitor — Muestra el estado de las alertas automáticas.\n"
    "/estado — Muestra el estado general del bot.\n"
    "/id — Muestra el ID de Telegram del usuario y del chat.\n"
    "/test — Prueba la conexión con eRepublik.\n\n"
    "<b>Cómo leer [AUTO]</b>\n"
    "[AUTO] GANAR o [AUTO] PERDER indica el objetivo calculado "
    "para Argentina. Solo aparece 🔴 cuando el tanteador general "
    "está fuera del objetivo.\n\n"
    "Las alertas automáticas solo se envían para batallas con una "
    "orden activa."
)


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        AYUDA_USUARIOS,
        parse_mode="HTML",
    )


async def autorizar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)

        if not es_admin(update, monitor["id"]):
            await update.message.reply_text(
                "⛔ Este comando está reservado a administradores."
            )
            return

        telegram_user_id = None
        telegram_username = None

        if context.args and context.args[0].isdigit():
            telegram_user_id = int(context.args[0])
            telegram_username = context.args[1] if len(context.args) > 1 else None
        elif (
            update.message
            and update.message.reply_to_message
            and update.message.reply_to_message.from_user
        ):
            usuario = update.message.reply_to_message.from_user
            telegram_user_id = int(usuario.id)
            telegram_username = (
                f"@{usuario.username}"
                if usuario.username
                else None
            )

        if telegram_user_id is None:
            await update.message.reply_text(
                "Uso:\n"
                "/autorizar <User ID> [@usuario]\n"
                "o respondé al mensaje de la persona con /autorizar."
            )
            return

        guardar_admin(
            monitor["id"],
            telegram_user_id,
            telegram_username,
        )

        await update.message.reply_text(
            "✅ Usuario autorizado para administrar órdenes\n\n"
            f"País: {monitor['name']}\n"
            f"User ID: {telegram_user_id}"
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /autorizar\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def desautorizar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)

        if not es_admin(update, monitor["id"]):
            await update.message.reply_text(
                "⛔ Este comando está reservado a administradores."
            )
            return

        telegram_user_id = None

        if context.args and context.args[0].isdigit():
            telegram_user_id = int(context.args[0])
        elif (
            update.message
            and update.message.reply_to_message
            and update.message.reply_to_message.from_user
        ):
            telegram_user_id = int(
                update.message.reply_to_message.from_user.id
            )

        if telegram_user_id is None:
            await update.message.reply_text(
                "Uso:\n"
                "/desautorizar <User ID>\n"
                "o respondé al mensaje de la persona con /desautorizar."
            )
            return
        quitado = quitar_admin(monitor["id"], telegram_user_id)

        if not quitado:
            await update.message.reply_text(
                "⚠️ No se quitó el permiso. Puede que el usuario no "
                "sea administrador o que sea el último administrador activo."
            )
            return

        await update.message.reply_text(
            "✅ Permiso de administrador quitado\n\n"
            f"País: {monitor['name']}\n"
            f"User ID: {telegram_user_id}"
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /desautorizar\n\n"
            f"{type(exc).__name__}: {exc}"
        )

async def mostrar_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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


async def orden(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)

        if not es_admin(update, monitor["id"]):
            await update.message.reply_text(
                "⛔ Este comando está reservado a administradores."
            )
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "Uso:\n"
                "/orden Chile defensor\n"
                "/orden Chile atacante"
            )
            return

        regla = normalizar_regla_orden(context.args[-1])

        if regla is None:
            await update.message.reply_text(
                "La orden debe terminar en:\n"
                "defensor o atacante\n\n"
                "También podés usar: def, defender, ataque o attacker."
            )
            return

        nombre = " ".join(context.args[:-1])
        country_id = resolver_pais_orden(nombre)

        if country_id is None:
            await update.message.reply_text(
                f"❌ No encontré el país: {nombre}"
            )
            return

        if country_id == monitor["erepublik_country_id"]:
            await update.message.reply_text(
                "❌ No corresponde cargar una regla contra "
                "el propio país monitoreado."
            )
            return

        guardar_orden(
            monitor["id"],
            country_id,
            regla,
            update.effective_user.id,
        )

        await update.message.reply_text(
            "✅ Orden persistente actualizada\n\n"
            f"{nombre_pais(country_id)} → gana {regla}"
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /orden\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def sinorden(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)

        if not es_admin(update, monitor["id"]):
            await update.message.reply_text(
                "⛔ Este comando está reservado a administradores."
            )
            return

        if not context.args:
            await update.message.reply_text(
                "Uso:\n/sinorden Chile"
            )
            return

        nombre = " ".join(context.args)
        country_id = resolver_pais_orden(nombre)

        if country_id is None:
            await update.message.reply_text(
                f"❌ No encontré el país: {nombre}"
            )
            return

        if not desactivar_orden(monitor["id"], country_id):
            await update.message.reply_text(
                f"{nombre_pais(country_id)} "
                "no tiene una orden activa."
            )
            return

        await update.message.reply_text(
            "✅ Orden desactivada\n\n"
            f"{nombre_pais(country_id)}"
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /sinorden\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def ordenes(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)
        reglas = obtener_reglas_campania(monitor["id"])

        if not reglas:
            await update.message.reply_text(
                "📋 No hay órdenes activas."
            )
            return

        lineas = [
            "📋 ÓRDENES ACTIVAS",
            f"País: {monitor['name']}",
            "",
        ]

        for country_id, regla in sorted(
            reglas.items(),
            key=lambda x: nombre_pais(x[0]),
        ):
            lineas.append(
                f"• {nombre_pais(country_id)} → {regla}"
            )

        lineas.extend([
            "",
            "💾 Guardadas en PostgreSQL.",
        ])

        await update.message.reply_text(
            "\n".join(lineas)
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /ordenes\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    monitor = resolver_monitor_contexto(update)

    await update.message.reply_text(
        "🌎 eRepublik Country Monitor\n\n"
        f"País actual: {monitor['name']}\n"
        f"Alias: /{monitor['telegram_command']}\n\n"
        "/batallas - Batallas activas\n"
        "/pais <país> - Cambia el país de este chat\n"
        "/paises - Lista países activos\n"
        "/ordenes - Órdenes actuales\n"
        "/monitor - Estado del monitor automático\n"
        "/alertas on|off - Activar/desactivar alertas\n"
        "/intervalo N - Segundos entre revisiones\n"
        "/id - Ver IDs de Telegram\n"
        "/estado - Estado del bot"
    )


async def estado(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)
        reglas = obtener_reglas_campania(monitor["id"])
        config = obtener_config_monitor(monitor["id"])

        await update.message.reply_text(
            "✅ Bot funcionando\n\n"
            f"País monitoreado: "
            f"{monitor['name']} "
            f"({monitor['erepublik_country_id']})\n"
            f"Alias: /{monitor['telegram_command']}\n"
            f"Órdenes activas: {len(reglas)}\n"
            "Persistencia: PostgreSQL ✅\n"
            f"Monitor automático: "
            f"{'✅' if config['enabled'] else '⏸️'}\n"
            f"Intervalo: {formatear_intervalo(config['interval'])}\n\n"
            "Empate de división → defensor\n"
            "Empate de score total → neutral"
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /estado\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def mostrar_batallas(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    monitor_id=None,
):
    try:
        monitor = (
            obtener_monitor_por_id(monitor_id)
            if monitor_id is not None
            else resolver_monitor_contexto(update)
        )
        reglas = obtener_reglas_campania(monitor["id"])
        data = consultar_campanas()
        batallas = buscar_batallas_pais(
            data,
            monitor["erepublik_country_id"],
        )

        if not batallas:
            await update.message.reply_text(
                f"{monitor['name']} "
                "no tiene batallas activas."
            )
            return

        bloques = [
            formatear_batalla_pais(item, reglas)
            for item in batallas
        ]

        mensaje = (
            f"🌎 <b>BATALLAS DE "
            f"{html.escape(monitor['name'].upper())}</b>\n"
            f"Activas: {len(batallas)}\n\n"
            + "\n\n".join(bloques)
            + "\n\n"
            + "ℹ️ <b>[AUTO]</b>: objetivo deducido de la "
              "regla cargada; puede estar equivocado si "
              "cambió el acuerdo."
        )

        await update.message.reply_text(
            mensaje,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /batallas\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        data = consultar_campanas()
        batalla = buscar_batalla(
            data,
            BATTLE_ID_TEST,
        )

        if batalla is None:
            raise ValueError(
                f"No encontré la batalla {BATTLE_ID_TEST}."
            )

        invader_id = int(
            batalla.get("inv", {})["id"]
        )
        defender_id = int(
            batalla.get("def", {})["id"]
        )

        await update.message.reply_text(
            "🧪 BATALLA DE CONTROL\n\n"
            f"Battle ID: {BATTLE_ID_TEST}\n"
            f"🛡️ {nombre_pais(defender_id)}\n"
            f"⚔️ {nombre_pais(invader_id)}"
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /test\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def monitor_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)
        config = obtener_config_monitor(monitor["id"])
        last_check = config["last_check"] or "todavía sin revisión"
        last_error = config["last_error"] or "ninguno"

        await update.message.reply_text(
            "📡 MONITOR AUTOMÁTICO\n\n"
            f"País: {monitor['name']}\n"
            f"Estado: {'ACTIVO ✅' if config['enabled'] else 'PAUSADO ⏸️'}\n"
            f"Intervalo: {formatear_intervalo(config['interval'])}\n"
            f"Chat de alertas: {config['chat_id'] or 'sin configurar'}\n"
            f"Última revisión: {last_check}\n"
            f"Último error: {last_error}\n\n"
            "Solo alerta sobre campañas con una orden activa."
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /monitor\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def alertas(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)

        if not es_admin(update, monitor["id"]):
            await update.message.reply_text(
                "⛔ Este comando está reservado a administradores."
            )
            return

        if not context.args or context.args[0].lower() not in {"on", "off"}:
            await update.message.reply_text(
                "Uso:\n/alertas on\n/alertas off"
            )
            return

        activar = context.args[0].lower() == "on"

        guardar_setting(
            monitor["id"],
            "alerts_enabled",
            "true" if activar else "false",
        )

        if activar and update.effective_chat:
            guardar_setting(
                monitor["id"],
                "alert_chat_id",
                update.effective_chat.id,
            )

        await update.message.reply_text(
            "✅ Alertas automáticas activadas."
            if activar
            else "⏸️ Alertas automáticas pausadas."
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /alertas\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def intervalo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)

        if not es_admin(update, monitor["id"]):
            await update.message.reply_text(
                "⛔ Este comando está reservado a administradores."
            )
            return

        if not context.args:
            await update.message.reply_text(
                f"Uso: /intervalo N\n"
                f"Mínimo {formatear_intervalo(MIN_MONITOR_INTERVAL_SECONDS)}, "
                f"máximo {formatear_intervalo(MAX_MONITOR_INTERVAL_SECONDS)}."
            )
            return

        try:
            segundos = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ El intervalo debe ser un número entero."
            )
            return

        if not (
            MIN_MONITOR_INTERVAL_SECONDS
            <= segundos
            <= MAX_MONITOR_INTERVAL_SECONDS
        ):
            await update.message.reply_text(
                f"❌ Usá entre "
                f"{formatear_intervalo(MIN_MONITOR_INTERVAL_SECONDS)} y "
                f"{formatear_intervalo(MAX_MONITOR_INTERVAL_SECONDS)}."
            )
            return

        guardar_setting(
            monitor["id"],
            "monitor_interval_seconds",
            segundos,
        )

        await update.message.reply_text(
            f"✅ Intervalo actualizado: {formatear_intervalo(segundos)}."
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /intervalo\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def chequear(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        monitor = resolver_monitor_contexto(update)

        if not es_admin(update, monitor["id"]):
            await update.message.reply_text(
                "⛔ Este comando está reservado a administradores."
            )
            return

        resultado = await asyncio.to_thread(
            evaluar_monitor_sync,
            monitor["id"],
        )

        if not resultado["checked"]:
            await update.message.reply_text(
                "⏸️ El monitor está pausado."
            )
            return

        await update.message.reply_text(
            "✅ Revisión manual completada\n\n"
            f"País: {monitor['name']}\n"
            f"Batallas con orden: "
            f"{resultado.get('relevant_battles', 0)}\n"
            f"Cambios detectados: "
            f"{len(resultado['events'])}"
        )

        for bloque in formatear_bloques_eventos(
            monitor,
            resultado["events"],
        ):
            await update.message.reply_text(
                bloque,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /chequear\n\n"
            f"{type(exc).__name__}: {exc}"
        )


def formatear_lista_paises_activos():
    monitores = obtener_monitores_activos()
    if not monitores:
        return "📭 No hay países activos configurados."

    lineas = [
        "🌎 PAÍSES ACTIVOS",
        "",
        "Usá /pais <país> para fijar el contexto de este chat.",
        "",
    ]

    for monitor in monitores:
        lineas.append(
            f"• {monitor['name']} "
            f"({monitor['erepublik_country_id']}) "
            f"→ /{monitor['telegram_command']}"
        )

    return "\n".join(lineas)


async def pais(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        if not context.args:
            monitor = resolver_monitor_contexto(update)
            await update.message.reply_text(
                "📌 País actual del chat\n\n"
                f"{monitor['name']} "
                f"({monitor['erepublik_country_id']})\n"
                f"Alias: /{monitor['telegram_command']}\n\n"
                "Usá /pais <país> para cambiarlo o /pais reset "
                "para volver al país por defecto."
            )
            return

        buscado = " ".join(context.args)

        if buscado.strip().lower() in {"reset", "default", "base", "limpiar"}:
            if update.effective_chat:
                await asyncio.to_thread(
                    borrar_preferencia_chat,
                    update.effective_chat.id,
                )
            await update.message.reply_text(
                "✅ Se volvió al país por defecto para este chat."
            )
            return

        monitor = resolver_monitor_por_texto(buscado)

        if monitor is None:
            await update.message.reply_text(
                f"❌ No encontré un país activo para: {buscado}"
            )
            return

        if update.effective_chat:
            await asyncio.to_thread(
                guardar_preferencia_chat,
                update.effective_chat.id,
                monitor["id"],
            )

        await update.message.reply_text(
            "✅ País seleccionado para este chat\n\n"
            f"{monitor['name']} "
            f"({monitor['erepublik_country_id']})\n"
            f"Alias: /{monitor['telegram_command']}"
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /pais\n\n"
            f"{type(exc).__name__}: {exc}"
        )


async def paises(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        if context.args:
            buscado = " ".join(context.args)
            monitor = resolver_monitor_por_texto(buscado)

            if monitor is None:
                await update.message.reply_text(
                    f"❌ No encontré un país activo para: {buscado}"
                )
                return

            if update.effective_chat:
                await asyncio.to_thread(
                    guardar_preferencia_chat,
                    update.effective_chat.id,
                    monitor["id"],
                )

            await update.message.reply_text(
                "✅ País seleccionado para este chat\n\n"
                f"{monitor['name']} "
                f"({monitor['erepublik_country_id']})\n"
                f"Alias: /{monitor['telegram_command']}"
            )
            return

        await update.message.reply_text(
            formatear_lista_paises_activos()
        )
    except Exception as exc:
        await update.message.reply_text(
            "❌ Error en /paises\n\n"
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================
# MAIN
# ============================================================

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("No se encontró TELEGRAM_TOKEN")

    monitor = obtener_monitor_actual()
    asegurar_esquema_monitor()

    app = (
        Application
        .builder()
        .token(token.strip())
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    handlers = [
        ("help", help_command),
        ("autorizar", autorizar),
        ("desautorizar", desautorizar),
        ("start", start),
        ("estado", estado),
        ("id", mostrar_id),
        ("pais", pais),
        ("paises", paises),
        ("orden", orden),
        ("sinorden", sinorden),
        ("ordenes", ordenes),
        ("test", test),
        ("batallas", mostrar_batallas),
        ("monitor", monitor_status),
        ("alertas", alertas),
        ("intervalo", intervalo),
        ("chequear", chequear),
    ]

    for command, callback in handlers:
        app.add_handler(
            CommandHandler(command, callback)
        )

    registered = {command for command, _ in handlers}
    for country in obtener_monitores_activos():
        alias = country["telegram_command"].strip().lower()
        if (
            alias
            and alias not in registered
            and re.fullmatch(r"[a-z0-9_]{1,32}", alias)
        ):
            app.add_handler(
                CommandHandler(
                    alias,
                    partial(
                        mostrar_batallas,
                        monitor_id=country["id"],
                    ),
                )
            )
            registered.add(alias)

    print(
        "eRepublik Country Monitor iniciado "
        f"para {monitor['name']} "
        f"({monitor['erepublik_country_id']})"
    )

    app.run_polling()


if __name__ == "__main__":
    main()
