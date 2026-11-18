import random
import string
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.flights.models import ClaseTiquete, EstadoSilla, EstadoVuelo, Silla, TipoVuelo, Vuelo
from apps.wallets.services import debitar_para_compra, reembolsar_a_billetera

from .errors import (
    AdultPassengerRequired,
    CancellationWindowClosed,
    CartEmpty,
    CartItemNotFound,
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
    Carrito,
    Compra,
    EstadoCompra,
    EstadoReserva,
    EstadoTiquete,
    ItemCarrito,
    NotificacionCompra,
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


def resolver_precio_vigente(vuelo: Vuelo, clase: str, fecha=None) -> Decimal:
    """Punto único de consulta del precio por persona para búsqueda, carrito y compra (DEC-06).

    Hoy retorna la tarifa base vigente del vuelo según la clase; `fecha` se acepta
    ya para el contrato de promociones y por ahora no altera el resultado.

    Contrato para HU-004 (promociones): HU-004 debe resolver aquí la promoción
    activa aplicable a (vuelo, clase) en `fecha` y retornar el precio promocional
    — positivo e inferior a la tarifa base (§6.3) — en lugar de la tarifa base.
    La política de selección ante promociones superpuestas, la elegibilidad de
    reservas previas y el significado de `cupos_afectados` siguen pendientes en
    P-04: hasta resolverlos no se implementa ningún algoritmo de selección de
    promociones. Búsqueda, carrito y compra deben obtener el precio solo desde
    esta función, de modo que las promociones se apliquen automáticamente y de
    forma consistente en los tres flujos. El `precio_pagado` de cada tiquete se
    conserva con el valor resuelto al confirmar; nunca se recalcula (DEC-06).
    """
    if clase == ClaseTiquete.PRIMERA_CLASE:
        return vuelo.costo_persona_primera
    return vuelo.costo_persona_economica


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

    # Ninguna persona puede figurar dos veces como viajero en el mismo vuelo:
    # tampoco en otra reserva vigente ni en un tiquete activo de ese vuelo
    vuelos_ids = [vuelo.pk]
    if vuelo_regreso:
        vuelos_ids.append(vuelo_regreso.pk)
    duplicado_en_reserva = (
        ReservaViajero.objects.filter(
            reserva__estado=EstadoReserva.VIGENTE,
            viajero__documento__in=documentos_vistos,
        )
        .filter(Q(reserva__vuelo_id__in=vuelos_ids) | Q(reserva__vuelo_regreso_id__in=vuelos_ids))
        .exists()
    )
    duplicado_en_tiquete = Tiquete.objects.filter(
        vuelo_id__in=vuelos_ids,
        estado=EstadoTiquete.ACTIVO,
        viajero__documento__in=documentos_vistos,
    ).exists()
    if duplicado_en_reserva or duplicado_en_tiquete:
        raise DuplicatePassengerInFlight()

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


def _preparar_compra(
    cliente,
    vuelo_id: int,
    clase: str,
    viajeros_data: list[dict],
    reserva_id: int,
    tipo_trayecto: str,
    vuelo_regreso_id: int,
) -> dict:
    """Valida disponibilidad, descuenta cupos, procesa viajeros y liquida el total.

    Es la lógica común de la compra directa y del checkout del carrito; no debita
    ni crea la compra.
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

        # Comprobar límite de 5 tiquetes activos por cliente en el vuelo
        actuales = contar_tiquetes_activos_cliente_en_vuelo(cliente, vuelo)
        if actuales + num_pasajeros > 5:
            raise TicketLimitExceeded()

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

    # Cálculo de precios vigentes (DEC-06) por el punto único de consulta
    tarifa_vuelo = resolver_precio_vigente(vuelo, clase, now)
    total = tarifa_vuelo * num_pasajeros
    tarifa_regreso = None
    if vuelo_regreso:
        tarifa_regreso = resolver_precio_vigente(vuelo_regreso, clase, now)
        total += tarifa_regreso * num_pasajeros

    return {
        "reserva": reserva,
        "vuelo": vuelo,
        "vuelo_regreso": vuelo_regreso,
        "clase": clase,
        "tipo_trayecto": tipo_trayecto,
        "viajeros": viajeros,
        "num_pasajeros": num_pasajeros,
        "tarifa_vuelo": tarifa_vuelo,
        "tarifa_regreso": tarifa_regreso,
        "total": total,
    }


def _materializar_compra(cliente, preparada: dict, localizador: str) -> Compra:
    """Crea la compra, asigna sillas y registra las notificaciones a viajeros.

    No debita la billetera: el débito lo hace el llamador antes de invocarla.
    """
    reserva = preparada["reserva"]
    vuelo = preparada["vuelo"]
    vuelo_regreso = preparada["vuelo_regreso"]
    clase = preparada["clase"]
    viajeros = preparada["viajeros"]
    num_pasajeros = preparada["num_pasajeros"]
    tarifa_vuelo = preparada["tarifa_vuelo"]
    tarifa_regreso = preparada["tarifa_regreso"]

    compra = Compra.objects.create(
        cliente=cliente,
        localizador=localizador,
        valor_pagado=preparada["total"],
        tipo_trayecto=preparada["tipo_trayecto"],
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

        tiquete = Tiquete.objects.create(
            compra=compra,
            vuelo=vuelo,
            viajero=viajero,
            silla=silla,
            clase=clase,
            precio_pagado=tarifa_vuelo,
            codigo_tiquete=generar_codigo_tiquete(localizador, idx),
            estado=EstadoTiquete.ACTIVO,
        )
        # Outbox: el código de reserva se envía al correo de cada viajero (HU-013);
        # el envío SMTP lo procesa `process_purchase_emails` tras el commit.
        NotificacionCompra.objects.create(tiquete=tiquete, recipient=viajero.correo)

    # Si hay regreso, asignar sillas en regreso
    if vuelo_regreso:
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

            tiquete_regreso = Tiquete.objects.create(
                compra=compra,
                vuelo=vuelo_regreso,
                viajero=viajero,
                silla=silla,
                clase=clase,
                precio_pagado=tarifa_regreso,
                codigo_tiquete=generar_codigo_tiquete(localizador, idx),
                estado=EstadoTiquete.ACTIVO,
            )
            NotificacionCompra.objects.create(tiquete=tiquete_regreso, recipient=viajero.correo)

    return compra


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
    preparada = _preparar_compra(
        cliente, vuelo_id, clase, viajeros_data, reserva_id, tipo_trayecto, vuelo_regreso_id
    )

    # Débito atómico en billetera (DEC-03, DEC-09)
    wallet = cliente.wallet
    localizador = generar_localizador()
    debitar_para_compra(
        wallet_id=wallet.pk,
        monto=preparada["total"],
        referencia=f"Compra tiquetes localizador {localizador}",
    )

    return _materializar_compra(cliente, preparada, localizador)


# ---------------------------------------------------------------------------
# Carrito de compras
# ---------------------------------------------------------------------------


def obtener_carrito(cliente) -> Carrito:
    """Retorna el carrito activo del cliente, creándolo si no existe."""
    carrito, _ = Carrito.objects.get_or_create(cliente=cliente)
    return carrito


def _contar_pasajeros_carrito_en_vuelo(carrito: Carrito, vuelo_id: int, clase: str = None) -> int:
    """Pasajeros que el carrito ya acumula sobre un vuelo, opcionalmente por clase."""
    total = 0
    for item in carrito.items.filter(vuelo_id=vuelo_id):
        if clase is None or item.clase == clase:
            total += item.num_pasajeros
    return total


def _cupos_disponibles_en_clase(vuelo: Vuelo, clase: str) -> int:
    if clase == ClaseTiquete.PRIMERA_CLASE:
        return vuelo.cupos_disponibles_primera
    return vuelo.cupos_disponibles_economica


@transaction.atomic
def agregar_item_carrito(
    cliente,
    vuelo_id: int,
    clase: str,
    viajeros_data: list[dict],
    tipo_trayecto: str = TipoTrayecto.UNICO,
    vuelo_regreso_id: int = None,
) -> ItemCarrito:
    """Agrega un item al carrito validando vuelo disponible, cupos tentativos y el
    límite de 5 tiquetes del cliente por vuelo (carrito + reservas + compras).

    Los cupos no se descuentan aquí: se confirman en `checkout_carrito`.
    """
    if not viajeros_data:
        raise InsufficientSeats()
    num_pasajeros = len(viajeros_data)
    if num_pasajeros > 5:
        raise TicketLimitExceeded()

    now = timezone.now()
    vuelo = Vuelo.objects.get(pk=vuelo_id)
    if vuelo.estado != EstadoVuelo.PROGRAMADO or vuelo.salida_utc <= now:
        raise FlightNotAvailableForSale()

    vuelo_regreso = None
    if vuelo_regreso_id:
        vuelo_regreso = Vuelo.objects.get(pk=vuelo_regreso_id)
        if vuelo_regreso.estado != EstadoVuelo.PROGRAMADO or vuelo_regreso.salida_utc <= now:
            raise FlightNotAvailableForSale()

    carrito = obtener_carrito(cliente)

    # Límite de 5 tiquetes del cliente por vuelo: carrito + reservas vigentes + compras
    pax_carrito = _contar_pasajeros_carrito_en_vuelo(carrito, vuelo.pk)
    actuales = contar_tiquetes_activos_cliente_en_vuelo(cliente, vuelo)
    if actuales + pax_carrito + num_pasajeros > 5:
        raise TicketLimitExceeded()

    # Cupos tentativos en la clase, descontando lo que el carrito ya acumula
    for trayecto in (vuelo, vuelo_regreso):
        if trayecto is None:
            continue
        pax_en_clase = _contar_pasajeros_carrito_en_vuelo(carrito, trayecto.pk, clase)
        if _cupos_disponibles_en_clase(trayecto, clase) < pax_en_clase + num_pasajeros:
            raise InsufficientSeats()

    return ItemCarrito.objects.create(
        carrito=carrito,
        vuelo=vuelo,
        vuelo_regreso=vuelo_regreso,
        clase=clase,
        tipo_trayecto=tipo_trayecto,
        viajeros=viajeros_data,
    )


def quitar_item_carrito(cliente, item_id: int) -> None:
    """Elimina un item del carrito del cliente."""
    eliminados, _ = ItemCarrito.objects.filter(pk=item_id, carrito__cliente=cliente).delete()
    if not eliminados:
        raise CartItemNotFound()


def listar_carrito(cliente) -> dict:
    """Liquida el carrito: precio unitario y subtotal por item con el precio
    vigente (`resolver_precio_vigente`, DEC-06) y el total a pagar."""
    carrito = obtener_carrito(cliente)
    now = timezone.now()
    items = []
    total = Decimal("0.00")
    for item in carrito.items.select_related(
        "vuelo__ruta__origen",
        "vuelo__ruta__destino",
        "vuelo_regreso__ruta__origen",
        "vuelo_regreso__ruta__destino",
    ):
        precio_unitario = resolver_precio_vigente(item.vuelo, item.clase, now)
        subtotal = precio_unitario * item.num_pasajeros
        if item.vuelo_regreso:
            subtotal += (
                resolver_precio_vigente(item.vuelo_regreso, item.clase, now) * item.num_pasajeros
            )
        items.append(
            {
                "item": item,
                "num_pasajeros": item.num_pasajeros,
                "precio_unitario": precio_unitario,
                "subtotal": subtotal,
            }
        )
        total += subtotal
    return {"items": items, "total": total}


@transaction.atomic
def checkout_carrito(cliente) -> list[Compra]:
    """Confirma todos los items del carrito en una sola transacción con un débito
    único del total (DEC-06, DEC-09).

    Si algo falla — saldo insuficiente, cupos agotados, límite de tiquetes — se
    revierte todo: el carrito, los cupos y la billetera quedan intactos.
    """
    carrito = Carrito.objects.select_for_update().filter(cliente=cliente).first()
    items = list(carrito.items.all()) if carrito else []
    if not items:
        raise CartEmpty()

    preparadas = [
        _preparar_compra(
            cliente,
            item.vuelo_id,
            item.clase,
            item.viajeros,
            None,
            item.tipo_trayecto,
            item.vuelo_regreso_id,
        )
        for item in items
    ]

    # Límite de 5 tiquetes del cliente por vuelo acumulando todos los items
    pax_por_vuelo = {}
    for preparada in preparadas:
        for trayecto in (preparada["vuelo"], preparada["vuelo_regreso"]):
            if trayecto is None:
                continue
            pax_por_vuelo[trayecto.pk] = (
                pax_por_vuelo.get(trayecto.pk, 0) + preparada["num_pasajeros"]
            )
    for vuelo_id, pax in pax_por_vuelo.items():
        actuales = contar_tiquetes_activos_cliente_en_vuelo(
            cliente, Vuelo.objects.get(pk=vuelo_id)
        )
        if actuales + pax > 5:
            raise TicketLimitExceeded()

    total = sum((preparada["total"] for preparada in preparadas), Decimal("0.00"))

    # Débito único del total del carrito (DEC-03, DEC-09)
    wallet = cliente.wallet
    debitar_para_compra(
        wallet_id=wallet.pk,
        monto=total,
        referencia=f"Checkout carrito ({len(preparadas)} compras)",
    )

    compras = [
        _materializar_compra(cliente, preparada, generar_localizador())
        for preparada in preparadas
    ]
    carrito.items.all().delete()
    return compras


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
