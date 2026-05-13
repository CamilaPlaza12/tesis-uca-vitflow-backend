from pydantic import BaseModel, Field, model_validator
from typing import Dict, List, Literal, Optional
from datetime import datetime

BloodGroup = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
Componente = Literal["globulos_rojos", "plasma", "plaquetas"]
EstadoUnidad = Literal["disponible", "usado", "vencido"]
MotivoRetiro = Literal["transfusion", "trasplante", "operacion", "otro"]

# Vida útil en días por componente
VIDA_UTIL_DIAS: Dict[str, int] = {
    "globulos_rojos": 42,
    "plasma": 365,
    "plaquetas": 5,
}


# ─── Unidades de componente ───────────────────────────────────────────────────

class UnidadCreate(BaseModel):
    """Body para crear una unidad. hospital_id se lee del token, no del body."""
    blood_group: BloodGroup
    turno_id: Optional[str] = None
    donante_id: Optional[str] = None


class UnidadPatch(BaseModel):
    estado: EstadoUnidad


class AgregarRequest(BaseModel):
    """Body para agregar una o más unidades en una sola operación. hospital_id se lee del token."""
    blood_group: BloodGroup
    cantidad: int = Field(1, ge=1, le=100)


class RetirarRequest(BaseModel):
    motivo: Optional[MotivoRetiro] = None
    motivo_detalle: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def check_detalle_requerido(self):
        if self.motivo == "otro" and not (self.motivo_detalle or "").strip():
            raise ValueError("motivo_detalle es obligatorio cuando motivo es 'otro'")
        return self


class RetirarBulkRequest(BaseModel):
    """Body para retirar múltiples unidades en una sola operación."""
    unidad_ids: List[str] = Field(..., min_length=1)
    motivo: Optional[MotivoRetiro] = None
    motivo_detalle: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def check_detalle_requerido(self):
        if self.motivo == "otro" and not (self.motivo_detalle or "").strip():
            raise ValueError("motivo_detalle es obligatorio cuando motivo es 'otro'")
        return self


class UnidadOut(BaseModel):
    id: str
    hospital_id: str
    blood_group: BloodGroup
    fecha_creacion: datetime
    fecha_vencimiento: datetime
    estado: EstadoUnidad
    turno_id: Optional[str] = None
    donante_id: Optional[str] = None
    motivo: Optional[MotivoRetiro] = None
    motivo_detalle: Optional[str] = None


# ─── Resumen por grupo sanguíneo ──────────────────────────────────────────────

class ResumenOut(BaseModel):
    hospital_id: str
    componente: Componente
    disponibles_por_grupo: Dict[str, int]


# ─── Umbrales ─────────────────────────────────────────────────────────────────

class UmbralCreate(BaseModel):
    """Body para crear/actualizar umbral. hospital_id se lee del token, no del body."""
    componente: Componente
    blood_group: BloodGroup
    umbral_minimo: int = Field(..., ge=0)


class UmbralPatch(BaseModel):
    umbral_minimo: int = Field(..., ge=0)


class UmbralOut(BaseModel):
    id: str
    hospital_id: str
    componente: Componente
    blood_group: BloodGroup
    umbral_minimo: int


class InicializarUmbralesOut(BaseModel):
    hospital_id: str
    umbrales_creados: int
    umbrales_existentes: int


# ─── Dashboard ────────────────────────────────────────────────────────────────

class ComponenteResumen(BaseModel):
    """Conteo de unidades disponibles por grupo sanguíneo + total."""
    A_pos: int = Field(0, alias="A+")
    A_neg: int = Field(0, alias="A-")
    B_pos: int = Field(0, alias="B+")
    B_neg: int = Field(0, alias="B-")
    AB_pos: int = Field(0, alias="AB+")
    AB_neg: int = Field(0, alias="AB-")
    O_pos: int = Field(0, alias="O+")
    O_neg: int = Field(0, alias="O-")
    total: int = 0

    model_config = {"populate_by_name": True}


class DashboardResumenOut(BaseModel):
    globulos_rojos: Dict[str, int]
    plasma: Dict[str, int]
    plaquetas: Dict[str, int]


# ─── Historial de movimientos ────────────────────────────────────────────────

class HistorialOut(BaseModel):
    id: str
    hospital_id: str
    usuario_id: str
    usuario_nombre: str
    accion: Literal["agrego", "retiro"]
    componente: Componente
    blood_group: BloodGroup
    unidades_ids: List[str]
    cantidad: int
    motivo: Optional[MotivoRetiro] = None
    motivo_detalle: Optional[str] = None
    fecha: datetime


# ─── Totales disponibles ─────────────────────────────────────────────────────

class TotalesOut(BaseModel):
    total: int
    globulos_rojos: int
    plasma: int
    plaquetas: int


# ─── Donaciones ───────────────────────────────────────────────────────────────

class ConfirmarDonacionRequest(BaseModel):
    """Body para confirmar donación. hospital_id se lee del token, no del body."""
    turno_id: str
    donante_id: str
    blood_group: BloodGroup
    componentes: list[Componente] = Field(..., min_length=1)


class ConfirmarDonacionOut(BaseModel):
    turno_id: str
    donante_id: str
    unidades_creadas: list[UnidadOut]
