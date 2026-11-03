import random
import string
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.flights.models import ClaseTiquete, EstadoSilla, EstadoVuelo, Silla, TipoVuelo, Vuelo
from apps.wallets.services import debitar_para_compra, reembolsar_a_billetera

from .errors import (
    AdultPassengerRequired,
    CancellationWindowClosed,
    CheckinAlreadyConfirmed,
    DuplicatePassengerInFlight,
    FlightNotAvailableForSale,
    InsufficientSeats,
    PurchaseNotCancellable,
    ReservationNotActive,
    ReservationWindowClosed,
    SeatChangeLimitReached,
    SeatNotAvailable,
    TicketLimitExceeded,
)
from .models import (
    Compra,
    EstadoCompra,
    EstadoReserva,
    EstadoTiquete,
    Reserva,
    ReservaViajero,
    TipoTrayecto,
    Tiquete,
    Viajero,
)


def generar_localizador() -> str:
    """Genera un localizador alfanumérico aleatorio y único de 6 caracteres (DEC-02)."""
    caracteres = string.ascii_uppercase + string.digits
    for _ in range(10):
        candidato = "".join(random.choices(caracteres, k=6))
        if not Compra.objects.filter(localizador=candidato).exists():
            return candidato
    # Fallback con timestamp
    return "".join(random.choices(caracteres, k=6))


def generar_codigo_tiquete(localizador: str, indice: int) -> str:
    return f"{localizador}-{indice:02d}"


def calcular_limite_vigencia_reserva(
    vuelo: Vuelo, now=None
) -> tuple[timezone.datetime, timezone.datetime]:
    """Calcula la vigencia de una reserva conforme a DEC-07.

    margen_reserva = 1 hora para nacional; 3 horas para internacional
    limite_por_salida = salida_vigente - margen_reserva
    vence_en = min(now + 24 horas, limite_por_salida)
    """
    if now is None:
        now = timezone.now()

    margen_horas = 1 if vuelo.tipo_vuelo == TipoVuelo.NACIONAL else 3
    limite_por_salida = vuelo.salida_utc - timedelta(hours=margen_horas)
    vence_en = min(now + timedelta(hours=24), limite_por_salida)
    return limite_por_salida, vence_en


def contar_tiquetes_activos_cliente_en_vuelo(cliente, vuelo: Vuelo) -> int:
    """Cuenta tiquetes activos (reservas vigentes + compras confirmadas) del cliente en el vuelo."""
    # Reservas vigentes
    reservas_count = ReservaViajero.objects.filter(
        reserva__cliente=cliente,
        reserva__vuelo=vuelo,
        reserva__estado=EstadoReserva.VIGENTE,
    ).count()

    # Compras confirmadas
    compras_count = Tiquete.objects.filter(
        compra__cliente=cliente,
        vuelo=vuelo,
        estado=EstadoTiquete.ACTIVO,
    ).count()

    return reservas_count + compras_count


def obtener_o_crear_viajero(data: dict) -> Viajero:
    doc = str(data["documento"]).strip()
    viajero, _ = Viajero.objects.get_or_create(
        documento=doc,
        defaults={
            "tipo_documento": data.get("tipo_documento", "CC"),
            "nombres": data["nombres"].strip(),
            "apellidos": data["apellidos"].strip(),
            "fecha_nacimiento": data["fecha_nacimiento"],
            "genero": data.get("genero", "OTRO"),
            "telefono": data.get("telefono", "").strip(),
            "correo": data.get("correo", "").strip().lower(),
            "nombre_contacto": data.get("nombre_contacto", "").strip(),
            "telefono_contacto": data.get("telefono_contacto", "").strip(),
        },
    )
    return viajero


