# VitFlow API — Referencia completa de endpoints

> **Audiencia:** equipo de frontend.  
> **Última actualización:** 2026-04-18  
> **Base URL:** `/api/v1`  
> **Autenticación:** todos los endpoints (salvo los marcados como públicos) requieren `Authorization: Bearer <firebase_id_token>`.

---

## Convenciones

- `hospital_id` **nunca** se envía desde el frontend. El backend lo lee del token.
- `user_id` tampoco se envía. Se infiere del token.
- Campos marcados como *opcional* pueden omitirse o enviarse como `null`.
- Fechas en formato `YYYY-MM-DD`. Timestamps en ISO 8601 UTC.

---

## Enums globales

| Enum | Valores |
|------|---------|
| `BloodGroup` | `A+` `A-` `B+` `B-` `AB+` `AB-` `O+` `O-` |
| `Componente` | `globulos_rojos` `plasma` `plaquetas` |
| `EstadoUnidad` | `disponible` `usado` `vencido` |
| `MotivoRetiro` | `transfusion` `trasplante` `operacion` `otro` |
| `AppointmentStatus` | `PROGRAMADO` `CONFIRMADO` `CANCELADO` `COMPLETADO` `NO_PRESENTADO` |
| `DonationType` | `SANGRE` `PLAQUETAS` `MEDULA_OSEA` |
| `HospitalRequestPriority` | `NORMAL` `URGENTE` `CRITICA` |
| `HospitalRequestStatus` | `ACTIVO` `COMPLETO` `CANCELADO` `FINALIZADO` |
| `HospitalRequestType` | `NORMAL` `CAMPAÑA` |
| `EligibilityStatus` | `APT` `WAIT` `NOT_APT` |
| `Gender` | `F` `M` `OTHER` |
| `UserRole` | `HOSPITAL_ADMIN` `TECHNICIAN` |
| `UserStatus` | `INVITED` `ACTIVE` `SUSPENDED` |
| `OnboardingStatus` | `SUBMITTED` `APPROVED` `REJECTED` |

---

## AUTH — `/auth`

---

### `POST /auth/register`

Registra un nuevo usuario en Firebase y Firestore.

**Auth:** no requerida.

**Request body:**
```json
{
  "email": "string (email válido, obligatorio)",
  "password": "string (min 6, max 128, obligatorio)",
  "full_name": "string (min 1, max 100, obligatorio)",
  "phone_number": "string (min 6, max 20, obligatorio)",
  "address": {
    "street": "string (min 1, max 100, obligatorio)",
    "number": "string (min 1, max 10, obligatorio)",
    "locality": "string (min 1, max 100, obligatorio)",
    "city": "string (min 1, max 100, obligatorio)",
    "province": "string (min 1, max 100, obligatorio)"
  }
}
```

**Response `201 Created`:**
```json
{
  "uid": "string",
  "email": "string | null",
  "firstName": "string | null",
  "lastName": "string | null",
  "phone": "string | null",
  "dni": "string | null",
  "role": "HOSPITAL_ADMIN | TECHNICIAN | null",
  "status": "INVITED | ACTIVE | SUSPENDED | null",
  "hospitalId": "string | null",
  "createdAt": "string | null"
}
```

---

### `GET /auth/me`

Devuelve el perfil básico del usuario autenticado.

**Response `200 OK`:** objeto `UserResponse` (mismo esquema que arriba).

---

### `GET /auth/me/full`

Devuelve el perfil completo del usuario autenticado (incluye datos de Firestore sin mapeo a schema fijo).

**Response `200 OK`:** objeto sin schema fijo, contiene todos los campos del documento `users/{uid}`.

---

## USERS — `/users`

---

### `GET /users`

Lista todos los usuarios del hospital del admin autenticado.

**Auth:** requiere rol `HOSPITAL_ADMIN`.

**Request body:** ninguno.

**Response `200 OK`:** lista de documentos de usuario (sin schema fijo).

---

### `GET /users/getByID/{uid}`

Obtiene un usuario por su UID de Firebase.

**Path param:** `uid` — UID del usuario.

**Request body:** ninguno.

**Response `200 OK`:** objeto `UserResponse`.

---

### `POST /users/technicians`

Crea un técnico para el hospital del admin autenticado.

**Auth:** requiere rol `HOSPITAL_ADMIN`.

**Request body:** objeto libre (`dict`). Campos típicos:
```json
{
  "email": "string (obligatorio)",
  "firstName": "string",
  "lastName": "string",
  "phone": "string"
}
```

**Response `200 OK`:** objeto del técnico creado (sin schema fijo).

---

### `POST /users/{uid}/resend-invitation`

Reenvía el email de invitación a un técnico.

**Auth:** requiere rol `HOSPITAL_ADMIN`.

