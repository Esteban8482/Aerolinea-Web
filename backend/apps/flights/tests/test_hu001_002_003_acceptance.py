"""Pruebas de aceptación directa para las Historias de Usuario HU-001, HU-002 y HU-003.

Documentación de referencia: docs/Historias_Usuario_Sistema_Tiquetes_Aereos.pdf
- HU-001: Programación de vuelos nacionales e internacionales (Iteración 2)
- HU-002: Edición de un vuelo programado (Iteración 2)
- HU-003: Cancelación de un vuelo programado (Iteración 2)
"""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from apps.flights.models import (
    BitacoraVuelo,
    Ciudad,
    EstadoSilla,
    EstadoVuelo,
    NoticiaVuelo,
    NotificacionAfectacion,
    Ruta,
    Silla,
    Vuelo,
)
from apps.flights.services import programar_vuelo


# ==============================================================================
# HU-001: Programación de vuelos nacionales e internacionales
# ==============================================================================


@pytest.mark.django_db
def test_hu001_programacion_vuelo_nacional_criterios_completos(catalogo, admin_client):
    """HU-001: Verifica programación nacional, código único, 150 sillas, noticia y catálogo."""
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    fecha_salida = date.today() + timedelta(days=5)

    payload = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(fecha_salida),
        "hora_salida": "10:00:00",
        "costo_persona_economica": "170000.00",
        "costo_persona_primera": "255000.00",
    }

    response = admin_client.post("/api/v1/flights/", payload, format="json")
    assert response.status_code == 201
    data = response.json()

    # 1. Estado "PROGRAMADO" y código único con prefijo
    assert data["estado"] == "PROGRAMADO"
    assert data["codigo_vuelo"].startswith("XX")

    # 2. Distribución de sillas nacional (RN-12: 150 sillas, 25 primera, 125 económica)
    vuelo = Vuelo.objects.get(pk=data["id"])
    sillas = Silla.objects.filter(vuelo=vuelo)
    assert sillas.count() == 150
    assert sillas.filter(clase="PRIMERA_CLASE", espacio_extra=True).count() == 25
    assert sillas.filter(clase="ECONOMICA", espacio_extra=False).count() == 125
    assert sillas.filter(estado=EstadoSilla.DISPONIBLE).count() == 150

    # 3. Noticia oficial publicada automáticamente
    noticia = NoticiaVuelo.objects.get(vuelo=vuelo)
    assert noticia.vigente is True
    assert "Bogotá" in noticia.titulo and "Pereira" in noticia.titulo
    assert "170000" in noticia.contenido

    # 4. El vuelo aparece en la búsqueda y en el catálogo por ciudad
    res_list = admin_client.get(f"/api/v1/flights/?origen=Bogotá&destino=Pereira")
    assert res_list.status_code == 200
    codigos_encontrados = [f["codigo_vuelo"] for f in res_list.json()]
    assert vuelo.codigo_vuelo in codigos_encontrados


@pytest.mark.django_db
def test_hu001_programacion_vuelo_internacional_capacidad_250(catalogo, admin_client):
    """HU-001: Verifica programación internacional (RN-13: 250 sillas, 50 primera, 200 económica)."""
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Madrid")
    fecha_salida = date.today() + timedelta(days=12)

    payload = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(fecha_salida),
        "hora_salida": "21:00:00",
        "costo_persona_economica": "1200000.00",
    }

    response = admin_client.post("/api/v1/flights/", payload, format="json")
    assert response.status_code == 201
    data = response.json()

    assert data["tipo_vuelo"] == "INTERNACIONAL"
    assert data["capacidad_total"] == 250
    assert data["cupos_primera_clase"] == 50
    assert data["cupos_economica"] == 200

    vuelo = Vuelo.objects.get(pk=data["id"])
    assert Silla.objects.filter(vuelo=vuelo).count() == 250