@transaction.atomic
def crear_reserva(
    cliente,
    vuelo_id: int,
    clase: str,
    viajeros_data: list[dict],
    tipo_trayecto: str = TipoTrayecto.UNICO,
    vuelo_regreso_id: int = None,
) -> Reserva:
    """CU-12: Permite al cliente apartar temporalmente cupos de un vuelo sin pago

    (DEC-07, DEC-08).
    """
    if not viajeros_data:
        raise InsufficientSeats()

    num_pasajeros = len(viajeros_data)
    if num_pasajeros > 5:
        raise TicketLimitExceeded()

    now = timezone.now()

    vuelo = Vuelo.objects.select_for_update().get(pk=vuelo_id)
    if vuelo.estado != EstadoVuelo.PROGRAMADO or vuelo.salida_utc <= now:
        raise FlightNotAvailableForSale()

    limite_por_salida, vence_en = calcular_limite_vigencia_reserva(vuelo, now)
    if now >= limite_por_salida:
        raise ReservationWindowClosed()

    # Comprobar límite de 5 tiquetes activos por cliente en el vuelo
    actuales = contar_tiquetes_activos_cliente_en_vuelo(cliente, vuelo)
    if actuales + num_pasajeros > 5:
        raise TicketLimitExceeded()

    # Verificar cupos en el vuelo
    if clase == ClaseTiquete.PRIMERA_CLASE:
        if vuelo.cupos_disponibles_primera < num_pasajeros:
            raise InsufficientSeats()
        vuelo.cupos_disponibles_primera -= num_pasajeros
    else:
        if vuelo.cupos_disponibles_economica < num_pasajeros:
            raise InsufficientSeats()
        vuelo.cupos_disponibles_economica -= num_pasajeros
    vuelo.save()

    # Validar que al menos un viajero sea mayor de edad en la fecha del vuelo
    vuelo_regreso = None
    if vuelo_regreso_id:
        vuelo_regreso = Vuelo.objects.select_for_update().get(pk=vuelo_regreso_id)
        if vuelo_regreso.estado != EstadoVuelo.PROGRAMADO or vuelo_regreso.salida_utc <= now:
            raise FlightNotAvailableForSale()
        # Verificar cupos en regreso
        if clase == ClaseTiquete.PRIMERA_CLASE:
            if vuelo_regreso.cupos_disponibles_primera < num_pasajeros:
                raise InsufficientSeats()
            vuelo_regreso.cupos_disponibles_primera -= num_pasajeros
        else:
            if vuelo_regreso.cupos_disponibles_economica < num_pasajeros:
                raise InsufficientSeats()
            vuelo_regreso.cupos_disponibles_economica -= num_pasajeros
        vuelo_regreso.save()

        # En ida y regreso el límite es el más temprano
        _, vence_regreso = calcular_limite_vigencia_reserva(vuelo_regreso, now)
        vence_en = min(vence_en, vence_regreso)

    # Procesar viajeros y validar unicidad
    viajeros = []
    documentos_vistos = set()
    al_menos_un_adulto = False

    for v_data in viajeros_data:
        doc = str(v_data["documento"]).strip()
        if doc in documentos_vistos:
            raise DuplicatePassengerInFlight()
        documentos_vistos.add(doc)

        viajero = obtener_o_crear_viajero(v_data)
        if viajero.es_mayor_de_edad(vuelo.fecha_salida):
            al_menos_un_adulto = True
        viajeros.append(viajero)

    if not al_menos_un_adulto:
        raise AdultPassengerRequired()

    reserva = Reserva.objects.create(
        cliente=cliente,
        vuelo=vuelo,
        vuelo_regreso=vuelo_regreso,
        tipo_trayecto=tipo_trayecto,
        clase=clase,
        limite_vigencia=vence_en,
        estado=EstadoReserva.VIGENTE,
    )

    for v in viajeros:
        ReservaViajero.objects.create(reserva=reserva, viajero=v)

    return reserva


@transaction.atomic
def liberar_reserva_si_vencida(reserva: Reserva) -> bool:
    """Libera transaccionalmente los cupos de una reserva si alcanzó su vigencia (DEC-07)."""
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    if reserva.estado != EstadoReserva.VIGENTE:
        return False

    if timezone.now() >= reserva.limite_vigencia:
        reserva.estado = EstadoReserva.VENCIDA
        reserva.save(update_fields=["estado"])

        num_viajeros = reserva.viajeros_reserva.count()
        vuelo = Vuelo.objects.select_for_update().get(pk=reserva.vuelo_id)
        if reserva.clase == ClaseTiquete.PRIMERA_CLASE:
            vuelo.cupos_disponibles_primera += num_viajeros
        else:
            vuelo.cupos_disponibles_economica += num_viajeros
        vuelo.save()

        if reserva.vuelo_regreso_id:
            v_reg = Vuelo.objects.select_for_update().get(pk=reserva.vuelo_regreso_id)
            if reserva.clase == ClaseTiquete.PRIMERA_CLASE:
                v_reg.cupos_disponibles_primera += num_viajeros
            else:
                v_reg.cupos_disponibles_economica += num_viajeros
            v_reg.save()

        return True
    return False