**Path param:** `uid` — UID del técnico.

**Request body:** ninguno.

**Response `200 OK`:** confirmación (sin schema fijo).

---

### `PATCH /users/{uid}/status`

Cambia el estado de un usuario (`ACTIVE`, `SUSPENDED`, etc.).

**Auth:** requiere rol `HOSPITAL_ADMIN`.

**Path param:** `uid` — UID del usuario.

**Request body:**
```json
{
  "status": "INVITED | ACTIVE | SUSPENDED (obligatorio)"
}
```

**Response `200 OK`:** objeto actualizado (sin schema fijo).

---

## DONORS — `/donors`

---

### `POST /donors/validate-address`

Valida y geocodifica una dirección usando Google Geocoding API.

**Request body:**
```json
{
  "address_text": "string (min 5, max 180, obligatorio)"
}
```

**Response `200 OK`:**
```json
{
  "ok": true,
  "address_text": "string",
  "geo": { "lat": -34.6, "lng": -58.4 }
}
```
Si no se puede geocodificar: `"ok": false`, `"geo": null`.

---

### `POST /donors/`

Crea un nuevo donante.

**Request body:**
```json
{
  "first_name": "string (max 50, obligatorio)",
  "last_name": "string (max 50, obligatorio)",
  "dni": "string (min 6, max 15, obligatorio)",
  "email": "string (email, obligatorio)",
  "phone_number": "string (min 6, max 20, obligatorio)",
  "gender": "F | M | OTHER (obligatorio)",
  "birth_date": "YYYY-MM-DD (obligatorio)",
  "weight_kg": "float > 0, <= 300 (obligatorio)",
  "blood_group": "BloodGroup (obligatorio)",
  "address_text": "string (min 5, max 180, obligatorio)",
  "has_recent_tattoo": "bool (default false)",
  "last_tattoo_or_piercing_date": "YYYY-MM-DD (opcional)",
  "last_donation_date": "YYYY-MM-DD (opcional)",
  "medications": ["string"] | null,
  "is_subscribed": "bool (default true)",
  "has_consent": "bool (default true)",
  "is_enabled": "bool (default true)",
  "has_fever_or_infection": "bool (default false)",
  "has_active_fever_or_infection": "bool (opcional)",
  "infection_resolved_date": "YYYY-MM-DD (opcional)",
  "screening_updated_at": "string (opcional)",
  "is_currently_pregnant": "bool (opcional, solo si gender = F)",
  "is_pregnant": "bool (opcional, solo si gender = F, campo legacy)",
  "last_pregnancy_end_date": "YYYY-MM-DD (opcional, solo si gender = F)",
  "pregnancy_end_type": "VAGINAL_BIRTH | CESAREAN | NON_SPONTANEOUS_ABORTION (opcional, solo si gender = F)",
  "is_breastfeeding": "bool (opcional, solo si gender = F)"
}
```

> Todos los campos de embarazo/lactancia **deben ser null** si `gender != F`.

**Response `200 OK`:** objeto `Donor` completo (ver esquema en sección de respuestas).

---

### `GET /donors/`

Lista todos los donantes. Sin filtros.

**Request body:** ninguno.

**Response `200 OK`:** lista de objetos `Donor`.

---

### `GET /donors/by-dni/{dni}`

Busca un donante por DNI.

**Path param:** `dni` — número de documento.

**Request body:** ninguno.

**Response `200 OK`:** objeto `Donor` o `404` si no existe.

---

### `GET /donors/by-dni/{dni}/donation-opportunities`

Devuelve las oportunidades de donación cercanas al donante (hospitales con pedidos activos compatibles dentro del radio).

**Path param:** `dni`  
**Query params:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `radius_km` | float | `5.0` | Radio de búsqueda en km |

**Request body:** ninguno.

**Response `200 OK`:** lista de oportunidades (sin schema fijo).

---

### `GET /donors/by-dni/{dni}/campaigns`

Devuelve las campañas de donación activas relevantes para el donante.

**Path param:** `dni`

**Request body:** ninguno.

**Response `200 OK`:** lista de campañas (sin schema fijo).

---

### `GET /donors/by-blood-group/{blood_group}`

Lista donantes filtrados por grupo sanguíneo.

**Path param:** `blood_group` — valor del enum `BloodGroup`.

**Request body:** ninguno.

**Response `200 OK`:** lista de objetos `Donor`.

---

### `POST /donors/{donor_id}/evaluate-eligibility`

Evalúa y actualiza la elegibilidad del donante. Escribe `eligibility_status`, `eligibility_reasons` y `eligibility_available_from` en Firestore.

**Path param:** `donor_id`

**Request body:** ninguno.

**Response `200 OK`:** objeto con la elegibilidad actualizada (sin schema fijo).

---

