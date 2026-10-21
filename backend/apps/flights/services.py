from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .errors import (
    CancellationReasonRequired,
    DepartureInPast,
    FlightCodeExhausted,
    FlightNotCancellable,
    FlightNotEditable,
    FlightNotFound,
    InvalidFlightCost,
    SameOriginDestination,
    UnauthorizedRoute,
)
from .models import (
    BitacoraVuelo,
    Ciudad,
    ClaseTiquete,
    EstadoSilla,
    EstadoVuelo,
    NoticiaVuelo,
    NotificacionAfectacion,
    Ruta,
    SecuenciaCodigoVuelo,
    Silla,
    TipoVuelo,
    Vuelo,
)


@transaction.atomic
def generar_codigo_vuelo() -> str:
    """Genera atómicamente un código de vuelo comercial único e inmutable (DEC-01).

    Prefijo de aerolínea configurable y consecutivo de 4 dígitos entre 0001 y 9999.
    """
    prefijo = getattr(settings, "AIRLINE_CODE_PREFIX", "XX")[:2].upper()
    secuencia, _ = SecuenciaCodigoVuelo.objects.select_for_update().get_or_create(
        prefijo=prefijo, defaults={"ultimo_consecutivo": 0}
    )
    if secuencia.ultimo_consecutivo >= 9999:
        raise FlightCodeExhausted()
    secuencia.ultimo_consecutivo += 1
    secuencia.save(update_fields=["ultimo_consecutivo"])
    return f"{prefijo}{secuencia.ultimo_consecutivo:04d}"


def calcular_llegada(
    fecha_salida, hora_salida, duracion_min: int, zona_origen: str, zona_destino: str
):
    """Calcula la llegada local y UTC a partir de la salida y zonas horarias IANA."""
    tz_origen = ZoneInfo(zona_origen)
    tz_destino = ZoneInfo(zona_destino)

    dt_salida_local = datetime.combine(fecha_salida, hora_salida).replace(tzinfo=tz_origen)
    salida_utc = dt_salida_local.astimezone(ZoneInfo("UTC"))

    llegada_utc = salida_utc + timedelta(minutes=duracion_min)
    dt_llegada_local = llegada_utc.astimezone(tz_destino)

    return (
        salida_utc,
        llegada_utc,
        dt_llegada_local.date(),
        dt_llegada_local.time().replace(microsecond=0),
    )


