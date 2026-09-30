# Guía de uso para usuarios

## ¿Qué hace el bot?

El bot consulta las batallas activas de eRepublik para los países configurados y muestra el tanteador total y el estado de las divisiones D3, D4 y Aire.

Los administradores pueden cargar una orden para cada país rival. Una orden indica quién debe ganar esa batalla: el defensor o el atacante. El bot conserva esas órdenes en la base de datos y las aplica automáticamente cada vez que aparece el rival, incluso después de que el bot se reinicie.

Los usuarios comunes no modifican las órdenes. Pueden consultarlas y ver cómo afectan la lectura de las batallas.

## Comandos disponibles

### `/help` o `/ayuda`

Muestra dentro de Telegram esta ayuda con los comandos disponibles para usuarios comunes.

```text
/help
```

También podés usar:

```text
/ayuda
```

### `/start`

Muestra una ayuda breve, el país actual del chat y los comandos principales.

```text
/start
```

### `/paises`

Lista los países activos configurados y muestra el alias disponible para cada uno.

```text
/paises
```

También permite seleccionar un país para este chat:

```text
/paises Argentina
```

### `/pais`

Muestra el país seleccionado actualmente para el chat.

```text
/pais
```

Permite cambiar el país del chat:

```text
/pais Argentina
```

Para volver al país predeterminado:

```text
/pais reset
```

La selección se guarda para ese chat y se mantiene entre reinicios.

### `/<alias_del_pais>`

Cada país activo puede tener un alias propio, que aparece en `/paises`. Ese alias muestra directamente las batallas del país correspondiente.

Por ejemplo, si `/paises` muestra el alias `argentina`:

```text
/argentina
```

### `/ordenes`

Muestra las órdenes activas del país seleccionado para el chat.

```text
/ordenes
```

Ejemplo de resultado:

```text
Chile → DEFENSOR
```

Esto significa que, contra Chile, el objetivo configurado es que gane el defensor.

### Configurar órdenes (solo administradores)

Una orden permanente se guarda por rival y se aplica a las próximas batallas de ese rival, hasta que se cambie o se elimine:

```text
/orden Chile defensor
/orden Chile atacante
```

También se puede usar el ID del país en lugar del nombre. Para eliminarla:

```text
/sinorden Chile
```

`defensor`, `def`, `atacante` y `ataque` son formas válidas de indicar el objetivo.

Si hace falta corregir el objetivo de una sola batalla activa, sin tocar la orden permanente, se usa una orden única:

```text
/ordenunica 123456 defensor
```

La orden única tiene prioridad para esa batalla, se muestra como `[ÚNICA]` y se elimina cuando termina esa batalla. No se conserva para la siguiente batalla o ronda de la misma TW. Para quitarla antes:

```text
/sinordenunica 123456
```

Después de cualquier cambio, `/ordenes` permite revisar las órdenes permanentes y las excepciones activas.

### `/batallas`

Muestra las batallas activas del país seleccionado. Cuando existe una orden para un rival, la batalla aparece marcada con `[AUTO]` y el objetivo correspondiente.

```text
/batallas
```

Ejemplo:

```text
Chile [AUTO] GANAR
```

El objetivo se calcula a partir de la orden guardada y del rol que tenga el país monitoreado en esa batalla.

### `/difundir`

Genera un texto compacto, listo para copiar y pegar en WhatsApp o en el juego. Incluye las batallas con una orden activa, la bandera y el nombre del rival, si corresponde `GANAR` o `PERDER`, y el tanteador general. El texto no supera los 500 caracteres.

```text
/difundir
```

Ejemplo:

```text
ORDENES (MIERCOLES 30/09 16:25 — HORA ARGENTINA)

🇨🇱 Chile — PERDER | T 62-118
🇮🇹 Italia — GANAR | T 139-5
```

### Órdenes excepcionales por batalla

Una TW es la guerra completa; dentro de ella pueden existir varias batallas, y cada batalla puede tener distintos rounds o rondas. Un administrador puede cambiar el objetivo de una sola batalla sin modificar la orden general del rival:

```text
/ordenunica 123456 defensor
```

La batalla debe estar activa e incluir al país monitoreado. En `/batallas` y en el chequeo automático aparecerá como `[ÚNICA]`. Se elimina automáticamente cuando esa batalla termina, aunque la TW continúe y pueda abrirse otra ronda.

Para retirarla manualmente:

```text
/sinordenunica 123456
```

### `/vacias`

Busca en todas las batallas activas rondas de una división que llevan más del tiempo indicado con un lado sin dominio. En esta primera versión, los casos buscados son `50%-50%`, `100%-0%` y `0%-100%`.

```text
/vacias D3 50
```

También se pueden consultar `D4` y `A` (Aire). El resultado incluye atacante, defensor, el lado sin dominio, el ID de la batalla y la antigüedad aproximada de la ronda.

### `/monitor`

Muestra el estado del monitor automático, el intervalo de revisión, la última revisión y el último error registrado.

```text
/monitor
```

Las alertas automáticas solo se generan para batallas que tienen una orden activa.

### `/estado`

Muestra un resumen general del bot, el país actual, la cantidad de órdenes activas y el estado del monitor.

```text
/estado
```

### `/id`

Muestra el User ID y el Chat ID de Telegram. Es útil para identificar un chat o pedir asistencia al administrador.

```text
/id
```

### `/test`

Consulta una batalla de control histórica para verificar que el bot pueda comunicarse con eRepublik.

```text
/test
```

## Flujo recomendado

1. Ejecutá `/paises` para ver los países disponibles.
2. Elegí el país del chat con `/pais <país>` o `/paises <país>`.
3. Ejecutá `/ordenes` para conocer los objetivos configurados.
4. Ejecutá `/batallas` para ver las batallas y las marcas `[AUTO]`.
5. Consultá `/monitor` si querés revisar el estado de las alertas automáticas.

## Importante sobre las órdenes

- Una orden se aplica por rival y queda fija hasta que un administrador la cambie o la desactive.
- Las órdenes no se pierden cuando termina una ejecución de GitHub Actions.
- Una batalla sin orden activa se muestra sin objetivo automático.
- `[AUTO] GANAR` o `[AUTO] PERDER` representa el objetivo calculado para el país monitoreado.
- Los círculos verdes no se muestran cuando la situación es correcta. `🔴` identifica un tanteador general (`T`) contrario al objetivo y `⚠️` identifica una división (`D3`, `D4` o `A`) que requiere atención. Las alertas automáticas se generan únicamente si el tanteador general contradice el objetivo.
- El chequeo automático se envía en cada intervalo configurado al chat de alertas e incluye las batallas activas, aunque estén correctas. Las alertas especiales solo se generan para batallas con una orden activa.
- El bot avisa por escalones sobre el tanteador general del lado que contradice la orden: a los 50 puntos envía una `PRIMERA ALERTA`, a los 100 una `ALERTA CRÍTICA` y a los 130 una `ALERTA CRÍTICA` urgente. Al llegar a 150 puntos, la batalla se considera ganada.
- Si cambió un acuerdo político o militar, avisale a un administrador para que actualice la orden.