### `GET /donors/{donor_id}`

Obtiene un donante por su ID de Firestore.

**Path param:** `donor_id`

**Request body:** ninguno.

**Response `200 OK`:** objeto `Donor`.

---

### `PATCH /donors/{donor_id}`

Actualiza datos del donante. Solo se envían los campos a modificar.

**Path param:** `donor_id`

**Request body** (todos opcionales):
```json
{
  "weight_kg": "float > 0, <= 300",
  "has_recent_tattoo": "bool",
  "last_tattoo_or_piercing_date": "YYYY-MM-DD",
  "last_donation_date": "YYYY-MM-DD",
  "address_text": "string (min 5, max 180)",
  "is_pregnant": "bool",
  "is_currently_pregnant": "bool",
  "last_pregnancy_end_date": "YYYY-MM-DD",
  "pregnancy_end_type": "VAGINAL_BIRTH | CESAREAN | NON_SPONTANEOUS_ABORTION",
  "is_breastfeeding": "bool",
  "medications": ["string"],
  "has_fever_or_infection": "bool",
  "has_active_fever_or_infection": "bool",
  "infection_resolved_date": "YYYY-MM-DD",
  "screening_updated_at": "string",
  "is_subscribed": "bool",
  "has_consent": "bool",
  "is_enabled": "bool"
}
```

**Response `200 OK`:** objeto `Donor` actualizado.

---

### `GET /donors/nearby-for-request/{request_id}`

Devuelve donantes cercanos al hospital que hizo el pedido, con grupo sanguíneo compatible y `eligibility_status = "APT"`. Solo incluye donantes con `has_consent = true` e `is_subscribed = true`.

**Path param:** `request_id`  
**Query params:**
| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `radius_km` | float | `5.0` | Radio de búsqueda en km |

**Request body:** ninguno.

**Response `200 OK`:**
```json
{
  "hospital_request_id": "string",
  "hospital_id": "string",
  "blood_group": "BloodGroup",
  "radius_km": 5.0,
  "total": 3,
  "donors": [
    {
      "id": "string",
      "first_name": "string",
      "last_name": "string",
      "dni": "string",
      "email": "string",
      "phone_number": "string",
      "blood_group": "BloodGroup",
      "eligibility_status": "APT",
      "distance_km": 2.3
    }
  ]
}
```

---

### `POST /donors/{donor_id}/reject-invitation`

Registra la respuesta de un donante a una invitación enviada por Vito (WhatsApp). Se llama en tres situaciones:

- El donante responde **"no puedo ahora"** → `reason: "not_now"`
- El donante responde **"no quiero más avisos"** → `reason: "opt_out"` (setea `is_subscribed = false`)
- Vito no recibe respuesta en 30 minutos → `reason: "no_response"` (solo registra el evento)

Persiste el evento en la colección `donor_invitations` de Firestore.

**Path param:** `donor_id`

**Request body:**
```json
{
  "hospital_request_id": "string (obligatorio)",
  "reason": "not_now | opt_out | no_response (obligatorio)",
  "notes": "string (opcional, max 500)"
}
```

**Response `200 OK`:**
```json
{
  "donor_id": "string",
  "hospital_request_id": "string",
  "reason": "not_now | opt_out | no_response",
  "recorded_at": "ISO 8601 datetime",
  "is_subscribed": true
}
```

> Si `reason = "opt_out"`, `is_subscribed` será `false` en la respuesta y el donante quedará excluido de futuras notificaciones.  
> Si `reason = "no_response"`, `is_subscribed` refleja el estado actual sin modificación.

---

## APPOINTMENTS — `/appointments`

---

### `GET /appointments/`

Lista todos los turnos del hospital del usuario autenticado.

**Request body:** ninguno.

**Response `200 OK`:** lista de objetos `Appointment` con su `id`.

---

### `GET /appointments/search/{desde}/{hasta}`

Lista turnos en un rango de fechas.

**Path params:**
| Param | Tipo | Descripción |
|-------|------|-------------|
| `desde` | date (`YYYY-MM-DD`) | Fecha de inicio (inclusive) |
| `hasta` | date (`YYYY-MM-DD`) | Fecha de fin (inclusive) |

**Request body:** ninguno.

**Response `200 OK`:** lista de turnos en el rango.

---

### `GET /appointments/window/months`

Devuelve los turnos en la ventana del mes actual y próximo.

**Request body:** ninguno.

**Response `200 OK`:** lista de turnos.

---

### `GET /appointments/by-dni/{dni}/active`

Devuelve el turno activo (estado `PROGRAMADO` o `CONFIRMADO`) de un donante por DNI.

**Path param:** `dni`

**Request body:** ninguno.

**Response `200 OK`:** objeto turno o `null` si no tiene turno activo.

---

