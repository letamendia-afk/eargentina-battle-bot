# Guía de uso para usuarios

## ¿Qué hace el bot?

El bot consulta las batallas activas de eRepublik para los países configurados y muestra el tanteador total y el estado de las divisiones D3, D4 y Aire.

Los administradores pueden cargar una orden para cada país rival. Una orden indica quién debe ganar esa batalla: el defensor o el atacante. El bot conserva esas órdenes en la base de datos y las aplica automáticamente cada vez que aparece el rival, incluso después de que el bot se reinicie.

Los usuarios comunes no modifican las órdenes. Pueden consultarlas y ver cómo afectan la lectura de las batallas.

## Comandos disponibles

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
- Los círculos verdes no se muestran cuando la situación es correcta; solo aparece 🔴 cuando el tanteador o una división contradice el objetivo. Las alertas automáticas se generan únicamente si el tanteador general contradice el objetivo.
- El bot avisa por escalones sobre el tanteador general del lado que contradice la orden: a los 50 puntos envía una `PRIMERA ALERTA`, a los 100 una `ALERTA CRÍTICA` y a los 130 una `ALERTA CRÍTICA` urgente. Al llegar a 150 puntos, la batalla se considera ganada.
- Si cambió un acuerdo político o militar, avisale a un administrador para que actualice la orden.