@transaction.atomic
def cancelar_reserva(reserva_id: int, cliente) -> Reserva:
    """CU-14 (Reserva): Cancela una reserva vigente y devuelve los cupos sin cobro."""
    reserva = Reserva.objects.select_for_update().get(pk=reserva_id)
    if reserva.cliente != cliente:
        raise ReservationNotActive()

    if reserva.estado != EstadoReserva.VIGENTE:
        raise ReservationNotActive()

    reserva.estado = EstadoReserva.CANCELADA
    reserva.save(update_fields=["estado"])

    num_viajeros = reserva.viajeros_reserva.count()
    vuelo = Vuelo.objects.select_for_update().get(pk=reserva.vuelo_id)
    if reserva.clase == ClaseTiquete.PRIMERA_CLASE:
        vuelo.cupos_disponibles_primera += num_viajeros
    else:
        vuelo.cupos_disponibles_economica += num_viajeros
    vuelo.save()

    if reserva.vuelo_regreso_id:
        v_reg = Vuelo.objects.select_for_update().get(pk=reserva.vuelo_regreso_id)
        if reserva.clase == ClaseTiquete.PRIMERA_CLASE:
            v_reg.cupos_disponibles_primera += num_viajeros
        else:
            v_reg.cupos_disponibles_economica += num_viajeros
        v_reg.save()

    return reserva


@transaction.atomic
def comprar_tiquetes(
    cliente,
    vuelo_id: int,
    clase: str,
    viajeros_data: list[dict] = None,
    reserva_id: int = None,
    tipo_trayecto: str = TipoTrayecto.UNICO,
    vuelo_regreso_id: int = None,
) -> Compra:
    """CU-13: Compra confirmada de tiquetes con débito en billetera y asignación

    de sillas (DEC-02, DEC-06, DEC-08, DEC-09).
    """
    now = timezone.now()
    reserva = None

    if reserva_id:
        reserva = Reserva.objects.select_for_update().get(pk=reserva_id)
        if reserva.cliente != cliente or reserva.estado != EstadoReserva.VIGENTE:
            raise ReservationNotActive()
        if now >= reserva.limite_vigencia:
            liberar_reserva_si_vencida(reserva)
            raise ReservationNotActive()

        vuelo = Vuelo.objects.select_for_update().get(pk=reserva.vuelo_id)
        clase = reserva.clase
        tipo_trayecto = reserva.tipo_trayecto
        vuelo_regreso = reserva.vuelo_regreso
        viajeros = [rv.viajero for rv in reserva.viajeros_reserva.select_related("viajero")]
        num_pasajeros = len(viajeros)
    else:
        if not viajeros_data:
            raise InsufficientSeats()
        num_pasajeros = len(viajeros_data)
        if num_pasajeros > 5:
            raise TicketLimitExceeded()

        vuelo = Vuelo.objects.select_for_update().get(pk=vuelo_id)
        if vuelo.estado != EstadoVuelo.PROGRAMADO or vuelo.salida_utc <= now:
            raise FlightNotAvailableForSale()

        # Verificar cupos
        if clase == ClaseTiquete.PRIMERA_CLASE:
            if vuelo.cupos_disponibles_primera < num_pasajeros:
                raise InsufficientSeats()
            vuelo.cupos_disponibles_primera -= num_pasajeros
        else:
            if vuelo.cupos_disponibles_economica < num_pasajeros:
                raise InsufficientSeats()
            vuelo.cupos_disponibles_economica -= num_pasajeros
        vuelo.save()

        vuelo_regreso = None
        if vuelo_regreso_id:
            vuelo_regreso = Vuelo.objects.select_for_update().get(pk=vuelo_regreso_id)
            if vuelo_regreso.estado != EstadoVuelo.PROGRAMADO or vuelo_regreso.salida_utc <= now:
                raise FlightNotAvailableForSale()
            if clase == ClaseTiquete.PRIMERA_CLASE:
                if vuelo_regreso.cupos_disponibles_primera < num_pasajeros:
                    raise InsufficientSeats()
                vuelo_regreso.cupos_disponibles_primera -= num_pasajeros
            else:
                if vuelo_regreso.cupos_disponibles_economica < num_pasajeros:
                    raise InsufficientSeats()
                vuelo_regreso.cupos_disponibles_economica -= num_pasajeros
            vuelo_regreso.save()

        # Procesar viajeros
        viajeros = []
        documentos_vistos = set()
        al_menos_un_adulto = False
        for v_data in viajeros_data:
            doc = str(v_data["documento"]).strip()
            if doc in documentos_vistos:
                raise DuplicatePassengerInFlight()
            documentos_vistos.add(doc)
            viajero = obtener_o_crear_viajero(v_data)
            if viajero.es_mayor_de_edad(vuelo.fecha_salida):
                al_menos_un_adulto = True
            viajeros.append(viajero)

        if not al_menos_un_adulto:
            raise AdultPassengerRequired()

    # Cálculo de precios vigentes (DEC-06)
    tarifa_vuelo = (
        vuelo.costo_persona_primera
        if clase == ClaseTiquete.PRIMERA_CLASE
        else vuelo.costo_persona_economica
    )
    total = tarifa_vuelo * num_pasajeros
    if vuelo_regreso:
        tarifa_regreso = (
            vuelo_regreso.costo_persona_primera
            if clase == ClaseTiquete.PRIMERA_CLASE
            else vuelo_regreso.costo_persona_economica
        )
        total += tarifa_regreso * num_pasajeros

    # Débito atómico en billetera (DEC-03, DEC-09)
    wallet = cliente.wallet
    localizador = generar_localizador()
    debitar_para_compra(
        wallet_id=wallet.pk,
        monto=total,
        referencia=f"Compra tiquetes localizador {localizador}",
    )

    compra = Compra.objects.create(
        cliente=cliente,
        localizador=localizador,
        valor_pagado=total,
        tipo_trayecto=tipo_trayecto,
        estado=EstadoCompra.CONFIRMADA,
        reserva_origen=reserva,
    )

    if reserva:
        reserva.estado = EstadoReserva.COMPRADA
        reserva.save(update_fields=["estado"])

    # Asignación aleatoria de sillas en vuelo de ida (DEC-08, RN-14)
    sillas_libres_ida = list(
        Silla.objects.select_for_update()
        .filter(vuelo=vuelo, clase=clase, estado=EstadoSilla.DISPONIBLE)
    )
    if len(sillas_libres_ida) < num_pasajeros:
        raise InsufficientSeats()

    sillas_asignadas_ida = random.sample(sillas_libres_ida, num_pasajeros)

    for idx, (viajero, silla) in enumerate(
        zip(viajeros, sillas_asignadas_ida, strict=False), start=1
    ):
        silla.estado = EstadoSilla.OCUPADA
        silla.save(update_fields=["estado"])

        Tiquete.objects.create(
            compra=compra,
            vuelo=vuelo,
            viajero=viajero,
            silla=silla,
            clase=clase,
            precio_pagado=tarifa_vuelo,
            codigo_tiquete=generar_codigo_tiquete(localizador, idx),
            estado=EstadoTiquete.ACTIVO,
        )

    # Si hay regreso, asignar sillas en regreso
    if vuelo_regreso:
        tarifa_reg = (
            vuelo_regreso.costo_persona_primera
            if clase == ClaseTiquete.PRIMERA_CLASE
            else vuelo_regreso.costo_persona_economica
        )
        sillas_libres_reg = list(
            Silla.objects.select_for_update()
            .filter(vuelo=vuelo_regreso, clase=clase, estado=EstadoSilla.DISPONIBLE)
        )
        if len(sillas_libres_reg) < num_pasajeros:
            raise InsufficientSeats()
        sillas_asignadas_reg = random.sample(sillas_libres_reg, num_pasajeros)

        for idx, (viajero, silla) in enumerate(
            zip(viajeros, sillas_asignadas_reg, strict=False), start=num_pasajeros + 1
        ):
            silla.estado = EstadoSilla.OCUPADA
            silla.save(update_fields=["estado"])

            Tiquete.objects.create(
                compra=compra,
                vuelo=vuelo_regreso,
                viajero=viajero,
                silla=silla,
                clase=clase,
                precio_pagado=tarifa_reg,
                codigo_tiquete=generar_codigo_tiquete(localizador, idx),
                estado=EstadoTiquete.ACTIVO,
            )

    return compra


