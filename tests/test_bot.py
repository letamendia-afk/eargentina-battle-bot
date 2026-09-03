import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

telegram = types.ModuleType("telegram")
telegram.Update = type("Update", (), {})

telegram_ext = types.ModuleType("telegram.ext")
telegram_ext.Application = type("Application", (), {})
telegram_ext.CommandHandler = type("CommandHandler", (), {})
telegram_ext.ContextTypes = types.SimpleNamespace(DEFAULT_TYPE=object())
telegram.ext = telegram_ext

psycopg = types.ModuleType("psycopg")
psycopg.connect = lambda *args, **kwargs: None

requests = types.ModuleType("requests")
requests.get = lambda *args, **kwargs: None

sys.modules.setdefault("telegram", telegram)
sys.modules.setdefault("telegram.ext", telegram_ext)
sys.modules.setdefault("psycopg", psycopg)
sys.modules.setdefault("requests", requests)

import bot


class BotHelpersTest(unittest.TestCase):
    def test_dividir_texto_por_limite_respects_limit(self):
        texto = "\n".join(["a" * 20, "b" * 20, "c" * 20, "d" * 20])
        bloques = bot.dividir_texto_por_limite(texto, limite=45)

        self.assertGreater(len(bloques), 1)
        self.assertEqual("\n".join(bloques), texto)
        self.assertTrue(all(len(bloque) <= 45 for bloque in bloques))

    def test_monitor_debe_evaluarse_respects_timestamps(self):
        ahora = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(
            bot.monitor_debe_evaluarse(
                {"enabled": True, "last_check": None, "interval": 60},
                ahora,
            )
        )
        self.assertFalse(
            bot.monitor_debe_evaluarse(
                {
                    "enabled": True,
                    "last_check": "2026-08-27T11:59:30+00:00",
                    "interval": 60,
                },
                ahora,
            )
        )
        self.assertTrue(
            bot.monitor_debe_evaluarse(
                {
                    "enabled": True,
                    "last_check": "2026-08-27T11:58:30+00:00",
                    "interval": 60,
                },
                ahora,
            )
        )
        self.assertFalse(
            bot.monitor_debe_evaluarse(
                {"enabled": False, "last_check": None, "interval": 60},
                ahora,
            )
        )

    def test_formatear_intervalo_prefers_minutes_when_possible(self):
        self.assertEqual(bot.formatear_intervalo(60), "1 minuto")
        self.assertEqual(bot.formatear_intervalo(300), "5 minutos")
        self.assertEqual(bot.formatear_intervalo(90), "90 segundos")

    def test_resolver_monitor_por_texto_matches_known_forms(self):
        fake_monitor = {
            "id": 7,
            "erepublik_country_id": 27,
            "name": "Argentina",
            "telegram_command": "argentina",
        }
        with patch.object(
            bot,
            "obtener_monitor_por_id",
            side_effect=lambda value: fake_monitor if int(value) == 7 else None,
        ), patch.object(
            bot,
            "obtener_monitor_por_country_id",
            side_effect=lambda value: fake_monitor if int(value) == 27 else None,
        ), patch.object(
            bot,
            "obtener_monitor_por_alias",
            side_effect=lambda value: fake_monitor if str(value).lower() == "argentina" else None,
        ), patch.object(
            bot,
            "buscar_country_id",
            return_value=27,
        ):
            self.assertEqual(bot.resolver_monitor_por_texto("7"), fake_monitor)
            self.assertEqual(bot.resolver_monitor_por_texto("27"), fake_monitor)
            self.assertEqual(bot.resolver_monitor_por_texto("Argentina"), fake_monitor)
            self.assertEqual(bot.resolver_monitor_por_texto("argentina"), fake_monitor)

    def test_resolver_pais_orden_accepts_name_and_known_id(self):
        self.assertEqual(bot.resolver_pais_orden("Chile"), 64)
        self.assertEqual(bot.resolver_pais_orden("64"), 64)
        self.assertIsNone(bot.resolver_pais_orden("999999"))

    def test_normalizar_regla_orden_accepts_common_variants(self):
        self.assertEqual(bot.normalizar_regla_orden("defensor"), "DEFENSOR")
        self.assertEqual(bot.normalizar_regla_orden("def"), "DEFENSOR")
        self.assertEqual(bot.normalizar_regla_orden("attacker"), "ATACANTE")
        self.assertEqual(bot.normalizar_regla_orden("ataque"), "ATACANTE")
        self.assertIsNone(bot.normalizar_regla_orden("neutral"))

    def test_indicadores_solo_muestran_rojo_si_el_resultado_es_incorrecto(self):
        self.assertEqual(bot.indicador_score(60, 40, "GANAR"), "")
        self.assertEqual(bot.indicador_score(40, 60, "GANAR"), "⚠️")
        self.assertEqual(bot.indicador_score(40, 60, "PERDER"), "")
        self.assertEqual(bot.indicador_score(60, 40, "PERDER"), "⚠️")
        self.assertEqual(bot.indicador_division(60, 40, "GANAR", True), "")
        self.assertEqual(bot.indicador_division(40, 60, "GANAR", True), "🔴")

    def test_alerta_de_score_general_usa_el_puntaje_del_lado_incorrecto(self):
        self.assertTrue(bot.alerta_score_general_alcanzada(40, 50, "GANAR"))
        self.assertFalse(bot.alerta_score_general_alcanzada(40, 49, "GANAR"))
        self.assertTrue(bot.alerta_score_general_alcanzada(50, 40, "PERDER"))
        self.assertFalse(bot.alerta_score_general_alcanzada(40, 50, "PERDER"))
        self.assertFalse(bot.alerta_score_general_alcanzada(60, 40, "GANAR"))

    def test_umbral_score_general_devuelve_el_mayor_escalon_alcanzado(self):
        self.assertEqual(bot.obtener_umbral_score_general(40, 50, "GANAR"), 50)
        self.assertEqual(bot.obtener_umbral_score_general(40, 110, "GANAR"), 100)
        self.assertEqual(bot.obtener_umbral_score_general(40, 135, "GANAR"), 130)
        self.assertEqual(bot.obtener_umbral_score_general(50, 40, "PERDER"), 50)
        self.assertIsNone(bot.obtener_umbral_score_general(60, 40, "GANAR"))

    def test_monitor_no_alerta_divisiones_si_el_tanteador_general_es_correcto(self):
        item = {"battle_id": 1, "rival_id": 64}
        visual = {
            "objetivo": "GANAR",
            "puntos_pais": 70,
            "puntos_rival": 30,
            "indicador_score": "",
            "divisiones": {
                3: {
                    "pais": 40,
                    "rival": 60,
                    "indicador": "🔴",
                }
            },
        }
        with patch.object(bot, "datos_visuales_batalla", return_value=visual):
            evaluacion = bot.evaluar_batalla_para_alerta(item, {})

        self.assertEqual(evaluacion["signature"], "OK")
        self.assertEqual(evaluacion["problemas"], [])

    def test_formatear_bloques_eventos_groups_by_type(self):
        monitor = {"name": "Argentina"}
        eventos = [
            {
                "tipo": "alerta",
                "rival_id": 64,
                "battle_id": 1,
                "objetivo": "GANAR",
                "problemas": ["T"],
                "resumen": "T 1-0",
            },
            {
                "tipo": "recuperado",
                "rival_id": 65,
                "battle_id": 2,
                "objetivo": "PERDER",
                "problemas": [],
                "resumen": "T 0-1",
            },
        ]

        bloques = bot.formatear_bloques_eventos(monitor, eventos)

        self.assertEqual(len(bloques), 2)
        self.assertIn("🚨 ALERTAS - Argentina", bloques[0])
        self.assertIn("✅ RECUPERACIONES - Argentina", bloques[1])

    def test_procesar_estados_alerta_no_repite_misma_senal(self):
        class FakeCursor:
            def __init__(self):
                self.executed = []

            def execute(self, query, params=None):
                self.executed.append((query.strip(), params))

            def fetchall(self):
                return [(101, "T", True)]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeConn:
            def __init__(self):
                self.cursor_obj = FakeCursor()

            def cursor(self):
                return self.cursor_obj

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_conn = FakeConn()

        with patch.object(bot, "conectar_db", return_value=fake_conn):
            eventos = bot.procesar_estados_alerta(
                1,
                [
                    {
                        "battle_id": 101,
                        "rival_id": 64,
                        "objetivo": "GANAR",
                        "problemas": ["T"],
                        "signature": "T",
                        "umbral_score": None,
                        "resumen": "T 1-0",
                    }
                ],
            )

        self.assertEqual(eventos, [])
        self.assertGreaterEqual(len(fake_conn.cursor_obj.executed), 2)

    def test_procesar_estados_alerta_notifica_recuperacion(self):
        class FakeCursor:
            def __init__(self):
                self.executed = []

            def execute(self, query, params=None):
                self.executed.append((query.strip(), params))

            def fetchall(self):
                return [(202, "T", True)]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeConn:
            def __init__(self):
                self.cursor_obj = FakeCursor()

            def cursor(self):
                return self.cursor_obj

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_conn = FakeConn()

        with patch.object(bot, "conectar_db", return_value=fake_conn):
            eventos = bot.procesar_estados_alerta(
                1,
                [
                    {
                        "battle_id": 202,
                        "rival_id": 64,
                        "objetivo": "GANAR",
                        "problemas": [],
                        "signature": "OK",
                        "umbral_score": None,
                        "resumen": "T 1-0",
                    }
                ],
            )

        self.assertEqual(eventos, [])


