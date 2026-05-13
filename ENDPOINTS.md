# Contrato de API — Módulo Eventos

Todos los endpoints requieren autenticación Firebase (`Authorization: Bearer <token>`).
El `hospital_id` se extrae del token; no se envía en el body.
Prefijo base: `/api/v1`

---

## Eventos

### POST /api/v1/eventos/
Crea un nuevo evento y genera automáticamente un Pedido tipo EVENTO asociado.

**Body:**
```json
{
  "nombre": "Campaña Primavera",
  "fecha": "2026-05-10",
  "hora_inicio": "09:00",
  "hora_fin": "17:00",
  "lugar": "Plaza Central",
  "capacidad_esperada": 100,
  "grupos_sanguineos": ["A", "B", "AB", "O"],
  "factores_rh": ["+", "-"]
}
```
Campos opcionales: `hora_inicio`, `hora_fin`, `lugar`, `capacidad_esperada`

**Response 201:**
```json
{
  "id": "firestore-doc-id",
  "nombre": "Campaña Primavera",
  "fecha": "2026-05-10",
  "hora_inicio": "09:00",
  "hora_fin": "17:00",
  "lugar": "Plaza Central",
  "capacidad_esperada": 100,
  "estado": "ACTIVO",
  "pedido_id": "firestore-pedido-id",
  "created_at": "2026-04-22T10:00:00-03:00"
}
```

**Errores:**
- `400` — grupos_sanguineos o factores_rh inválidos
- `400` / `403` — usuario sin hospital asociado

---

### GET /api/v1/eventos/
Lista todos los eventos del hospital, ordenados por fecha descendente.

**Response 200:**
```json
[
  {
    "id": "firestore-doc-id",
    "nombre": "Campaña Primavera",
    "fecha": "2026-05-10",
    "lugar": "Plaza Central",
    "estado": "ACTIVO",
    "total_donaciones": 42
  }
]
```

---

### GET /api/v1/eventos/activo/
Devuelve el evento con estado ACTIVO del hospital autenticado.

**Response 200:** igual que POST response

**Errores:**
- `404` — `{ "detail": "No hay ningún evento activo" }`

---

### PATCH /api/v1/eventos/{evento_id}
Edita campos del evento. Solo eventos en estado ACTIVO pueden editarse.

**Body (todos opcionales, enviar solo los que se quieren cambiar):**
```json
{
  "nombre": "Nuevo nombre",
  "fecha": "2026-05-15",
  "hora_inicio": "10:00",
  "hora_fin": "18:00",
  "lugar": "Nuevo lugar",
  "capacidad_esperada": 150
}
```

**Response 200:** el evento completo actualizado (misma estructura que POST response + `updated_at`)

**Errores:**
- `400` — sin campos para actualizar
- `404` — evento no encontrado
- `409` — el evento no está en estado ACTIVO

---

### PATCH /api/v1/eventos/{evento_id}/finalizar
Finaliza el evento y su pedido asociado.

**Body:** vacío

**Response 200:**
```json
{
  "id": "firestore-doc-id",
  "estado": "FINALIZADO",
  "mensaje": "Evento finalizado correctamente"
}
```

**Errores:**
- `404` — evento no encontrado
- `409` — el evento ya está FINALIZADO o está CANCELADO

---

## Donaciones dentro de un evento

### POST /api/v1/eventos/{evento_id}/registrar-donacion
Registra que una persona donó durante el evento. Recibe únicamente el DNI.
Si el DNI existe en el sistema de donantes, autocompleta el nombre.

**Body:**
```json
{
  "dni": "12345678"
}
```

**Response 201:**
```json
{
  "registro_id": "firestore-registro-id",
  "donante_dni": "12345678",
  "donante_nombre": "Juan Pérez",
  "timestamp_donacion": "2026-05-10T11:30:00-03:00",
  "mensaje": "Donación registrada correctamente"
}
```
`donante_nombre` puede ser `null` si el DNI no existe en el sistema.

**Errores:**
- `400` — `{ "detail": "Este DNI ya fue registrado en este evento" }`
- `404` — evento no encontrado
- `409` — el evento no está en estado ACTIVO