### `GET /appointments/request/{request_id}/available-days`

Devuelve los días con disponibilidad para un pedido hospitalario dado.

**Path param:** `request_id`  
**Query params:**
| Param | Tipo | Default | Obligatorio | Descripción |
|-------|------|---------|-------------|-------------|
| `donor_id` | string | — | sí | ID del donante a reservar |
| `days_ahead` | int | `14` | no | Cuántos días hacia adelante buscar |
| `allow_existing_active` | bool | `false` | no | Si se permite reservar aunque el donante ya tenga turno activo |

**Request body:** ninguno.

**Response `200 OK`:** lista de fechas disponibles (strings `YYYY-MM-DD`).

---

### `GET /appointments/request/{request_id}/available-time-ranges`

Devuelve las franjas horarias disponibles para un día dado.

**Path param:** `request_id`  
**Query params:**
| Param | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `donor_id` | string | sí | ID del donante |
| `date_local` | date | sí | Fecha a consultar (`YYYY-MM-DD`) |
| `allow_existing_active` | bool | no (default `false`) | Ver arriba |

**Request body:** ninguno.

**Response `200 OK`:** lista de franjas horarias disponibles.

---

### `GET /appointments/request/{request_id}/available-slots`

Devuelve los slots (horarios exactos) disponibles para un día y franja.

**Path param:** `request_id`  
**Query params:**
| Param | Tipo | Default | Obligatorio | Descripción |
|-------|------|---------|-------------|-------------|
| `donor_id` | string | — | sí | ID del donante |
| `date_local` | date | — | sí | Fecha (`YYYY-MM-DD`) |
| `time_range` | string | null | no | Franja horaria, ej: `"09:00-12:00"` |
| `limit` | int | `8` | no | Máx resultados por página |
| `offset` | int | `0` | no | Paginación |
| `allow_existing_active` | bool | `false` | no | Ver arriba |

**Request body:** ninguno.

**Response `200 OK`:** lista paginada de slots disponibles.

---

### `GET /appointments/{appointment_id}`

Obtiene un turno por ID.

**Path param:** `appointment_id`

**Request body:** ninguno.

**Response `200 OK`:** objeto `Appointment` con todos sus campos.

---

### `POST /appointments/manual`

Crea un turno de forma manual (ingresado por el hospital).

**Request body:**
```json
{
  "hospital_request_id": "string (obligatorio)",
  "date_local": "YYYY-MM-DD (obligatorio)",
  "time_local": "HH:MM (obligatorio)",
  "donor": {
    "full_name": "string (max 100, obligatorio)",
    "dni": "string (min 6, max 10, obligatorio)"
  },
  "donation_type": "SANGRE | PLAQUETAS | MEDULA_OSEA (obligatorio)"
}
```

**Response `200 OK`:** objeto turno creado.

---

### `POST /appointments/vito`

Crea un turno generado por el chatbot Vito (WhatsApp).

**Request body:**
```json
{
  "donor_id": "string (obligatorio)",
  "hospital_request_id": "string (obligatorio)",
  "date_local": "YYYY-MM-DD (obligatorio)",
  "time_local": "HH:MM (obligatorio)"
}
```

**Response `200 OK`:** objeto turno creado.

---

### `PATCH /appointments/{appointment_id}/status`

Cambia el estado de un turno.

**Path param:** `appointment_id`

**Request body:**
```json
{
  "status": "PROGRAMADO | CONFIRMADO | CANCELADO | COMPLETADO | NO_PRESENTADO (obligatorio)"
}
```

**Response `200 OK`:** objeto turno actualizado.

---

### `PATCH /appointments/{appointment_id}/reschedule`

Reprograma un turno a una nueva fecha y hora.

**Path param:** `appointment_id`

**Request body:**
```json
{
  "date_local": "YYYY-MM-DD (obligatorio)",
  "time_local": "HH:MM (obligatorio)"
}
```

**Response `200 OK`:** objeto turno actualizado.

---

### `POST /appointments/{appointment_id}/confirmar-asistencia`

Marca la asistencia del donante: cambia el turno a `COMPLETADO` y crea una unidad de stock por cada componente seleccionado.

**Path param:** `appointment_id`

**Request body:**
```json
{
  "blood_group": "BloodGroup (obligatorio)",
  "componentes": ["globulos_rojos | plasma | plaquetas"] 
}
```
> `componentes` debe tener al menos 1 elemento.

**Response `200 OK`:**
```json
{
  "appointment_id": "string",
  "status": "COMPLETADO",
  "unidades_creadas": [
    {
      "id": "string",
      "componente": "string",
      "blood_group": "string",
      "fecha_vencimiento": "string",
      "estado": "disponible"
    }
  ]
}
```

---

## HOSPITAL REQUESTS — `/hospital-requests`