@transaction.atomic
def cancelar_compra(compra_id: int, cliente) -> Compra:
    """CU-14 (Compra): Cancela voluntariamente una compra dentro del plazo legal.

    Reembolsa a la billetera (DEC-06, DEC-07, DEC-09).
    """
    compra = Compra.objects.select_for_update().get(pk=compra_id)
    if compra.cliente != cliente or compra.estado != EstadoCompra.CONFIRMADA:
        raise PurchaseNotCancellable()

    tiquetes = list(
        compra.tiquetes.filter(estado=EstadoTiquete.ACTIVO).select_related("vuelo", "silla")
    )
    if not tiquetes:
        raise PurchaseNotCancellable()

    now = timezone.now()

    # Validar plazo de cancelación voluntaria: 1 hora nacional / 3 horas internacional (§7.1)
    for t in tiquetes:
        margen = 1 if t.vuelo.tipo_vuelo == TipoVuelo.NACIONAL else 3
        limite_cancelacion = t.vuelo.salida_utc - timedelta(hours=margen)
        if now >= limite_cancelacion:
            raise CancellationWindowClosed()

    total_reembolso = Decimal("0.00")

    # Liberar sillas, devolver cupos y marcar tiquetes cancelados
    for t in tiquetes:
        silla = t.silla
        silla.estado = EstadoSilla.DISPONIBLE
        silla.save(update_fields=["estado"])

        vuelo = Vuelo.objects.select_for_update().get(pk=t.vuelo_id)
        if t.clase == ClaseTiquete.PRIMERA_CLASE:
            vuelo.cupos_disponibles_primera += 1
        else:
            vuelo.cupos_disponibles_economica += 1
        vuelo.save()

        t.estado = EstadoTiquete.CANCELADO
        t.save(update_fields=["estado"])

        total_reembolso += t.precio_pagado

    compra.estado = EstadoCompra.CANCELADA
    compra.fecha_cancelacion = now
    compra.save(update_fields=["estado", "fecha_cancelacion"])

    # Reembolso íntegro a la billetera del cliente comprador (DEC-09)
    reembolsar_a_billetera(
        wallet_id=cliente.wallet.pk,
        monto=total_reembolso,
        referencia=f"Reembolso por cancelación de compra {compra.localizador}",
    )

    return compra