@transaction.atomic
def programar_vuelo(
    origen_id: int,
    destino_id: int,
    fecha_salida,
    hora_salida,
    costo_persona_economica: Decimal,
    costo_persona_primera: Decimal = None,
    actor=None,
    ip_origen: str = "",
) -> Vuelo:
    """CU-01 / HU-001: Programa un nuevo vuelo nacional o internacional."""
    if origen_id == destino_id:
        raise SameOriginDestination()

    try:
        origen = Ciudad.objects.get(pk=origen_id, activa=True)
        destino = Ciudad.objects.get(pk=destino_id, activa=True)
    except Ciudad.DoesNotExist:
        raise UnauthorizedRoute() from None

    try:
        ruta = Ruta.objects.select_related("origen", "destino").get(
            origen=origen, destino=destino, activa=True
        )
    except Ruta.DoesNotExist:
        raise UnauthorizedRoute() from None

    costo_persona_economica = Decimal(str(costo_persona_economica))
    if costo_persona_economica <= Decimal("0.00"):
        raise InvalidFlightCost()

    if costo_persona_primera is None:
        costo_persona_primera = (costo_persona_economica * Decimal("1.50")).quantize(
            Decimal("0.01")
        )
    else:
        costo_persona_primera = Decimal(str(costo_persona_primera))
        if costo_persona_primera <= Decimal("0.00"):
            raise InvalidFlightCost()

    salida_utc, llegada_utc, fecha_llegada, hora_llegada = calcular_llegada(
        fecha_salida=fecha_salida,
        hora_salida=hora_salida,
        duracion_min=ruta.duracion_min,
        zona_origen=origen.zona_horaria,
        zona_destino=destino.zona_horaria,
    )

    if salida_utc <= timezone.now():
        raise DepartureInPast()

    # Capacidades y distribución según reglas RN-12 y RN-13
    if ruta.tipo_vuelo == TipoVuelo.NACIONAL:
        capacidad_total = 150
        cupos_primera = 25
        cupos_economica = 125
    else:
        capacidad_total = 250
        cupos_primera = 50
        cupos_economica = 200

    codigo_vuelo = generar_codigo_vuelo()

    vuelo = Vuelo.objects.create(
        codigo_vuelo=codigo_vuelo,
        ruta=ruta,
        tipo_vuelo=ruta.tipo_vuelo,
        fecha_salida=fecha_salida,
        hora_salida=hora_salida,
        salida_utc=salida_utc,
        tiempo_vuelo_min=ruta.duracion_min,
        fecha_llegada=fecha_llegada,
        hora_llegada=hora_llegada,
        llegada_utc=llegada_utc,
        costo_persona_economica=costo_persona_economica,
        costo_persona_primera=costo_persona_primera,
        capacidad_total=capacidad_total,
        cupos_primera_clase=cupos_primera,
        cupos_economica=cupos_economica,
        cupos_disponibles_primera=cupos_primera,
        cupos_disponibles_economica=cupos_economica,
        estado=EstadoVuelo.PROGRAMADO,
        creado_por=actor,
    )

    # Generación del inventario de sillas
    sillas = []
    for num in range(1, capacidad_total + 1):
        clase = ClaseTiquete.PRIMERA_CLASE if num <= cupos_primera else ClaseTiquete.ECONOMICA
        sillas.append(
            Silla(
                vuelo=vuelo,
                numero_silla=num,
                clase=clase,
                estado=EstadoSilla.DISPONIBLE,
                espacio_extra=(clase == ClaseTiquete.PRIMERA_CLASE),
            )
        )
    Silla.objects.bulk_create(sillas)

    # Publicación automática de la noticia del vuelo (RF-ADM-14, CU-01)
    NoticiaVuelo.objects.create(
        vuelo=vuelo,
        titulo=f"Nuevo vuelo {vuelo.codigo_vuelo}: {origen.nombre} a {destino.nombre}",
        contenido=(
            f"Se ha programado el vuelo directo {vuelo.tipo_vuelo.lower()} {vuelo.codigo_vuelo} "
            f"con salida de {origen.nombre} ({vuelo.fecha_salida} a las {vuelo.hora_salida}) "
            f"y llegada a {destino.nombre} ({vuelo.fecha_llegada} a las {vuelo.hora_llegada}). "
            f"Cupos disponibles a partir de ${costo_persona_economica} COP."
        ),
        tipo="VUELO_PROGRAMADO",
        vigente=True,
    )

    # Registro en bitácora de auditoría (RNF-FIA-02, CU-01)
    BitacoraVuelo.objects.create(
        vuelo=vuelo,
        actor=actor,
        tipo_evento=BitacoraVuelo.Evento.PROGRAMACION,
        ip_origen=ip_origen,
        detalles={
            "codigo_vuelo": vuelo.codigo_vuelo,
            "origen": origen.nombre,
            "destino": destino.nombre,
            "salida_utc": salida_utc.isoformat(),
            "costo_economica": str(costo_persona_economica),
            "costo_primera": str(costo_persona_primera),
        },
    )

    return vuelo