---

### `POST /hospital-requests/`

Crea un pedido de sangre del hospital.

**Request body:**
```json
{
  "hospital_unit": "ITU | Terapia Intensiva | Guardia | Quirofano | Clinica Medica (obligatorio)",
  "component": "string (max 100, obligatorio)",
  "blood_group": "string (min 2, max 4, obligatorio)",
  "requested_units": "float > 0, <= 20 (obligatorio)",
  "priority": "NORMAL | URGENTE | CRITICA (obligatorio)",
  "requested_by": "string (max 100, obligatorio)",
  "end_date": "string (ISO date/datetime, obligatorio)",
  "request_type": "NORMAL | CAMPAÑA (default: NORMAL)",
  "comments": "string (max 500, opcional)"
}
```

**Response `200 OK`:** objeto pedido creado.

---

### `GET /hospital-requests/`

Lista todos los pedidos del hospital del usuario autenticado.

**Request body:** ninguno.

**Response `200 OK`:** lista de pedidos con sus IDs.

---

### `PATCH /hospital-requests/{request_id}`

Actualiza campos de un pedido. Solo se envían los campos a modificar.

**Path param:** `request_id`

**Request body** (todos opcionales):
```json
{
  "hospital_unit": "ITU | Terapia Intensiva | Guardia | Quirofano | Clinica Medica",
  "priority": "NORMAL | URGENTE | CRITICA",
  "status": "ACTIVO | COMPLETO | CANCELADO | FINALIZADO",
  "comments": "string (max 500)",
  "request_type": "NORMAL | CAMPAÑA",
  "end_date": "string (min 10, max 40)"
}
```

**Response `200 OK`:** objeto pedido actualizado.

---

### `GET /hospital-requests/{request_id}`

Obtiene un pedido por ID.

**Path param:** `request_id`

**Request body:** ninguno.

**Response `200 OK`:** objeto pedido con todos sus campos.

---

## HOSPITAL AVAILABILITY — `/hospital-availability`

---

### `GET /hospital-availability`

Obtiene la configuración de disponibilidad semanal del hospital autenticado.

**Request body:** ninguno.

**Response `200 OK`:**
```json
{
  "id_hospital": "string",
  "days": [
    {
      "day": "Lunes | Martes | Miercoles | Jueves | Viernes | Sabado | Domingo",
      "enabled": true,
      "timeSlots": [
        { "time": "HH:MM", "capacity": 5 }
      ]
    }
  ]
}
```

---

### `PUT /hospital-availability`

Guarda (reemplaza completamente) la configuración de disponibilidad semanal.

**Request body:**
```json
{
  "days": [
    {
      "day": "Lunes | Martes | Miercoles | Jueves | Viernes | Sabado | Domingo (obligatorio)",
      "enabled": "bool (default false)",
      "timeSlots": [
        { "time": "HH:MM (obligatorio)", "capacity": "int >= 1 (obligatorio)" }
      ]
    }
  ]
}
```

> Deben enviarse los **7 días exactamente**, sin repetir. Los minutos de `time` deben ser múltiplos de 5.

**Response `200 OK`:** mismo esquema que el GET, con `id_hospital` incluido.

---

## BLOOD BANK — `/blood-bank`

> Modelo de stock agregado (sistema anterior). Sigue activo en paralelo al sistema de unidades por componente.

---

### `GET /blood-bank`

Devuelve el stock actual del banco de sangre del hospital.

**Request body:** ninguno.

**Response `200 OK`:**
```json
{
  "hospital_id": "string",
  "stocks_units": { "A+": 5, "A-": 2, ... },
  "thresholds_units": { "A+": 10, "A-": 4, ... }
}
```

---

### `PATCH /blood-bank/add-stock`

Suma unidades al stock de un grupo sanguíneo.

**Request body:**
```json
{
  "blood_type": "BloodGroup (obligatorio)",
  "amount_units": "int > 0, <= 5000000 (obligatorio)"
}
```

**Response `200 OK`:** objeto `BloodBankOut` actualizado.

---

### `PATCH /blood-bank/remove-stock`

Resta unidades al stock de un grupo sanguíneo.

**Request body:**
```json
{
  "blood_type": "BloodGroup (obligatorio)",
  "amount_units": "int > 0, <= 5000000 (obligatorio)"
}
```

**Response `200 OK`:** objeto `BloodBankOut` actualizado.

---

### `PATCH /blood-bank/thresholds`

Actualiza los umbrales mínimos del banco de sangre (modelo viejo).

**Request body:**
```json
{
  "thresholds_units": {
    "A+": 10, "A-": 5, "B+": 5, "B-": 3,
    "AB+": 2, "AB-": 2, "O+": 8, "O-": 4
  }
}
```