---

### GET /api/v1/eventos/{evento_id}/donaciones
Lista todos los registros de donación del evento.

**Response 200:**
```json
[
  {
    "registro_id": "firestore-registro-id",
    "donante_dni": "12345678",
    "donante_nombre": "Juan Pérez",
    "timestamp_donacion": "2026-05-10T11:30:00-03:00",
    "componente_donado": null
  }
]
```
`componente_donado` puede ser: `"SANGRE_ENTERA"` | `"PLASMA"` | `"PLAQUETAS"` | `"GLOBULOS_ROJOS"` | `null`

**Errores:**
- `404` — evento no encontrado

---

### GET /api/v1/eventos/{evento_id}/pendientes-clasificacion
Lista solo los registros donde `componente_donado` es `null`.

**Response 200:** mismo formato que `/donaciones`, filtrado

**Errores:**
- `404` — evento no encontrado

---

### PATCH /api/v1/registros-donacion/{registro_id}/clasificar
Clasifica el componente donado de un registro existente.

**Body:**
```json
{
  "componente_donado": "PLASMA"
}
```
Valores válidos: `"SANGRE_ENTERA"` | `"PLASMA"` | `"PLAQUETAS"` | `"GLOBULOS_ROJOS"`

**Response 200:**
```json
{
  "registro_id": "firestore-registro-id",
  "donante_dni": "12345678",
  "donante_nombre": "Juan Pérez",
  "componente_donado": "PLASMA",
  "mensaje": "Clasificación guardada correctamente"
}
```

**Errores:**
- `404` — registro no encontrado (o no pertenece al hospital autenticado)
- `422` — `componente_donado` con valor inválido

---

## Dashboard

### GET /api/v1/eventos/{evento_id}/dashboard
Resumen estadístico del evento.

**Response 200:**
```json
{
  "evento_id": "firestore-doc-id",
  "nombre": "Campaña Primavera",
  "fecha": "2026-05-10",
  "hora_inicio": "09:00",
  "hora_fin": "17:00",
  "lugar": "Plaza Central",
  "estado": "ACTIVO",
  "capacidad_esperada": 100,
  "total_donaciones_registradas": 42,
  "pendientes_clasificacion": 8,
  "porcentaje_avance": 42.0,
  "por_componente": {
    "plasma": 10,
    "plaquetas": 5,
    "globulos_rojos": 12,
    "sangre_entera": 7,
    "sin_clasificar": 8
  }
}
```
`porcentaje_avance` = `(total_donaciones / capacidad_esperada) * 100`. Es `0.0` si `capacidad_esperada` no está definida.

**Errores:**
- `404` — evento no encontrado

---

## Resumen de rutas

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/eventos/` | Crear evento + pedido EVENTO |
| `GET` | `/api/v1/eventos/` | Listar eventos del hospital |
| `GET` | `/api/v1/eventos/activo/` | Obtener evento activo |
| `PATCH` | `/api/v1/eventos/{evento_id}` | Editar evento |
| `PATCH` | `/api/v1/eventos/{evento_id}/finalizar` | Finalizar evento |
| `POST` | `/api/v1/eventos/{evento_id}/registrar-donacion` | Registrar donación por DNI |
| `GET` | `/api/v1/eventos/{evento_id}/donaciones` | Listar donaciones del evento |
| `GET` | `/api/v1/eventos/{evento_id}/pendientes-clasificacion` | Donaciones sin clasificar |
| `PATCH` | `/api/v1/registros-donacion/{registro_id}/clasificar` | Clasificar componente donado |
| `GET` | `/api/v1/eventos/{evento_id}/dashboard` | Dashboard del evento |

---

## Colecciones Firestore nuevas

| Colección | Descripción |
|-----------|-------------|
| `eventos` | Documentos de cada evento |
| `registros_donacion_evento` | Un documento por donación registrada en un evento |

Los pedidos tipo EVENTO se guardan en la colección `hospital_requests` existente con
`request_type = "EVENTO"`, `blood_group = "MULTIPLE"`, y los campos extra
`blood_groups: list[str]` y `factores_rh: list[str]`.
