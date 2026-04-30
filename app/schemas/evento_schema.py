from datetime import date, time
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

EstadoEvento = Literal["ACTIVO", "FINALIZADO", "CANCELADO"]
ComponenteDonado = Literal["SANGRE_ENTERA", "PLASMA", "PLAQUETAS", "GLOBULOS_ROJOS"]


class EventoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    fecha: date
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    lugar: Optional[str] = Field(None, max_length=300)
    capacidad_esperada: Optional[int] = Field(None, ge=1)
    grupos_sanguineos: List[str] = Field(..., min_length=1)
    factores_rh: List[str] = Field(..., min_length=1)


class EventoOut(BaseModel):
    id: str
    nombre: str
    fecha: str
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    lugar: Optional[str] = None
    capacidad_esperada: Optional[int] = None
    estado: EstadoEvento
    pedido_id: str
    created_at: str


class EventoListItem(BaseModel):
    id: str
    nombre: str
    fecha: str
    lugar: Optional[str] = None
    estado: EstadoEvento
    total_donaciones: int


class EventoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    fecha: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    lugar: Optional[str] = Field(None, max_length=300)
    capacidad_esperada: Optional[int] = Field(None, ge=1)


class RegistrarDonacionRequest(BaseModel):
    dni: str = Field(..., min_length=1, max_length=20)


class RegistroDonacionOut(BaseModel):
    turno_id: str
    donante_dni: str
    donante_nombre: Optional[str] = None
    status: str
    date_local: Optional[str] = None
    time_local: Optional[str] = None


class RegistrarDonacionResponse(BaseModel):
    turno_id: str
    donante_dni: str
    donante_nombre: Optional[str] = None
    status: str
    mensaje: str


class FinalizarEventoResponse(BaseModel):
    id: str
    estado: EstadoEvento
    mensaje: str


class DashboardOut(BaseModel):
    evento_id: str
    nombre: str
    fecha: str
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    lugar: Optional[str] = None
    estado: EstadoEvento
    capacidad_esperada: Optional[int] = None
    total_donaciones_registradas: int
    pendientes_clasificacion: int
    porcentaje_avance: float
    por_componente: dict