**Response `200 OK`:** objeto `BloodBankOut` actualizado.

---

## STOCK — `/stock`

> Sistema nuevo de stock por unidad física, separado por componente. Convive con `/blood-bank`.

---

### `GET /stock/totales`

Devuelve el conteo total de unidades disponibles del hospital, separado por componente.

**Request body:** ninguno.

**Response `200 OK`:**
```json
{
  "total": 45,
  "globulos_rojos": 20,
  "plasma": 15,
  "plaquetas": 10
}
```

---

### `GET /stock/dashboard/resumen`

Devuelve el resumen completo de stock disponible por componente y grupo sanguíneo. Los 8 grupos siempre están presentes aunque tengan 0.

**Request body:** ninguno.

**Response `200 OK`:**
```json
{
  "globulos_rojos": { "A+": 4, "A-": 1, "B+": 0, "B-": 2, "AB+": 0, "AB-": 0, "O+": 5, "O-": 1, "total": 13 },
  "plasma":         { "A+": 2, "A-": 0, "B+": 1, "B-": 0, "AB+": 0, "AB-": 0, "O+": 3, "O-": 2, "total": 8 },
  "plaquetas":      { "A+": 0, "A-": 0, "B+": 1, "B-": 0, "AB+": 0, "AB-": 0, "O+": 2, "O-": 0, "total": 3 }
}
```

---

### `GET /stock/umbrales`

Lista los umbrales mínimos de stock del hospital (24 umbrales: 3 componentes × 8 grupos).

**Request body:** ninguno.

**Response `200 OK`:** lista de `UmbralOut`:
```json
[
  {
    "id": "string",
    "hospital_id": "string",
    "componente": "globulos_rojos | plasma | plaquetas",
    "blood_group": "BloodGroup",
    "umbral_minimo": 5
  }
]
```

---

### `POST /stock/umbrales`

Crea o actualiza (upsert) un umbral para un componente + grupo sanguíneo.

**Request body:**
```json
{
  "componente": "globulos_rojos | plasma | plaquetas (obligatorio)",
  "blood_group": "BloodGroup (obligatorio)",
  "umbral_minimo": "int >= 0 (obligatorio)"
}
```

**Response `201 Created`:** objeto `UmbralOut`.

---

### `PATCH /stock/umbrales/{umbral_id}`

Modifica el valor mínimo de un umbral existente.

**Path param:** `umbral_id`

**Request body:**
```json
{
  "umbral_minimo": "int >= 0 (obligatorio)"
}
```

**Response `200 OK`:** objeto `UmbralOut`.

---

### `POST /stock/umbrales/inicializar`

Inicializa los 24 umbrales por defecto para el hospital. Solo crea los que no existen.

**Request body:** ninguno.

**Response `201 Created`:**
```json
{
  "hospital_id": "string",
  "umbrales_creados": 18,
  "umbrales_existentes": 6
}
```

---

### `GET /stock/historial`

Lista el historial de movimientos de stock (entradas y retiros), ordenado por fecha descendente.

**Query params** (todos opcionales):
| Param | Valores | Descripción |
|-------|---------|-------------|
| `componente` | `globulos_rojos` \| `plasma` \| `plaquetas` | Filtrar por componente |
| `accion` | `agrego` \| `retiro` | Filtrar por tipo de movimiento |
| `desde` | `YYYY-MM-DD` | Fecha de inicio (inclusive) |
| `hasta` | `YYYY-MM-DD` | Fecha de fin (inclusive) |

**Request body:** ninguno.

**Response `200 OK`:** lista de `HistorialOut`:
```json
[
  {
    "id": "string",
    "hospital_id": "string",
    "usuario_id": "string",
    "usuario_nombre": "string",
    "accion": "agrego | retiro",
    "componente": "Componente",
    "blood_group": "BloodGroup",
    "unidades_ids": ["string"],
    "cantidad": 2,
    "motivo": "transfusion | trasplante | operacion | otro | null",
    "motivo_detalle": "string | null",
    "fecha": "ISO 8601 datetime"
  }
]
```

---

### `POST /stock/{componente}`

Crea una sola unidad de un componente.

**Path param:** `componente` — `globulos_rojos`, `plasma` o `plaquetas`.

**Request body:**
```json
{
  "blood_group": "BloodGroup (obligatorio)",
  "turno_id": "string (opcional)",
  "donante_id": "string (opcional)"
}
```

**Response `201 Created`:** objeto `UnidadOut`:
```json
{
  "id": "string",
  "hospital_id": "string",
  "blood_group": "BloodGroup",
  "fecha_creacion": "ISO 8601 datetime",
  "fecha_vencimiento": "ISO 8601 datetime",
  "estado": "disponible",
  "turno_id": "string | null",
  "donante_id": "string | null",
  "motivo": null,
  "motivo_detalle": null
}
```

