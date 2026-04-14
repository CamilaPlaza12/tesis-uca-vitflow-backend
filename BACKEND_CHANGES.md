# BACKEND CHANGES — Refactorización de Stock por Componentes

> **Audiencia:** equipo de frontend.  
> **Última actualización:** 2026-04-12

---

## 0. Nuevo endpoint: totales disponibles

### `GET /api/v1/stock/totales`

Devuelve el conteo de unidades con `estado = "disponible"` en las tres
colecciones (`globulos_rojos`, `plasma`, `plaquetas`) **del hospital del
usuario autenticado** (leído del token, no del frontend).

**Headers requeridos:**
```
Authorization: Bearer <token>
```

**Respuesta `200 OK`:**
```json
{
  "total": 45,
  "globulos_rojos": 20,
  "plasma": 15,
  "plaquetas": 10
}
```

> Usar este endpoint para el contador de "unidades totales disponibles" del
> home. El endpoint anterior (`/blood-bank`) devolvía datos del modelo viejo
> y el número era incorrecto.

---

## 1. Resumen del cambio

Hasta ahora el sistema manejaba el stock de sangre como un único contador
genérico por grupo sanguíneo (ej: "tenemos 10 unidades de A+"). Eso cambió.

El stock ahora se modela a nivel de **unidad física individual**, separada
por **componente sanguíneo**: glóbulos rojos, plasma y plaquetas. Cada unidad
tiene su propio ciclo de vida (fecha de creación, fecha de vencimiento, estado).
Los endpoints del banco de sangre viejo (`/blood-bank`) **no se eliminaron** y
siguen funcionando; los nuevos endpoints conviven con ellos.

---

## 2. Colecciones nuevas en Firestore

Se crearon **cuatro** colecciones nuevas. Las colecciones existentes no se tocaron.

### `globulos_rojos`, `plasma`, `plaquetas`

Cada documento representa **una unidad física** de ese componente.

```json
{
  "id": "abc123xyz",
  "hospital_id": "hospital_456",
  "blood_group": "A+",
  "fecha_creacion": "2026-04-10T14:30:00Z",
  "fecha_vencimiento": "2026-05-22T14:30:00Z",
  "estado": "disponible",
  "turno_id": "turno_789",
  "donante_id": "donante_321"
}
```

| Campo              | Tipo      | Obligatorio | Notas |
|--------------------|-----------|-------------|-------|
| `id`               | string    | sí          | ID generado por Firestore |
| `hospital_id`      | string    | sí          | — |
| `blood_group`      | string    | sí          | Ver enums §5 |
| `fecha_creacion`   | timestamp | sí          | UTC, seteado automáticamente al crear |
| `fecha_vencimiento`| timestamp | sí          | Calculado automáticamente (ver §5) |
| `estado`           | string    | sí          | `disponible` al crear; ver enums §5 |
| `turno_id`         | string    | **no**      | Puede ser `null` si no viene de un turno |
| `donante_id`       | string    | **no**      | Puede ser `null` si se carga manualmente |

**Vida útil por componente** (determina `fecha_vencimiento`):

| Componente      | Días desde creación |
|-----------------|---------------------|
| `globulos_rojos`| 42 días             |
| `plasma`        | 365 días            |
| `plaquetas`     | 5 días              |

### `stock_umbrales`

Almacena el umbral mínimo de stock para un componente + grupo sanguíneo en un hospital.
El frontend puede usarlos para mostrar alertas visuales cuando el stock baja de ese valor.

```json
{
  "id": "umbral_111",
  "hospital_id": "hospital_456",
  "componente": "globulos_rojos",
  "blood_group": "O-",
  "umbral_minimo": 5
}
```

---

## 3. Endpoints nuevos

Todos requieren el header `Authorization: Bearer <firebase_id_token>`.  
Base URL: `/api/v1`

---

### Dashboard de stock — resumen completo

**`GET /stock/dashboard/resumen?hospital_id={id}`**

El endpoint más importante para el dashboard. Devuelve en **una sola llamada**
el conteo de unidades disponibles para los tres componentes, con todos los grupos
sanguíneos presentes (aunque tengan 0).

```
GET /api/v1/stock/dashboard/resumen?hospital_id=hospital_456
Authorization: Bearer <token>
```

Respuesta `200 OK`:

```json
{
  "globulos_rojos": {
    "A+": 4, "A-": 1, "B+": 0, "B-": 2,
    "AB+": 0, "AB-": 0, "O+": 5, "O-": 1,
    "total": 13
  },
  "plasma": {
    "A+": 2, "A-": 0, "B+": 1, "B-": 0,
    "AB+": 0, "AB-": 0, "O+": 3, "O-": 2,
    "total": 8
  },
  "plaquetas": {
    "A+": 0, "A-": 0, "B+": 1, "B-": 0,
    "AB+": 0, "AB-": 0, "O+": 2, "O-": 0,
    "total": 3
  }
}
```