class PaisHandlersTest(unittest.IsolatedAsyncioTestCase):
    async def test_help_muestra_solo_comandos_publicos(self):
        update = types.SimpleNamespace(
            message=types.SimpleNamespace(reply_text=AsyncMock()),
        )

        await bot.help_command(update, types.SimpleNamespace())

        mensaje = update.message.reply_text.await_args.args[0]
        self.assertIn("/ordenes", mensaje)
        self.assertIn("/batallas", mensaje)
        self.assertIn("50 puntos", mensaje)
        self.assertIn("100 y 130 puntos", mensaje)
        self.assertIn("chequeo automático", mensaje)
        self.assertIn("⚠️ junto a T", mensaje)
        self.assertIn("🔴 junto a D3", mensaje)
        self.assertNotIn("/orden ", mensaje)
        self.assertNotIn("/sinorden", mensaje)
        self.assertNotIn("/alertas", mensaje)

    async def test_autorizar_guarda_usuario_para_el_pais_actual(self):
        update = types.SimpleNamespace(
            effective_user=types.SimpleNamespace(id=10),
            effective_chat=types.SimpleNamespace(id=123),
            message=types.SimpleNamespace(reply_text=AsyncMock()),
        )
        context = types.SimpleNamespace(args=["456", "@nuevo_usuario"])
        monitor = {"id": 7, "name": "Argentina"}

        with patch.object(bot, "resolver_monitor_contexto", return_value=monitor), patch.object(
            bot, "es_admin", return_value=True
        ), patch.object(bot, "guardar_admin") as guardar:
            await bot.autorizar(update, context)

        guardar.assert_called_once_with(7, 456, "@nuevo_usuario")
        update.message.reply_text.assert_awaited_once()

    async def test_autorizar_puede_usar_el_mensaje_al_que_se_respondio(self):
        update = types.SimpleNamespace(
            effective_user=types.SimpleNamespace(id=10),
            effective_chat=types.SimpleNamespace(id=123),
            message=types.SimpleNamespace(
                reply_to_message=types.SimpleNamespace(
                    from_user=types.SimpleNamespace(id=456, username="nuevo")
                ),
                reply_text=AsyncMock(),
            ),
        )
        context = types.SimpleNamespace(args=[])
        monitor = {"id": 7, "name": "Argentina"}

        with patch.object(bot, "resolver_monitor_contexto", return_value=monitor), patch.object(
            bot, "es_admin", return_value=True
        ), patch.object(bot, "guardar_admin") as guardar:
            await bot.autorizar(update, context)

        guardar.assert_called_once_with(7, 456, "@nuevo")

    async def test_paises_with_argument_sets_chat_country(self):
        fake_monitor = {
            "id": 7,
            "erepublik_country_id": 27,
            "name": "Argentina",
            "telegram_command": "argentina",
        }

        update = types.SimpleNamespace(
            effective_chat=types.SimpleNamespace(id=123),
            message=types.SimpleNamespace(reply_text=AsyncMock()),
        )
        context = types.SimpleNamespace(args=["Argentina"])

        with patch.object(bot, "resolver_monitor_por_texto", return_value=fake_monitor), patch.object(
            bot,
            "guardar_preferencia_chat",
            return_value=None,
        ) as guardar_preferencia_chat:
            await bot.paises(update, context)

        guardar_preferencia_chat.assert_called_once_with(123, 7)
        update.message.reply_text.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
