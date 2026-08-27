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


class PaisHandlersTest(unittest.IsolatedAsyncioTestCase):
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