> Los 8 grupos sanguíneos **siempre están presentes** en la respuesta, nunca se omiten.  
> `total` es la suma de todos los grupos de ese componente.  
> Solo cuenta unidades con `estado = "disponible"`.

---

### Agregar unidad de componente

**`POST /stock/{componente}/agregar`**  
*(alias semántico — equivalente a `POST /stock/{componente}`)*

Registra una unidad nueva. El estado inicial siempre es `"disponible"`.
La `fecha_vencimiento` se calcula automáticamente; no hay que enviarla.

```
POST /api/v1/stock/globulos_rojos/agregar
Authorization: Bearer <token>
Content-Type: application/json
```

Body:

```json
{
  "hospital_id": "hospital_456",
  "blood_group": "A+",
  "turno_id": null,
  "donante_id": null
}
```

Respuesta `201 Created`:

```json
{
  "id": "abc123xyz",
  "hospital_id": "hospital_456",
  "blood_group": "A+",
  "fecha_creacion": "2026-04-10T14:30:00Z",
  "fecha_vencimiento": "2026-05-22T14:30:00Z",
  "estado": "disponible",
  "turno_id": null,
  "donante_id": null
}
```

> `{componente}` puede ser `globulos_rojos`, `plasma` o `plaquetas`.  
> `turno_id` y `donante_id` son opcionales; enviar `null` si no aplica.

---

### Listar unidades disponibles de un componente

**`GET /stock/{componente}/disponibles`**

Devuelve solo las unidades con `estado = "disponible"`. Filtros opcionales por query param.

```
GET /api/v1/stock/plasma/disponibles?hospital_id=hospital_456&blood_group=O%2B
Authorization: Bearer <token>
```

| Query param   | Obligatorio | Ejemplo |
|---------------|-------------|---------|
| `hospital_id` | no          | `hospital_456` |
| `blood_group` | no          | `O+` (URL-encode el `+` como `%2B`) |

Respuesta `200 OK`: array de objetos `UnidadOut` (misma estructura que en §3 Agregar).

```json
[
  {
    "id": "abc123xyz",
    "hospital_id": "hospital_456",
    "blood_group": "O+",
    "fecha_creacion": "2026-04-10T14:30:00Z",
    "fecha_vencimiento": "2027-04-10T14:30:00Z",
    "estado": "disponible",
    "turno_id": null,
    "donante_id": null
  }
]
```

> Si no hay unidades que coincidan devuelve `[]`, nunca un error.

---

### Retirar una unidad (uso clínico)

**`PATCH /stock/{componente}/{id}/retirar`**

Marca la unidad como `"usado"`. No requiere body.
Usar cuando una unidad se entrega a un paciente o se usa clínicamente.

```
PATCH /api/v1/stock/globulos_rojos/abc123xyz/retirar
Authorization: Bearer <token>
```

Respuesta `200 OK`: objeto `UnidadOut` con `estado: "usado"`.

---

### Vencer una unidad manualmente

**`PATCH /stock/{componente}/{id}/vencer`**

Marca la unidad como `"vencido"`. No requiere body.
Uso manual mientras no exista un job automático de vencimiento.

```
PATCH /api/v1/stock/plaquetas/abc123xyz/vencer
Authorization: Bearer <token>
```

Respuesta `200 OK`: objeto `UnidadOut` con `estado: "vencido"`.

---

### Confirmar donación y registrar componentes obtenidos

**`POST /donaciones/confirmar`**

Cuando un donante asiste a su turno, este endpoint registra qué componentes
se extrajeron. Por cada componente en la lista se crea una unidad nueva en
su colección con `estado = "disponible"`. **No modifica el turno.**

```
POST /api/v1/donaciones/confirmar
Authorization: Bearer <token>
Content-Type: application/json
```

Body:

```json
{
  "turno_id": "turno_789",
  "donante_id": "donante_321",
  "hospital_id": "hospital_456",
  "blood_group": "A+",
  "componentes": ["globulos_rojos", "plasma"]
}
```

> `componentes` acepta cualquier combinación de los tres valores posibles.
> Debe tener al menos un elemento.

Respuesta `201 Created`:

```json
{
  "turno_id": "turno_789",
  "donante_id": "donante_321",
  "unidades_creadas": [
    {
      "id": "gr_001",
      "hospital_id": "hospital_456",
      "blood_group": "A+",
      "fecha_creacion": "2026-04-10T14:30:00Z",
      "fecha_vencimiento": "2026-05-22T14:30:00Z",
      "estado": "disponible",
      "turno_id": "turno_789",
      "donante_id": "donante_321"
    },
    {
      "id": "pl_002",
      "hospital_id": "hospital_456",
      "blood_group": "A+",
      "fecha_creacion": "2026-04-10T14:30:00Z",
      "fecha_vencimiento": "2027-04-10T14:30:00Z",
      "estado": "disponible",
      "turno_id": "turno_789",
      "donante_id": "donante_321"
    }
  ]
}
```

---

### Resumen por componente (por separado)

**`GET /stock/{componente}/resumen?hospital_id={id}`**

Alternativa al endpoint de dashboard cuando solo se necesita un componente.

Respuesta `200 OK`:

```json
{
  "hospital_id": "hospital_456",
  "componente": "globulos_rojos",
  "disponibles_por_grupo": {
    "A+": 4,
    "O-": 1
  }
}
```

> A diferencia del dashboard, aquí **solo se incluyen los grupos con stock > 0**.
> Para el dashboard completo preferir `GET /stock/dashboard/resumen`.

---

### Listar todas las unidades de un componente (con filtros)

**`GET /stock/{componente}?hospital_id=&blood_group=&estado=`**

Todos los filtros son opcionales. Permite listar por cualquier estado, incluyendo
`"usado"` y `"vencido"` (útil para historial).

---

### Obtener una unidad por ID

**`GET /stock/{componente}/{id}`**

Responde con el objeto `UnidadOut` o `404` si no existe.

---

### Actualizar estado de una unidad (genérico)

**`PATCH /stock/{componente}/{id}`**

Body:

```json
{ "estado": "vencido" }
```

Acepta cualquier valor del enum de estado. Para las acciones más comunes
preferir los endpoints semánticos `/retirar` y `/vencer`.

---

### Eliminar una unidad

**`DELETE /stock/{componente}/{id}`**

Responde `204 No Content`. Sin body.

---

### Umbrales mínimos

**`GET /stock/umbrales?hospital_id={id}`** — lista todos los umbrales del hospital.

**`POST /stock/umbrales`** — crea o actualiza un umbral (upsert por hospital+componente+grupo).

Body:

```json
{
  "hospital_id": "hospital_456",
  "componente": "plaquetas",
  "blood_group": "O-",
  "umbral_minimo": 3
}
```

**`PATCH /stock/umbrales/{umbral_id}`** — modifica solo el valor mínimo.

Body:

```json
{ "umbral_minimo": 5 }
```

Respuesta de los tres: objeto `UmbralOut`.

```json
{
  "id": "umbral_111",
  "hospital_id": "hospital_456",
  "componente": "plaquetas",
  "blood_group": "O-",
  "umbral_minimo": 5
}
```

---

## 4. Endpoints que siguen igual

Los siguientes endpoints **no fueron modificados** y pueden seguirse usando sin cambios:

| Método | URL | Descripción |
|--------|-----|-------------|
| `GET`  | `/api/v1/blood-bank` | Stock agregado (modelo viejo) |
| `PATCH`| `/api/v1/blood-bank/add-stock` | Sumar unidades al stock viejo |
| `PATCH`| `/api/v1/blood-bank/remove-stock` | Restar unidades al stock viejo |
| `PATCH`| `/api/v1/blood-bank/thresholds` | Umbrales del stock viejo |
| `POST` | `/api/v1/auth/register` | Registro de usuario |
| `GET`  | `/api/v1/auth/me` | Perfil del usuario autenticado |
| `GET`  | `/api/v1/auth/me/full` | Perfil completo |
| `GET`  | `/api/v1/appointments/` | Listar turnos |
| `POST` | `/api/v1/appointments/manual` | Crear turno manual |
| `PATCH`| `/api/v1/appointments/{id}/status` | Cambiar estado de turno |
| `PATCH`| `/api/v1/appointments/{id}/reschedule` | Reprogramar turno |
| `POST` | `/api/v1/appointments/vito` | Turno vía chatbot Vito |
| `GET`  | `/api/v1/hospital-requests/` | Pedidos de sangre |
| `POST` | `/api/v1/hospital-requests/` | Crear pedido |
| `PATCH`| `/api/v1/hospital-requests/{id}` | Actualizar pedido |
| `GET`  | `/api/v1/donors/` | Listar donantes |
| `POST` | `/api/v1/donors/` | Crear donante |
| `GET`  | `/api/v1/home/summary` | Resumen del home |
| `GET`  | `/api/v1/users` | Listar usuarios |
| todos  | `/api/v1/hospital-availability` | Disponibilidad hospitalaria |
| todos  | `/api/v1/hospital-onboarding/` | Onboarding de hospitales |

