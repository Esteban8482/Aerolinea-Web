from datetime import date, timedelta

import pytest

from apps.flights.models import BitacoraVuelo, Ciudad, NoticiaVuelo, Ruta, Silla, Vuelo


@pytest.mark.django_db
def test_programar_vuelo_nacional_exitoso(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")

    fecha_salida = date.today() + timedelta(days=5)

    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(fecha_salida),
        "hora_salida": "14:30:00",
        "costo_persona_economica": "180000.00",
        "costo_persona_primera": "270000.00",
    }

    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 201
    resp_data = response.json()

    # Validaciones del vuelo creado
    assert resp_data["codigo_vuelo"].startswith("XX")
    assert resp_data["tipo_vuelo"] == "NACIONAL"
    assert resp_data["capacidad_total"] == 150
    assert resp_data["cupos_primera_clase"] == 25
    assert resp_data["cupos_economica"] == 125
    assert resp_data["cupos_disponibles_primera"] == 25
    assert resp_data["cupos_disponibles_economica"] == 125
    assert resp_data["estado"] == "PROGRAMADO"
    assert resp_data["fecha_salida"] == str(fecha_salida)
    assert resp_data["hora_salida"] == "14:30:00"
    # Duración Bogotá -> Pereira es 55 min => llegada 15:25
    assert resp_data["hora_llegada"] == "15:25:00"
    assert resp_data["fecha_llegada"] == str(fecha_salida)

    # Validar inventario de sillas generadas en BD (RN-12: 150 sillas)
    vuelo = Vuelo.objects.get(pk=resp_data["id"])
    sillas = Silla.objects.filter(vuelo=vuelo)
    assert sillas.count() == 150
    assert sillas.filter(clase="PRIMERA_CLASE").count() == 25
    assert sillas.filter(clase="ECONOMICA").count() == 125

    # Validar publicación de noticia (RF-ADM-14, CU-01)
    noticia = NoticiaVuelo.objects.get(vuelo=vuelo)
    assert noticia.vigente is True
    assert "Bogotá" in noticia.titulo and "Pereira" in noticia.titulo

    # Validar bitácora de auditoría
    bitacora = BitacoraVuelo.objects.get(vuelo=vuelo)
    assert bitacora.tipo_evento == BitacoraVuelo.Evento.PROGRAMACION


@pytest.mark.django_db
def test_programar_vuelo_internacional_calculo_horario_y_sillas(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Madrid")

    fecha_salida = date.today() + timedelta(days=10)
    # Salida 20:00 Bogotá (UTC-5)
    # Duración Bogotá - Madrid: 590 min (9h 50m)
    # Salida UTC: 01:00 día siguiente. Llegada UTC: 10:50.
    # Madrid (UTC+1 o UTC+2 en verano): llega al día siguiente local
    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(fecha_salida),
        "hora_salida": "20:00:00",
        "costo_persona_economica": "2500000.00",
    }

    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 201
    resp_data = response.json()

    assert resp_data["tipo_vuelo"] == "INTERNACIONAL"
    assert resp_data["capacidad_total"] == 250
    assert resp_data["cupos_primera_clase"] == 50
    assert resp_data["cupos_economica"] == 200

    vuelo = Vuelo.objects.get(pk=resp_data["id"])
    assert Silla.objects.filter(vuelo=vuelo).count() == 250


@pytest.mark.django_db
def test_programar_vuelo_fecha_salida_en_el_pasado_rechazada(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Medellín")

    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": "2020-01-01",
        "hora_salida": "10:00:00",
        "costo_persona_economica": "150000.00",
    }

    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "departure_in_past"


@pytest.mark.django_db
def test_programar_vuelo_ruta_no_autorizada_rechazada(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Pasto")
    destino = Ciudad.objects.get(nombre="Madrid")  # Pasto no es origen internacional autorizado

    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(date.today() + timedelta(days=2)),
        "hora_salida": "10:00:00",
        "costo_persona_economica": "1500000.00",
    }

    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "unauthorized_route"


@pytest.mark.django_db
def test_programar_vuelo_origen_coincide_con_destino_rechazado(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Bogotá")

    data = {
        "origen_id": origen.pk,
        "destino_id": origen.pk,
        "fecha_salida": str(date.today() + timedelta(days=2)),
        "hora_salida": "10:00:00",
        "costo_persona_economica": "150000.00",
    }

    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "same_origin_destination"


@pytest.mark.django_db
def test_programar_vuelo_costo_invalido_rechazado(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")

    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(date.today() + timedelta(days=2)),
        "hora_salida": "10:00:00",
        "costo_persona_economica": "0.00",
    }

    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_programar_vuelo_denegado_para_no_administrador(catalogo, regular_client, anon_client):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")

    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(date.today() + timedelta(days=2)),
        "hora_salida": "10:00:00",
        "costo_persona_economica": "150000.00",
    }

    # Cliente regular (rol CLIENTE)
    res_cliente = regular_client.post("/api/v1/flights/", data, format="json")
    assert res_cliente.status_code == 403

    # Anónimo (visitante)
    res_anon = anon_client.post("/api/v1/flights/", data, format="json")
    assert res_anon.status_code in (401, 403)