> Vida útil automática: `globulos_rojos` 42 días, `plasma` 365 días, `plaquetas` 5 días.

---

### `POST /stock/{componente}/agregar`

Crea una o más unidades del mismo componente y grupo sanguíneo en una operación. Registra historial automáticamente.

**Path param:** `componente`

**Request body:**
```json
{
  "blood_group": "BloodGroup (obligatorio)",
  "cantidad": "int >= 1, <= 100 (default: 1)"
}
```

**Response `201 Created`:** array de `UnidadOut`.

---

### `GET /stock/{componente}`

Lista todas las unidades de un componente del hospital. Filtros opcionales.

**Path param:** `componente`

**Query params** (opcionales):
| Param | Descripción |
|-------|-------------|
| `blood_group` | Filtrar por grupo sanguíneo |
| `estado` | `disponible` \| `usado` \| `vencido` |

**Request body:** ninguno.

**Response `200 OK`:** lista de `UnidadOut`.

---

### `GET /stock/{componente}/resumen`

Resumen de unidades disponibles por grupo sanguíneo para un componente. Solo incluye grupos con stock > 0.

**Path param:** `componente`

**Request body:** ninguno.

**Response `200 OK`:**
```json
{
  "hospital_id": "string",
  "componente": "globulos_rojos | plasma | plaquetas",
  "disponibles_por_grupo": { "A+": 4, "O-": 1 }
}
```

---

### `GET /stock/{componente}/disponibles`

Lista solo las unidades con `estado = "disponible"`. Filtro opcional por grupo.

**Path param:** `componente`

**Query params** (opcionales):
| Param | Descripción |
|-------|-------------|
| `blood_group` | Filtrar por grupo sanguíneo (`O%2B` para `O+`) |

**Request body:** ninguno.

**Response `200 OK`:** lista de `UnidadOut`.

---

### `PATCH /stock/{componente}/retirar`

Retira múltiples unidades en una sola operación. Todas pasan a `estado = "usado"`. Registra historial automáticamente.

**Path param:** `componente`

**Request body:**
```json
{
  "unidad_ids": ["string"] ,
  "motivo": "transfusion | trasplante | operacion | otro (opcional)",
  "motivo_detalle": "string (obligatorio si motivo = 'otro')"
}
```

**Response `200 OK`:** lista de `UnidadOut` con `estado: "usado"`.

> Si algún ID no existe o pertenece a otro hospital → `404` / `403`.

---

### `GET /stock/{componente}/{unidad_id}`

Obtiene una unidad por ID.

**Path params:** `componente`, `unidad_id`

**Request body:** ninguno.

**Response `200 OK`:** objeto `UnidadOut` o `404`.

---

### `PATCH /stock/{componente}/{unidad_id}`

Actualiza el estado de una unidad (genérico).

**Path params:** `componente`, `unidad_id`

**Request body:**
```json
{ "estado": "disponible | usado | vencido (obligatorio)" }
```

**Response `200 OK`:** objeto `UnidadOut`.

---

### `PATCH /stock/{componente}/{unidad_id}/retirar`

Marca una unidad como `"usado"`. Verifica que pertenezca al hospital del token.

**Path params:** `componente`, `unidad_id`

**Request body** (opcional):
```json
{
  "motivo": "transfusion | trasplante | operacion | otro",
  "motivo_detalle": "string (obligatorio si motivo = 'otro')"
}
```

**Response `200 OK`:** objeto `UnidadOut` con `estado: "usado"`.

> Este endpoint individual **no genera historial automático**. Para historial usar `PATCH /{componente}/retirar` (bulk).

---

### `PATCH /stock/{componente}/{unidad_id}/vencer`

Marca una unidad como `"vencido"`.

**Path params:** `componente`, `unidad_id`

**Request body:** ninguno.

**Response `200 OK`:** objeto `UnidadOut` con `estado: "vencido"`.

---

### `DELETE /stock/{componente}/{unidad_id}`

Elimina una unidad de Firestore.

**Path params:** `componente`, `unidad_id`

**Request body:** ninguno.

**Response `204 No Content`:** sin body.

---

## DONACIONES — `/donaciones`

---

### `POST /donaciones/confirmar`

Confirma la asistencia de un donante y registra los componentes obtenidos. Crea una unidad por cada componente seleccionado. **No modifica el estado del turno.**

**Request body:**
```json
{
  "turno_id": "string (obligatorio)",
  "donante_id": "string (obligatorio)",
  "blood_group": "BloodGroup (obligatorio)",
  "componentes": ["globulos_rojos | plasma | plaquetas"]
}
```
> `componentes` debe tener al menos 1 elemento. `hospital_id` **no va en el body**.