---

## 5. Enums y valores válidos

### `componente`
```
globulos_rojos | plasma | plaquetas
```

### `estado`
```
disponible | usado | vencido
```
- Al crear una unidad el estado es siempre `"disponible"` (el backend lo fija, no se envía).
- `"usado"`: unidad entregada a un paciente o utilizada clínicamente.
- `"vencido"`: unidad fuera de su vida útil.

### `blood_group`
```
A+ | A- | B+ | B- | AB+ | AB- | O+ | O-
```
> El `+` en URLs debe codificarse como `%2B`. Ejemplo: `blood_group=O%2B`.

### Vida útil por componente

| Componente       | Vencimiento desde fecha de creación |
|------------------|-------------------------------------|
| `globulos_rojos` | 42 días                             |
| `plasma`         | 365 días                            |
| `plaquetas`      | 5 días ← **muy corto, tenerlo en cuenta para alertas** |

---

## 6. Pantallas del frontend que necesitan cambios

### Dashboard de stock

**Antes:** una única sección mostrando el total de unidades por grupo sanguíneo  
(proveniente de `GET /blood-bank`, que devuelve un único objeto con `stocks_units`).

**Ahora:** debe dividirse en **tres secciones**, una por componente.

**Endpoint a consumir:**
```
GET /api/v1/stock/dashboard/resumen
Authorization: Bearer <firebase_id_token>
```

**Estructura de datos que recibirá:**
```json
{
  "globulos_rojos": { "A+": 4, "A-": 1, "B+": 0, ..., "total": 13 },
  "plasma":         { "A+": 2, "A-": 0, "B+": 1, ..., "total": 8  },
  "plaquetas":      { "A+": 0, "A-": 0, "B+": 1, ..., "total": 3  }
}
```

**Notas de implementación:**
- Los 8 grupos siempre están presentes, incluso con valor 0 → no hace falta manejar ausencia de claves.
- Mostrar `total` como número destacado por componente es suficiente para una vista rápida.
- Para alertas de umbral bajo, comparar con los valores de `GET /stock/umbrales` (sin parámetros) y cruzar por `componente` + `blood_group`.

---

### Pantalla de confirmación de donación

**Antes:** al confirmar que un donante asistió, solo se actualizaba el estado del turno.  
El frontend no registraba qué componentes se obtuvieron.

**Ahora:** luego de (o junto con) confirmar el turno, el frontend debe presentar
un formulario/modal donde el personal del hospital seleccione qué componentes
se extrajeron de esa donación y llamar al nuevo endpoint.

**Endpoint a consumir:**
```
POST /api/v1/donaciones/confirmar
```

**Body a enviar:**
```json
{
  "turno_id":   "id_del_turno",
  "donante_id": "id_del_donante",
  "blood_group": "A+",
  "componentes": ["globulos_rojos", "plasma"]
}
```

> `blood_group` es el grupo del donante (dato ya disponible en el turno/donante).  
> `componentes` es una lista de checkboxes que el usuario selecciona.
> Debe tener al menos 1 elemento seleccionado (el backend lo valida).
> `hospital_id` **no va en el body** — el backend lo lee del token.

**Estructura de datos que recibirá:**
```json
{
  "turno_id": "id_del_turno",
  "donante_id": "id_del_donante",
  "unidades_creadas": [
    {
      "id": "gr_001",
      "hospital_id": "hospital_456",
      "blood_group": "A+",
      "fecha_creacion": "2026-04-10T14:30:00Z",
      "fecha_vencimiento": "2026-05-22T14:30:00Z",
      "estado": "disponible",
      "turno_id": "id_del_turno",
      "donante_id": "id_del_donante"
    }
  ]
}
```

El array `unidades_creadas` tiene tantos elementos como componentes se enviaron.
El frontend puede usar esto para mostrar un feedback de confirmación
("Se registraron 2 unidades: glóbulos rojos vence el 22/05, plasma vence el 10/04/2027").

**Importante:** este endpoint **no cambia el estado del turno**. Si el flujo actual
actualiza el estado del turno con `PATCH /appointments/{id}/status`, esa llamada
sigue siendo necesaria por separado.

---

## 7. Referencia rápida de endpoints clave

### GET /api/v1/stock/umbrales

```
GET /api/v1/stock/umbrales
Authorization: Bearer <firebase_id_token>
```

Sin parámetros. Devuelve los 24 umbrales del hospital (3 componentes × 8 grupos).