@pytest.mark.django_db
def test_consultar_catalogos_y_listar_vuelos(catalogo, admin_client, anon_client):
    # Consultar catálogo de ciudades (público)
    res_ciudades = anon_client.get("/api/v1/flights/cities/")
    assert res_ciudades.status_code == 200
    ciudades = res_ciudades.json()
    assert len(ciudades) >= 20
    assert any(c["nombre"] == "Pereira" for c in ciudades)

    # Consultar catálogo de rutas (público)
    res_rutas = anon_client.get("/api/v1/flights/routes/")
    assert res_rutas.status_code == 200
    rutas = res_rutas.json()
    assert len(rutas) >= 30

    # Programar un vuelo para listarlo
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    fecha_salida = date.today() + timedelta(days=7)
    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(fecha_salida),
        "hora_salida": "09:00:00",
        "costo_persona_economica": "175000.00",
    }
    creacion = admin_client.post("/api/v1/flights/", data, format="json")
    assert creacion.status_code == 201
    vuelo_id = creacion.json()["id"]

    # Listar vuelos con filtros (RF-ADM-18)
    res_vuelos = anon_client.get("/api/v1/flights/?estado=PROGRAMADO&origen=Bogotá&destino=Pereira")
    assert res_vuelos.status_code == 200
    vuelos = res_vuelos.json()
    assert len(vuelos) >= 1
    assert vuelos[0]["id"] == vuelo_id

    # Detalle de vuelo (público)
    res_detalle = anon_client.get(f"/api/v1/flights/{vuelo_id}/")
    assert res_detalle.status_code == 200
    detalle = res_detalle.json()
    assert detalle["id"] == vuelo_id
    assert detalle["capacidad_total"] == 150



@pytest.mark.django_db
def test_programar_vuelo_campos_obligatorios_faltantes(catalogo, admin_client):
    response = admin_client.post("/api/v1/flights/", {}, format="json")
    assert response.status_code == 400
    resp = response.json()
    assert "details" in resp
    for campo in ["origen_id", "destino_id", "fecha_salida", "hora_salida", "costo_persona_economica"]:
        assert campo in resp["details"]


@pytest.mark.django_db
def test_programar_vuelo_formato_fecha_hora_invalido(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")

    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": "fecha-invalida",
        "hora_salida": "hora-invalida",
        "costo_persona_economica": "150000.00",
    }
    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 400
    resp = response.json()
    assert "fecha_salida" in resp["details"]
    assert "hora_salida" in resp["details"]


@pytest.mark.django_db
def test_programar_vuelo_costo_primera_clase_personalizado_valido(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    fecha_salida = date.today() + timedelta(days=4)

    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(fecha_salida),
        "hora_salida": "11:00:00",
        "costo_persona_economica": "160000.00",
        "costo_persona_primera": "310000.00",
    }
    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 201
    resp = response.json()
    assert resp["costo_persona_primera"] == "310000.00"
    vuelo = Vuelo.objects.get(pk=resp["id"])
    assert str(vuelo.costo_persona_primera) == "310000.00"


@pytest.mark.django_db
def test_programar_vuelo_costo_primera_clase_invalido_rechazado(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")

    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(date.today() + timedelta(days=4)),
        "hora_salida": "11:00:00",
        "costo_persona_economica": "160000.00",
        "costo_persona_primera": "-500.00",
    }
    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_flight_cost"


@pytest.mark.django_db
def test_programar_vuelo_ciudad_o_ruta_inactiva_rechazada(catalogo, admin_client):
    origen = Ciudad.objects.get(nombre="Bogotá")
    destino = Ciudad.objects.get(nombre="Pereira")
    ruta = Ruta.objects.get(origen=origen, destino=destino)
    ruta.activa = False
    ruta.save()

    data = {
        "origen_id": origen.pk,
        "destino_id": destino.pk,
        "fecha_salida": str(date.today() + timedelta(days=3)),
        "hora_salida": "10:00:00",
        "costo_persona_economica": "150000.00",
    }
    response = admin_client.post("/api/v1/flights/", data, format="json")
    assert response.status_code == 400
    assert response.json()["code"] == "unauthorized_route"