@pytest.mark.django_db
def test_hu001_rechazo_ruta_no_autorizada_o_campos_vacios(catalogo, admin_client, regular_client):
    """HU-001: Valida rechazo ante ruta no autorizada, campos faltantes y acceso restringido."""
    # 1. Campos obligatorios vacíos
    res_vacio = admin_client.post("/api/v1/flights/", {}, format="json")
    assert res_vacio.status_code == 400

    # 2. Ruta no autorizada (ej. ciudad de destino inexistente o par sin ruta activa)
    res_ruta = admin_client.post(
        "/api/v1/flights/",
        {
            "origen_id": 9999,
            "destino_id": 8888,
            "fecha_salida": str(date.today() + timedelta(days=5)),
            "hora_salida": "10:00:00",
            "costo_persona_economica": "150000.00",
        },
        format="json",
    )
    assert res_ruta.status_code == 400
    assert res_ruta.json()["code"] == "unauthorized_route"

    # 3. Usuario sin rol administrador (denegado)
    res_perm = regular_client.post(
        "/api/v1/flights/",
        {
            "origen_id": 1,
            "destino_id": 2,
            "fecha_salida": str(date.today() + timedelta(days=5)),
            "hora_salida": "10:00:00",
            "costo_persona_economica": "150000.00",
        },
        format="json",
    )
    assert res_perm.status_code == 403


# ==============================================================================
# HU-002: Edición de un vuelo programado
# ==============================================================================


@pytest.mark.django_db
def test_hu002_edicion_recalcula_llegada_y_notifica_pasajeros(catalogo, admin_user, admin_client):
    """HU-002: Modifica fecha/hora, recalcula arribo, preserva inmutables y notifica."""
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    vuelo = programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=3),
        hora_salida=time(8, 0),
        costo_persona_economica=Decimal("150000.00"),
        actor=admin_user,
    )
    codigo_original = vuelo.codigo_vuelo
    ruta_original = vuelo.ruta_id

    nueva_fecha = date.today() + timedelta(days=4)
    nueva_hora = "14:00:00"

    # Intentamos también enviar campos inmutables (deben ser ignorados o preservados)
    payload = {
        "codigo_vuelo": "XX9999",
        "origen_id": 999,
        "fecha_salida": str(nueva_fecha),
        "hora_salida": nueva_hora,
        "costo_persona_economica": "185000.00",
    }

    url = f"/api/v1/flights/{vuelo.pk}/"
    response = admin_client.patch(url, payload, format="json")
    assert response.status_code == 200
    data = response.json()

    # Campos inmutables se conservan
    assert data["codigo_vuelo"] == codigo_original
    vuelo.refresh_from_db()
    assert vuelo.codigo_vuelo == codigo_original
    assert vuelo.ruta_id == ruta_original

    # Recálculo de arribo (Bogotá -> Pereira dura 55 min => llegada 14:55)
    assert data["fecha_salida"] == str(nueva_fecha)
    assert data["hora_salida"] == nueva_hora
    assert data["hora_llegada"] == "14:55:00"

    # Notificación de reprogramación registrada
    notif = NotificacionAfectacion.objects.filter(
        vuelo=vuelo, tipo_afectacion=NotificacionAfectacion.Tipo.REPROGRAMACION
    )
    assert notif.exists()

    # Bitácora de auditoría
    bitacora = BitacoraVuelo.objects.filter(vuelo=vuelo, tipo_evento=BitacoraVuelo.Evento.EDICION)
    assert bitacora.exists()


@pytest.mark.django_db
def test_hu002_edicion_rechaza_vuelos_no_programados_o_fechas_pasadas(
    catalogo, admin_user, admin_client
):
    """HU-002: Sólo pueden editarse vuelos en estado 'programado' y fecha futura."""
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    vuelo = programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=3),
        hora_salida=time(8, 0),
        costo_persona_economica=Decimal("150000.00"),
        actor=admin_user,
    )

    url = f"/api/v1/flights/{vuelo.pk}/"

    # 1. Rechazo por fecha en el pasado
    res_pasado = admin_client.patch(
        url,
        {"fecha_salida": "2020-01-01", "hora_salida": "10:00:00"},
        format="json",
    )
    assert res_pasado.status_code == 400
    assert res_pasado.json()["code"] == "departure_in_past"

    # 2. Rechazo por vuelo que ya no está en estado PROGRAMADO
    vuelo.estado = EstadoVuelo.REALIZADO
    vuelo.save()

    res_no_prog = admin_client.patch(
        url,
        {"costo_persona_economica": "190000.00"},
        format="json",
    )
    assert res_no_prog.status_code == 400
    assert res_no_prog.json()["code"] == "flight_not_editable"