**Respuesta:**
```json
[
  {
    "id": "0f8L57YCBxxyZxI772hZ",
    "hospital_id": "nGIcjJ9VfPVL0HF1TvLA",
    "componente": "globulos_rojos",
    "blood_group": "O+",
    "umbral_minimo": 5
  },
  {
    "id": "4Gef2FNbiYO5dCbMO7iK",
    "hospital_id": "nGIcjJ9VfPVL0HF1TvLA",
    "componente": "plasma",
    "blood_group": "A+",
    "umbral_minimo": 3
  },
  {
    "id": "9dXvNpQrsT4uVwYZ1efg",
    "hospital_id": "nGIcjJ9VfPVL0HF1TvLA",
    "componente": "plaquetas",
    "blood_group": "AB-",
    "umbral_minimo": 2
  }
]
```

Valores por defecto al inicializar: `globulos_rojos=5`, `plasma=3`, `plaquetas=2`.  
Para cruzar con el stock actual y detectar grupos por debajo del umbral,
combinar con `GET /api/v1/stock/dashboard/resumen`.

---

### GET /api/v1/home/summary

```
GET /api/v1/home/summary
Authorization: Bearer <firebase_id_token>
```

Sin parámetros. Devuelve el resumen del dashboard principal del hospital.

**Respuesta:**
```json
{
  "stocks": {
    "A+": 12, "A-": 3, "B+": 0, "B-": 1,
    "AB+": 4, "AB-": 0, "O+": 8, "O-": 2
  },
  "thresholds": {
    "A+": 10, "A-": 5, "B+": 5, "B-": 3,
    "AB+": 2, "AB-": 2, "O+": 8, "O-": 4
  },
  "kpis": {
    "totalUnits": 30,
    "urgentActive": 2,
    "appointmentsToday": 5,
    "criticalGroupsCount": 3
  },
  "appointments": [
    { "time_local": "09:00", "donation_type": "SANGRE",    "status": "PROGRAMADO" },
    { "time_local": "10:30", "donation_type": "PLAQUETAS", "status": "CONFIRMADO" }
  ],
  "activeRequests": [
    {
      "date": "11/04/2026",
      "hospital_unit": "Guardia",
      "component": "SANGRE",
      "blood_group": "O+",
      "requested_units": 3.0,
      "priority": "URGENTE",
      "status": "ACTIVO"
    }
  ]
}
```

| Campo | Descripción |
|-------|-------------|
| `stocks` | Stock agregado por grupo sanguíneo (modelo viejo de blood-bank) |
| `thresholds` | Umbrales del modelo viejo de blood-bank |
| `kpis.totalUnits` | Suma de todas las unidades del stock viejo |
| `kpis.urgentActive` | Pedidos activos con prioridad URGENTE o CRITICA |
| `kpis.appointmentsToday` | Turnos de hoy con estado PROGRAMADO o CONFIRMADO |
| `kpis.criticalGroupsCount` | Grupos por debajo de su umbral |
| `appointments` | Turnos de hoy y mañana, ordenados por hora |
| `activeRequests` | Todos los pedidos hospitalarios del hospital |

> **Nota:** `stocks` y `thresholds` pertenecen al modelo de sangre viejo (`/blood-bank`).
> Son independientes del nuevo sistema de unidades por componente (`/stock/*`).
> Si el dashboard necesita el desglose por glóbulos/plasma/plaquetas, usar además
> `GET /api/v1/stock/dashboard/resumen`.

---

---

## 8. Actualización 2026-04-12 — Múltiples unidades y historial de movimientos

### 8.1 `POST /stock/{componente}/agregar` — ahora soporta múltiples unidades

El endpoint ya **no devuelve un objeto único**, sino un **array** con todas las unidades creadas.

**Body actualizado:**

```json
{
  "blood_group": "A+",
  "cantidad": 3
}
```

| Campo       | Tipo   | Obligatorio | Descripción |
|-------------|--------|-------------|-------------|
| `blood_group` | string | sí | Grupo sanguíneo (enum §5) |
| `cantidad`  | int    | no | Unidades a crear. Default: `1`. Máximo: `100`. |

> `turno_id` y `donante_id` ya no forman parte de este body. Para cargas manuales no se asocian a un turno.

**Respuesta `201 Created`:** array de `UnidadOut`

```json
[
  {
    "id": "abc1",
    "hospital_id": "hospital_456",
    "blood_group": "A+",
    "fecha_creacion": "2026-04-12T10:00:00Z",
    "fecha_vencimiento": "2026-05-24T10:00:00Z",
    "estado": "disponible",
    "turno_id": null,
    "donante_id": null
  },
  {
    "id": "abc2",
    "blood_group": "A+",
    "..."
  }
]
```

