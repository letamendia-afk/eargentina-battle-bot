# eRepublik Country Monitor

Bot de Telegram para monitoreo de campañas de eRepublik.

El proyecto nació para Argentina, pero la lógica y la base están preparadas para configurar otros países sin duplicar el bot.

## Funciones actuales

- Lista batallas activas del país monitoreado.
- Muestra tanteador total y situación de D3, D4 y Air.
- Permite cargar órdenes por rival: debe ganar el defensor o el atacante.
- Deduce automáticamente si el país monitoreado debe GANAR o PERDER.
- Guarda órdenes y administradores en PostgreSQL.
- Monitor automático de campañas con órdenes activas.
- Alertas solo cuando cambia la situación, evitando mensajes repetidos cada ciclo.
- Estado de alertas persistente entre reinicios.

## Comandos

- `/batallas` — lista batallas activas.
- `/pais <país>` — fija el país monitoreado para este chat. `/pais reset` vuelve al país por defecto.
- `/paises` — lista los países activos configurados en la base.
- `/<alias_pais>` — alias configurado en `monitored_countries.telegram_command`.
- `/orden <pais> defensor|atacante` — crea o actualiza una orden. Solo administradores.
- `/sinorden <pais>` — desactiva una orden. Solo administradores.
- `/ordenes` — lista órdenes activas.
- `/monitor` — muestra estado del monitor automático.
- `/alertas on|off` — activa o pausa alertas y, al activar, usa el chat actual como destino. Solo administradores.
- `/intervalo <segundos>` — cambia el intervalo de revisión (30 a 3600 s). Solo administradores.
- `/chequear` — fuerza una revisión manual. Solo administradores.
- `/estado` — estado general del bot.
- `/id` — muestra User ID y Chat ID de Telegram.
- `/test` — batalla de control histórica si sigue disponible en campañas activas.

## Variables de entorno / GitHub Secrets

- `TELEGRAM_TOKEN` — token del bot de Telegram.
- `EREPUBLIK_COOKIE` — cookie de sesión usada para consultar eRepublik.
- `DATABASE_URL` — URI PostgreSQL estándar.
- `MONITORED_COUNTRY_ID` — opcional; por defecto `27` (Argentina).

No guardar valores reales de estos Secrets en el repositorio.

## Base de datos

El esquema está en [`schema.sql`](schema.sql).

Está escrito con PostgreSQL estándar para reducir dependencia de Supabase. La misma estructura puede migrarse a PostgreSQL en OCI u otro proveedor cambiando principalmente `DATABASE_URL`.

Tablas principales:

- `monitored_countries`
- `country_admins`
- `campaign_orders`
- `country_settings`
- `chat_country_preferences`
- `monitor_alert_state`

## Monitor automático

Por defecto revisa cada 60 segundos. Solo evalúa campañas que tengan una orden activa.

El monitor lee todos los países activos configurados en `monitored_countries` y respeta el intervalo y el chat de alertas de cada uno. Si en un chat querés trabajar con otro país, usá `/pais <país>` para fijar el contexto de ese chat.

Una alerta se genera cuando cambia el conjunto de elementos que están fuera del objetivo (tanteador total, D3, D4 o Air). Si la situación no cambia, no vuelve a enviar la misma alerta. Cuando todo vuelve a estar alineado, envía un aviso de recuperación.

## GitHub Actions

El workflow se puede iniciar manualmente y también se relanza de forma programada. Usa una regla de concurrencia para evitar dos instancias del bot haciendo polling simultáneamente.

## Portabilidad

Supabase se usa actualmente como PostgreSQL administrado. La lógica del bot no depende de la API específica de Supabase; se conecta mediante `psycopg` y una URI PostgreSQL estándar.