**Response `201 Created`:**
```json
{
  "turno_id": "string",
  "donante_id": "string",
  "unidades_creadas": [
    {
      "id": "string",
      "hospital_id": "string",
      "blood_group": "BloodGroup",
      "fecha_creacion": "ISO 8601 datetime",
      "fecha_vencimiento": "ISO 8601 datetime",
      "estado": "disponible",
      "turno_id": "string",
      "donante_id": "string",
      "motivo": null,
      "motivo_detalle": null
    }
  ]
}
```

---

## HOME — `/home`

---

### `GET /home/summary`

Devuelve el resumen principal del dashboard del hospital.

**Request body:** ninguno.

**Response `200 OK`:**
```json
{
  "stocks": { "A+": 12, "A-": 3, "B+": 0, ... },
  "thresholds": { "A+": 10, "A-": 5, "B+": 5, ... },
  "kpis": {
    "totalUnits": 30,
    "urgentActive": 2,
    "appointmentsToday": 5,
    "criticalGroupsCount": 3
  },
  "appointments": [
    { "time_local": "09:00", "donation_type": "SANGRE", "status": "PROGRAMADO" }
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
| `stocks` / `thresholds` | Modelo viejo de blood-bank (stock agregado por grupo) |
| `kpis.totalUnits` | Suma del stock viejo |
| `kpis.urgentActive` | Pedidos activos con prioridad `URGENTE` o `CRITICA` |
| `kpis.appointmentsToday` | Turnos de hoy con estado `PROGRAMADO` o `CONFIRMADO` |
| `kpis.criticalGroupsCount` | Grupos por debajo de su umbral |
| `appointments` | Turnos de hoy y mañana, ordenados por hora |
| `activeRequests` | Todos los pedidos activos del hospital |

---

## HOSPITAL ONBOARDING — `/hospital-onboarding`

> Endpoints públicos (sin autenticación requerida).

---

### `POST /hospital-onboarding/`

Crea una solicitud de registro de un nuevo hospital.

**Auth:** ninguna.

**Request body:**
```json
{
  "hospital": {
    "name": "string (min 3, max 120, obligatorio)",
    "email": "string (email, obligatorio)",
    "phone": "string (min 6, max 20, obligatorio)",
    "logoFile": "string (opcional)",
    "address": {
      "province": "string (min 2, max 80, obligatorio)",
      "localidad": "string (min 2, max 80, obligatorio)",
      "city": "string (min 2, max 80, obligatorio)",
      "street": "string (min 2, max 120, obligatorio)",
      "number": "string (min 1, max 10, obligatorio)",
      "provinceId": "string (obligatorio)",
      "localidadId": "string (obligatorio)"
    }
  },
  "admin": {
    "firstName": "string (min 2, max 40, obligatorio)",
    "lastName": "string (min 2, max 40, obligatorio)",
    "email": "string (email, obligatorio)",
    "phone": "string (min 6, max 20, obligatorio)",
    "dni": "string (7-8 dígitos, obligatorio)"
  },
  "status": "SUBMITTED | APPROVED | REJECTED (obligatorio)",
  "createdAt": "string (obligatorio)",
  "updatedAt": "string (obligatorio)"
}
```

**Response `200 OK`:** objeto de la solicitud creada.

---

### `GET /hospital-onboarding/`

Lista todas las solicitudes de onboarding (backoffice).

**Auth:** ninguna.

**Request body:** ninguno.

**Response `200 OK`:** lista de solicitudes.

---

### `PATCH /hospital-onboarding/{request_id}`

Aprueba o rechaza una solicitud de onboarding (backoffice).

**Auth:** ninguna.

**Path param:** `request_id`

**Request body:**
```json
{
  "status": "SUBMITTED | APPROVED | REJECTED (obligatorio)",
  "reviewedBy": "string (opcional)",
  "reviewedAt": "string (opcional)",
  "reviewNote": "string (opcional)"
}
```

**Response `200 OK`:** objeto de la solicitud actualizada.

---

## Notas de seguridad

- **`hospital_id`** nunca se envía desde el frontend. El backend lo extrae del token en cada request.
- **`donor_id`** sí se envía en los endpoints de disponibilidad de turnos y en `/appointments/vito`, porque identifica a otra persona (el donante), no al usuario autenticado.
- En endpoints PATCH/DELETE de stock, el backend verifica que el recurso pertenezca al hospital del usuario antes de modificarlo → `403` si no.

## Vida útil por componente

| Componente | Días |
|------------|------|
| `globulos_rojos` | 42 |
| `plasma` | 365 |
| `plaquetas` | 5 ← muy corto, priorizar alertas |

## Codificación de `+` en URLs

Al usar grupos como `A+`, `O+` en query params, codificar el `+` como `%2B`.  
Ejemplo: `?blood_group=O%2B`.