> El registro de historial se crea automáticamente — el frontend no tiene que hacer nada adicional.

---

### 8.2 `PATCH /stock/{componente}/retirar` — retiro de múltiples unidades

**Nuevo endpoint.** Retira varias unidades en una sola operación.

> El endpoint individual `PATCH /stock/{componente}/{id}/retirar` **sigue existiendo** y no fue modificado.

```
PATCH /api/v1/stock/globulos_rojos/retirar
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**

```json
{
  "unidad_ids": ["id1", "id2", "id3"],
  "motivo": "transfusion",
  "motivo_detalle": null
}
```

| Campo          | Tipo           | Obligatorio | Descripción |
|----------------|----------------|-------------|-------------|
| `unidad_ids`   | array\<string\> | sí          | Al menos 1 ID. Todas deben pertenecer al hospital del token. |
| `motivo`       | string         | no          | `transfusion` \| `trasplante` \| `operacion` \| `otro` |
| `motivo_detalle` | string       | condicional | Obligatorio si `motivo == "otro"` |

**Respuesta `200 OK`:** array de `UnidadOut` con `estado: "usado"`.

> Si alguna unidad no existe o pertenece a otro hospital, devuelve `404` o `403` y ninguna unidad es modificada hasta ese punto (no hay transacción atómica — se procesan en orden).

> El registro de historial se crea automáticamente.

---

### 8.3 `GET /stock/historial` — historial de movimientos

Lista todos los movimientos de stock del hospital autenticado, ordenados por fecha descendente.

```
GET /api/v1/stock/historial
Authorization: Bearer <token>
```

**Query params opcionales:**

| Parámetro   | Valores válidos | Descripción |
|-------------|-----------------|-------------|
| `componente` | `globulos_rojos` \| `plasma` \| `plaquetas` | Filtrar por componente |
| `accion`    | `agrego` \| `retiro` | Filtrar por tipo de movimiento |
| `desde`     | ISO date, ej: `2026-04-01` | Fecha de inicio (inclusive) |
| `hasta`     | ISO date, ej: `2026-04-30` | Fecha de fin (inclusive) |

**Respuesta `200 OK`:**

```json
[
  {
    "id": "mov_001",
    "hospital_id": "hospital_456",
    "usuario_id": "uid_del_usuario",
    "usuario_nombre": "María López",
    "accion": "retiro",
    "componente": "globulos_rojos",
    "blood_group": "A+",
    "unidades_ids": ["id1", "id2"],
    "cantidad": 2,
    "motivo": "transfusion",
    "motivo_detalle": null,
    "fecha": "2026-04-12T14:30:00Z"
  }
]
```

> `usuario_nombre` se construye automáticamente del perfil del usuario autenticado (`firstName + lastName`).

**Cuándo se genera un registro automáticamente:**

| Acción | `accion` en historial | Notas |
|--------|-----------------------|-------|
| `POST /stock/{componente}/agregar` | `"agrego"` | Un registro por llamada, con todas las unidades creadas |
| `PATCH /stock/{componente}/retirar` | `"retiro"` | Un registro por llamada, con todas las unidades retiradas |
| `POST /donaciones/confirmar` | `"agrego"` | Un registro por cada componente en `body.componentes` |

> El endpoint individual `PATCH /{componente}/{id}/retirar` **no** genera historial (es el endpoint legacy). Para historial usar el nuevo bulk.

**Colección Firestore nueva:** `stock_historial`

```json
{
  "hospital_id": "hospital_456",
  "usuario_id": "uid_abc",
  "usuario_nombre": "María López",
  "accion": "agrego",
  "componente": "plasma",
  "blood_group": "O+",
  "unidades_ids": ["pl_001", "pl_002", "pl_003"],
  "cantidad": 3,
  "motivo": null,
  "motivo_detalle": null,
  "fecha": "2026-04-12T10:00:00Z"
}
```

---

## 9. Pendiente — no implementar todavía (renumerado desde §7)

Las siguientes features están marcadas como TODO en el código y **no están implementadas**.
El frontend no debe construir pantallas para estas funcionalidades aún:

### Donación por aféresis
La donación exclusiva de plaquetas por aféresis requiere un tipo de turno diferente
al turno genérico actual. En esta modalidad el donante dona únicamente plaquetas,
en mayor cantidad que en una donación de sangre completa.  
Cuando se implemente tendrá su propio flujo de confirmación y un nuevo tipo de turno `"aferesis"`.  
Las unidades generadas irán a la colección `plaquetas` igual que hoy.

### Vencimiento automático de unidades
Hoy las unidades no se marcan automáticamente como `"vencido"` al superar su `fecha_vencimiento`.
Existe el endpoint `PATCH /stock/{componente}/{id}/vencer` para hacerlo manualmente.
En el futuro habrá un job automático (Cloud Function u otro) que lo haga sin intervención.

### Features fuera del scope de esta refactorización
- Cantidades en mililitros por unidad
- Vincular turnos a componentes específicos desde el módulo de turnos
- Modificar pedidos hospitalarios para referenciar componentes

---

## 9. Seguridad — hospital_id desde el token

> **Cambio importante** (2026-04-11): el `hospital_id` ya **no se pasa como parámetro**
> en ningún endpoint de stock ni donaciones. El backend lo lee directamente del
> token de Firebase del usuario autenticado.

### De dónde viene el hospital_id ahora

El flujo es:

1. El usuario se autentica con Firebase y recibe un ID token.
2. En cada request, el backend verifica el token con Firebase Admin SDK.
3. Con el `uid` del token, el backend lee el documento `users/{uid}` en Firestore
   y extrae el campo `hospitalId` (que fue asignado durante el onboarding).
4. Ese `hospitalId` se usa en todas las queries de stock — el frontend nunca puede
   falsificarlo porque no forma parte del body ni de los query params.

Además, en los endpoints PATCH (retirar, vencer, actualizar umbral), el backend
verifica que el recurso pertenezca al hospital del usuario antes de modificarlo.
Si otro hospital intenta modificar un recurso ajeno, recibe `403 Forbidden`.

### Impacto en las llamadas del frontend

**Antes** (ya no funciona así):
```
GET /api/v1/stock/umbrales?hospital_id=nGIcjJ9VfPVL0HF1TvLA
GET /api/v1/stock/dashboard/resumen?hospital_id=nGIcjJ9VfPVL0HF1TvLA
```

**Ahora** (forma correcta):
```
GET /api/v1/stock/umbrales
GET /api/v1/stock/dashboard/resumen
Authorization: Bearer <firebase_id_token>
```

El token ya identifica al hospital. No hay que pasar `hospital_id` en ningún lado.

### Endpoints que cambiaron su firma

| Endpoint | Antes | Ahora |
|----------|-------|-------|
| `GET /stock/umbrales` | `?hospital_id=...` requerido | Sin params — hospital del token |
| `GET /stock/dashboard/resumen` | `?hospital_id=...` requerido | Sin params |
| `GET /stock/{componente}` | `?hospital_id=...` opcional | Sin hospital_id — siempre filtra por el del token |
| `GET /stock/{componente}/disponibles` | `?hospital_id=...` opcional | Solo acepta `?blood_group=...` |
| `GET /stock/{componente}/resumen` | `?hospital_id=...` requerido | Sin params |
| `POST /stock/{componente}` y `/agregar` | Body incluía `hospital_id` | Sin `hospital_id` en body |
| `POST /stock/umbrales` | Body incluía `hospital_id` | Sin `hospital_id` en body |
| `POST /stock/umbrales/inicializar` | Body `{ hospital_id }` | Sin body — usa el del token |
| `POST /donaciones/confirmar` | Body incluía `hospital_id` | Sin `hospital_id` en body |

### Ejemplo actualizado — umbrales

```
GET /api/v1/stock/umbrales
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