@transaction.atomic
def editar_vuelo(
    vuelo_id: int,
    fecha_salida=None,
    hora_salida=None,
    costo_persona_economica=None,
    costo_persona_primera=None,
    actor=None,
    ip_origen: str = "",
) -> Vuelo:
    """CU-02 / HU-002: Modifica fecha, hora o costo por persona de un vuelo programado."""
    try:
        vuelo = (
            Vuelo.objects.select_for_update()
            .select_related("ruta__origen", "ruta__destino")
            .get(pk=vuelo_id)
        )
    except Vuelo.DoesNotExist:
        raise FlightNotFound() from None

    if vuelo.estado != EstadoVuelo.PROGRAMADO:
        raise FlightNotEditable()

    cambios = {}
    nueva_fecha = fecha_salida or vuelo.fecha_salida
    nueva_hora = hora_salida or vuelo.hora_salida

    if fecha_salida is not None or hora_salida is not None:
        salida_utc, llegada_utc, fecha_llegada, hora_llegada = calcular_llegada(
            fecha_salida=nueva_fecha,
            hora_salida=nueva_hora,
            duracion_min=vuelo.tiempo_vuelo_min,
            zona_origen=vuelo.ruta.origen.zona_horaria,
            zona_destino=vuelo.ruta.destino.zona_horaria,
        )
        if salida_utc <= timezone.now():
            raise DepartureInPast()

        cambios["salida_anterior"] = {
            "fecha": str(vuelo.fecha_salida),
            "hora": str(vuelo.hora_salida),
            "salida_utc": vuelo.salida_utc.isoformat(),
        }
        vuelo.fecha_salida = nueva_fecha
        vuelo.hora_salida = nueva_hora
        vuelo.salida_utc = salida_utc
        vuelo.fecha_llegada = fecha_llegada
        vuelo.hora_llegada = hora_llegada
        vuelo.llegada_utc = llegada_utc
        cambios["salida_nueva"] = {
            "fecha": str(nueva_fecha),
            "hora": str(nueva_hora),
            "salida_utc": salida_utc.isoformat(),
        }

    if costo_persona_economica is not None:
        nuevo_costo_eco = Decimal(str(costo_persona_economica))
        if nuevo_costo_eco <= Decimal("0.00"):
            raise InvalidFlightCost()
        cambios["costo_economica_anterior"] = str(vuelo.costo_persona_economica)
        vuelo.costo_persona_economica = nuevo_costo_eco
        cambios["costo_economica_nuevo"] = str(nuevo_costo_eco)

    if costo_persona_primera is not None:
        nuevo_costo_prim = Decimal(str(costo_persona_primera))
        if nuevo_costo_prim <= Decimal("0.00"):
            raise InvalidFlightCost()
        cambios["costo_primera_anterior"] = str(vuelo.costo_persona_primera)
        vuelo.costo_persona_primera = nuevo_costo_prim
        cambios["costo_primera_nuevo"] = str(nuevo_costo_prim)

    vuelo.save()

    # Si hubo cambios en horarios, registramos notificación de afectación (DEC-13, CU-02)
    if "salida_nueva" in cambios:
        NotificacionAfectacion.objects.create(
            vuelo=vuelo,
            destinatario="pasajeros@aerolinea.local",
            tipo_afectacion=NotificacionAfectacion.Tipo.REPROGRAMACION,
            motivo="Reprogramación de fecha y hora de salida del vuelo.",
            datos_adicionales=cambios,
        )

    BitacoraVuelo.objects.create(
        vuelo=vuelo,
        actor=actor,
        tipo_evento=BitacoraVuelo.Evento.EDICION,
        ip_origen=ip_origen,
        detalles=cambios,
    )

    return vuelo


@transaction.atomic
def cancelar_vuelo(
    vuelo_id: int, motivo: str, alternativa: str = "REINTEGRO", actor=None, ip_origen: str = ""
) -> Vuelo:
    """CU-03 / HU-003: Cancela un vuelo programado y gestiona afectaciones."""
    if not motivo or not motivo.strip():
        raise CancellationReasonRequired()

    try:
        vuelo = Vuelo.objects.select_for_update().get(pk=vuelo_id)
    except Vuelo.DoesNotExist:
        raise FlightNotFound() from None

    if vuelo.estado != EstadoVuelo.PROGRAMADO:
        raise FlightNotCancellable()

    vuelo.estado = EstadoVuelo.CANCELADO
    vuelo.motivo_cancelacion = motivo.strip()
    vuelo.cancelado_en = timezone.now()
    vuelo.cancelado_por = actor
    vuelo.cupos_disponibles_primera = 0
    vuelo.cupos_disponibles_economica = 0
    vuelo.save()

    # Retirar noticias asociadas para que dejen de presentarse (CU-03)
    vuelo.noticias.filter(vigente=True).update(vigente=False)

    # Registrar notificación persistente de cancelación (DEC-13)
    NotificacionAfectacion.objects.create(
        vuelo=vuelo,
        destinatario="pasajeros@aerolinea.local",
        tipo_afectacion=NotificacionAfectacion.Tipo.CANCELACION,
        motivo=motivo.strip(),
        datos_adicionales={"alternativa": alternativa},
    )

    BitacoraVuelo.objects.create(
        vuelo=vuelo,
        actor=actor,
        tipo_evento=BitacoraVuelo.Evento.CANCELACION,
        ip_origen=ip_origen,
        detalles={"motivo": motivo.strip(), "alternativa": alternativa},
    )

    return vuelo
