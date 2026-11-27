from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.sales.locking import inventory_transaction
from apps.sales.rules import administrator_required, money

from .errors import (
    DepartureInPast,
    DuplicateRoute,
    FlightCodeExhausted,
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
    Ruta,
    SecuenciaCodigoVuelo,
    Silla,
    TipoVuelo,
    Vuelo,
)


@inventory_transaction
def generar_codigo_vuelo() -> str:
    """Genera atómicamente un código de vuelo comercial único e inmutable (DEC-01).

    Prefijo de aerolínea configurable y consecutivo de 4 dígitos entre 0001 y 9999.
    """
    prefijo = getattr(settings, "AIRLINE_CODE_PREFIX", "XX").upper()
    if len(prefijo) != 2 or not prefijo.isascii() or not prefijo.isalnum():
        raise ValidationError("Prefijo de aerolínea inválido.")
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

    naive = datetime.combine(fecha_salida, hora_salida)
    candidates = [naive.replace(tzinfo=tz_origen, fold=fold) for fold in (0, 1)]
    valid = [
        d
        for d in candidates
        if d.astimezone(ZoneInfo("UTC")).astimezone(tz_origen).replace(tzinfo=None) == naive
    ]
    if not valid or len({d.utcoffset() for d in valid}) > 1:
        raise ValidationError("La hora local es inexistente o ambigua; elige otra hora.")
    dt_salida_local = valid[0]
    salida_utc = dt_salida_local.astimezone(ZoneInfo("UTC"))

    llegada_utc = salida_utc + timedelta(minutes=duracion_min)
    dt_llegada_local = llegada_utc.astimezone(tz_destino)

    return (
        salida_utc,
        llegada_utc,
        dt_llegada_local.date(),
        dt_llegada_local.time().replace(microsecond=0),
    )


@inventory_transaction
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

    administrator_required(actor)
    try:
        costo_persona_economica = money(costo_persona_economica)
        costo_persona_primera = money(costo_persona_primera)
    except ValidationError:
        raise InvalidFlightCost() from None

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


@inventory_transaction
def editar_vuelo(
    vuelo_id: int,
    fecha_salida=None,
    hora_salida=None,
    costo_persona_economica=None,
    costo_persona_primera=None,
    actor=None,
    ip_origen: str = "",
    motivo: str = "",
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

    administrator_required(actor)
    if not motivo.strip():
        raise ValidationError({"motivo": "Indica el motivo de la edición."})
    cambios = {"motivo": motivo.strip()}
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
        try:
            nuevo_costo_eco = money(costo_persona_economica)
        except ValidationError:
            raise InvalidFlightCost() from None
        if nuevo_costo_eco <= Decimal("0.00"):
            raise InvalidFlightCost()
        cambios["costo_economica_anterior"] = str(vuelo.costo_persona_economica)
        vuelo.costo_persona_economica = nuevo_costo_eco
        cambios["costo_economica_nuevo"] = str(nuevo_costo_eco)

    if costo_persona_primera is not None:
        try:
            nuevo_costo_prim = money(costo_persona_primera)
        except ValidationError:
            raise InvalidFlightCost() from None
        if nuevo_costo_prim <= Decimal("0.00"):
            raise InvalidFlightCost()
        cambios["costo_primera_anterior"] = str(vuelo.costo_persona_primera)
        vuelo.costo_persona_primera = nuevo_costo_prim
        cambios["costo_primera_nuevo"] = str(nuevo_costo_prim)

    vuelo.save()

    from .operations import propagate_edit

    propagate_edit(vuelo, cambios, actor)

    BitacoraVuelo.objects.create(
        vuelo=vuelo,
        actor=actor,
        tipo_evento=BitacoraVuelo.Evento.EDICION,
        ip_origen=ip_origen,
        detalles=cambios,
    )

    return vuelo


@inventory_transaction
def cancelar_vuelo(vuelo_id, motivo, alternativa="REINTEGRO", actor=None, ip_origen=""):
    from .operations import cancel_flight

    return cancel_flight(vuelo_id, motivo, alternativa, actor, ip_origen)


@inventory_transaction
def crear_ruta(*, origen_id: int, destino_id: int, tipo_vuelo: str, duracion_min: int) -> Ruta:
    """Registra una ruta en el catálogo validando las reglas de autorización."""
    if origen_id == destino_id:
        raise SameOriginDestination()

    try:
        origen = Ciudad.objects.get(pk=origen_id, activa=True)
        destino = Ciudad.objects.get(pk=destino_id, activa=True)
    except Ciudad.DoesNotExist:
        raise UnauthorizedRoute() from None

    if tipo_vuelo == TipoVuelo.NACIONAL:
        if not (
            origen.codigo_pais == "CO"
            and origen.es_capital_principal
            and destino.codigo_pais == "CO"
            and destino.es_capital_principal
        ):
            raise UnauthorizedRoute()
    else:  # INTERNACIONAL
        if not origen.origen_internacional or not destino.destino_internacional:
            raise UnauthorizedRoute()

    if Ruta.objects.filter(origen=origen, destino=destino).exists():
        raise DuplicateRoute()

    return Ruta.objects.create(
        origen=origen,
        destino=destino,
        tipo_vuelo=tipo_vuelo,
        duracion_min=duracion_min,
    )