@transaction.atomic
def reembolsar_tiquetes_por_cancelacion_vuelo(vuelo_id: int) -> int:
    """Procesa el reintegro automático de todos los tiquetes vendidos cuando un administrador

    cancela un vuelo (CU-03, §6.5).
    """
    tiquete_ids = list(
        Tiquete.objects.filter(vuelo_id=vuelo_id, estado=EstadoTiquete.ACTIVO).values_list(
            "id", flat=True
        )
    )
    if not tiquete_ids:
        return 0

    tiquetes = list(
        Tiquete.objects.select_for_update(of=("self",))
        .filter(id__in=tiquete_ids)
        .select_related("compra__cliente", "silla")
    )

    reembolsos_por_billetera = {}
    for t in tiquetes:
        wallet = t.compra.cliente.wallet
        reembolsos_por_billetera.setdefault(wallet.pk, Decimal("0.00"))
        reembolsos_por_billetera[wallet.pk] += t.precio_pagado

        # Liberar silla y marcar tiquete como cancelado
        t.silla.estado = EstadoSilla.DISPONIBLE
        t.silla.save(update_fields=["estado"])
        t.estado = EstadoTiquete.CANCELADO
        t.save(update_fields=["estado"])

    for wallet_id, monto in reembolsos_por_billetera.items():
        reembolsar_a_billetera(
            wallet_id=wallet_id,
            monto=monto,
            referencia=f"Reintegro por cancelación administrativa de vuelo #{vuelo_id}",
        )

    return len(tiquetes)


@transaction.atomic
def cambiar_silla_tiquete(tiquete_id: int, nueva_silla_id: int, actor) -> Tiquete:
    """CU-17: Permite al cliente/viajero cambiar por una única vez la silla asignada

    antes de check-in (RN-15).
    """
    tiquete = (
        Tiquete.objects.select_for_update()
        .select_related("compra", "vuelo", "silla")
        .get(pk=tiquete_id)
    )

    if tiquete.estado != EstadoTiquete.ACTIVO:
        raise SeatNotAvailable()

    # Si el check-in ya fue confirmado, no se admite cambio (CU-17 Flujo 2.a)
    if tiquete.checkin_confirmado:
        raise CheckinAlreadyConfirmed()

    # Máximo un único cambio permitido por tiquete (RN-15)
    if tiquete.numero_cambios_silla >= 1:
        raise SeatChangeLimitReached()

    # Obtener y validar la nueva silla
    nueva_silla = (
        Silla.objects.select_for_update()
        .filter(pk=nueva_silla_id, vuelo=tiquete.vuelo)
        .first()
    )
    if not nueva_silla:
        raise SeatNotAvailable()

    if nueva_silla.clase != tiquete.clase or nueva_silla.estado != EstadoSilla.DISPONIBLE:
        raise SeatNotAvailable()

    # Reasignación atómica: liberar anterior y ocupar nueva
    silla_anterior = tiquete.silla
    silla_anterior.estado = EstadoSilla.DISPONIBLE
    silla_anterior.save(update_fields=["estado"])

    nueva_silla.estado = EstadoSilla.OCUPADA
    nueva_silla.save(update_fields=["estado"])

    tiquete.silla = nueva_silla
    tiquete.numero_cambios_silla += 1
    tiquete.save(update_fields=["silla", "numero_cambios_silla"])

    return tiquete