# ==============================================================================
# HU-003: Cancelación de un vuelo programado
# ==============================================================================


@pytest.mark.django_db
def test_hu003_cancelacion_vuelo_motivo_noticias_y_notificacion(
    catalogo, admin_user, admin_client
):
    """HU-003: Cancela vuelo, vacía cupos disponibles, inactiva noticias y registra afectación."""
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    vuelo = programar_vuelo(
        origen_id=origen.pk,
        destino_id=destino.pk,
        fecha_salida=date.today() + timedelta(days=4),
        hora_salida=time(11, 0),
        costo_persona_economica=Decimal("150000.00"),
        actor=admin_user,
    )
    assert vuelo.noticias.filter(vigente=True).exists()

    url = f"/api/v1/flights/{vuelo.pk}/cancel/"
    motivo = "Falla técnica severa en los motores de la aeronave asignada."

    response = admin_client.post(
        url,
        {"motivo": motivo, "alternativa": "REINTEGRO"},
        format="json",
    )
    assert response.status_code == 200
    data = response.json()

    # Estado CANCELADO y cupos a 0
    assert data["estado"] == "CANCELADO"
    assert data["motivo_cancelacion"] == motivo
    assert data["cupos_disponibles_primera"] == 0
    assert data["cupos_disponibles_economica"] == 0

    # Las noticias asociadas dejan de estar vigentes
    vuelo.refresh_from_db()
    assert not vuelo.noticias.filter(vigente=True).exists()

    # Notificación de cancelación y alternativa persistente
    notif = NotificacionAfectacion.objects.filter(
        vuelo=vuelo, tipo_afectacion=NotificacionAfectacion.Tipo.CANCELACION
    )
    assert notif.exists()
    assert notif.first().datos_adicionales.get("alternativa") == "REINTEGRO"

    # Intento de cancelar nuevamente es rechazado
    res_recancel = admin_client.post(url, {"motivo": "Reintento"}, format="json")
    assert res_recancel.status_code == 400
    assert res_recancel.json()["code"] == "flight_not_cancellable"



# ==============================================================================
# Editor de Catálogo de Rutas (Administrador y ROOT)
# ==============================================================================


@pytest.mark.django_db
def test_catalogo_rutas_creacion_edicion_y_permisos(catalogo, admin_client, regular_client):
    """Verifica creación, edición y restricción de rutas en el catálogo."""
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="San Andrés")

    # 1. Cliente común no puede crear rutas (403)
    res_cli = regular_client.post(
        "/api/v1/flights/routes/",
        {
            "origen_id": origen.pk,
            "destino_id": destino.pk,
            "tipo_vuelo": "NACIONAL",
            "duracion_min": 120,
            "activa": True,
        },
        format="json",
    )
    assert res_cli.status_code == 403

    # 2. Administrador crea una nueva ruta
    res_admin = admin_client.post(
        "/api/v1/flights/routes/",
        {
            "origen_id": origen.pk,
            "destino_id": destino.pk,
            "tipo_vuelo": "NACIONAL",
            "duracion_min": 120,
            "activa": True,
        },
        format="json",
    )
    assert res_admin.status_code in (200, 201)
    ruta_id = res_admin.json()["id"]

    # 3. Administrador modifica la ruta (desactiva y ajusta duración)
    res_patch = admin_client.patch(
        f"/api/v1/flights/routes/{ruta_id}/",
        {"activa": False, "duracion_min": 115},
        format="json",
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["activa"] is False
    assert res_patch.json()["duracion_min"] == 115

    # 4. Consulta pública no incluye ruta inactiva
    res_pub = regular_client.get("/api/v1/flights/routes/")
    assert not any(r["id"] == ruta_id for r in res_pub.json())

    # 5. Consulta de administrador con ?todos=1 sí la incluye
    res_adm_all = admin_client.get("/api/v1/flights/routes/?todos=1")
    assert any(r["id"] == ruta_id for r in res_adm_all.json())