HTTP 200 OK
[
  { "id": "0f8L57YCBxxyZxI772hZ", "hospital_id": "nGIcjJ9VfPVL0HF1TvLA", "componente": "globulos_rojos", "blood_group": "O+", "umbral_minimo": 5 },
  { "id": "4Gef2FNbiYO5dCbMO7iK", "hospital_id": "nGIcjJ9VfPVL0HF1TvLA", "componente": "plasma",         "blood_group": "AB+", "umbral_minimo": 3 },
  ...
]
```

### Ejemplo actualizado — confirmar donación

```json
POST /api/v1/donaciones/confirmar
Authorization: Bearer <token>
Content-Type: application/json

{
  "turno_id":   "turno_789",
  "donante_id": "donante_321",
  "blood_group": "A+",
  "componentes": ["globulos_rojos", "plasma"]
}
```

> `hospital_id` ya **no va en el body**. El backend lo lee del token.

---

## 9b. Notas técnicas para el frontend

### Campos opcionales
- `turno_id` y `donante_id` en `UnidadOut` pueden ser `null`. Manejar ambos casos en la UI.

### Campos siempre presentes
- `id`, `hospital_id`, `blood_group`, `fecha_creacion`, `fecha_vencimiento`, `estado`
  siempre están en toda respuesta de unidad.
- En `GET /stock/dashboard/resumen` los 8 grupos sanguíneos y `total` siempre están presentes.

### Codificación de `+` en URLs
Al filtrar por grupos como `A+`, `B+`, `O+`, `AB+` en query params, el `+` debe
ir codificado como `%2B`. Ejemplo: `?blood_group=O%2B`.

### Orden recomendado para implementar
1. **Dashboard de stock** — consumir `GET /stock/dashboard/resumen`. Es de solo lectura y no depende de nada más.
2. **Pantalla de confirmación de donación** — agregar el formulario de componentes y llamar a `POST /donaciones/confirmar`.
3. **Gestión manual de unidades** (si aplica) — usar `/agregar`, `/retirar`, `/vencer` según el flujo de gestión de banco de sangre.
4. **Umbrales y alertas** — implementar último, es opcional para el MVP.

### El modelo viejo de stock sigue activo
`GET /blood-bank` y sus endpoints asociados **no fueron eliminados**. Si el dashboard
actual los consume, puede seguir haciéndolo mientras se migra. Ambos modelos
(viejo y nuevo) están activos en paralelo.

---

## 10. Auditoría de seguridad completa — hospital_id y user_id

> **Actualización** (2026-04-11): se realizó una auditoría de seguridad sobre
> **todos** los endpoints del backend para garantizar que ninguno acepte
> `hospital_id` ni `user_id` como parámetro enviado desde el frontend.

### Resultado: ningún endpoint los acepta como parámetro externo

La auditoría cubrió los siguientes módulos:

| Módulo | Endpoints auditados | Resultado |
|--------|---------------------|-----------|
| `/stock/*` | 12 endpoints | ✅ hospital_id del token (ya auditado en §9) |
| `/donaciones/*` | 1 endpoint | ✅ hospital_id del token (ya auditado en §9) |
| `/appointments/*` | 11 endpoints | ✅ hospital_id del token |
| `/hospital-requests/*` | 4 endpoints | ✅ hospital_id del token |
| `/hospital-availability/*` | 2 endpoints | ✅ hospital_id del token |
| `/blood-bank/*` | 4 endpoints | ✅ hospital_id del token |
| `/home/*` | 1 endpoint | ✅ hospital_id del token |
| `/donors/*` | 9 endpoints | ✅ sin hospital_id ni user_id |
| `/users/*` | 5 endpoints | ✅ sin hospital_id |
| `/auth/*` | 3 endpoints | ✅ sin hospital_id |
| `/hospital-onboarding/*` | 3 endpoints | ✅ endpoint público, sin auth |

### Parámetros legítimos que SÍ vienen del frontend (no son hospital_id ni user_id)

Algunos endpoints reciben IDs de otras entidades que el frontend sí debe proveer,
porque representan datos de negocio que no pueden inferirse del token:

| Endpoint | Parámetro | Por qué es legítimo |
|----------|-----------|---------------------|
| `GET /appointments/request/{request_id}/available-days?donor_id=...` | `donor_id` | El hospital verifica elegibilidad de un donante externo; no es el usuario autenticado |
| `GET /appointments/request/{request_id}/available-time-ranges?donor_id=...` | `donor_id` | Ídem |
| `GET /appointments/request/{request_id}/available-slots?donor_id=...` | `donor_id` | Ídem |
| `POST /appointments/vito` body: `{ donor_id, ... }` | `donor_id` | El chatbot Vito reserva en nombre de un donante identificado por ID |

En todos estos casos el `donor_id` identifica a **otra persona** (el donante),
no al usuario autenticado. No puede venir del token.

### Mejora técnica aplicada: eliminación de lectura redundante a Firestore

`resolve_hospital_id()` en `app/utils/auth_utils.py` fue refactorizado.
**Antes** hacía una segunda lectura a Firestore en cada request para buscar el
`hospitalId` del usuario, aunque `get_current_user()` ya lo había leído y
almacenado en `current_user` durante la verificación del token.

**Ahora** lee directamente de `current_user["hospitalId"]`, eliminando el viaje
extra a la base de datos. Esto afecta todos los endpoints de:
`/appointments`, `/hospital-requests`, `/hospital-availability`.

El comportamiento externo no cambió — sigue devolviendo `403` si el usuario no
tiene hospital asociado.

### Conclusión para el equipo de frontend

> **No envíen `hospital_id` en ningún endpoint.** El backend lo obtiene siempre
> del token de Firebase. Si lo envían en el body o en query params, simplemente
> será ignorado (no falla, pero tampoco se usa).
>
> El único identificador de "otro usuario" que deben enviar es `donor_id` en los
> endpoints de disponibilidad de turnos y en el endpoint de Vito.
