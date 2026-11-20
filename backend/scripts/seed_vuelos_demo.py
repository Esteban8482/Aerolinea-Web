"""
Script de datos de demostración — Iteración 2 (Aerolinea Web / "Alas").

Crea ciudades, rutas autorizadas y un repertorio variado de vuelos
programados usando la capa de servicios del backend (reglas RN-12/RN-13,
generación de código, sillas, noticia y bitácora incluidas).

USO (dentro del entorno del backend):

    # Opción 1: shell de Django
    python manage.py shell < scripts/seed_vuelos_demo.py

    # Opción 2: con Docker Compose (nombre del servicio según compose.local.yaml)
    docker compose -f compose.local.yaml exec -T backend \
        python manage.py shell < backend/scripts/seed_vuelos_demo.py

Es idempotente a nivel de ciudades y rutas; los vuelos se crean siempre
(los códigos son consecutivos nuevos). Si una fecha queda en el pasado,
el vuelo se omite con un aviso.
"""

from datetime import date, time, timedelta
from decimal import Decimal

from apps.flights.models import Ciudad, Ruta, TipoVuelo
from apps.flights.services import crear_ruta, programar_vuelo
from apps.flights import errors as fl_errors
from django.contrib.auth import get_user_model

User = get_user_model()

# ---------------------------------------------------------------------------
# 0. Actor: primer superusuario / admin disponible (para bitácora y noticias)
# ---------------------------------------------------------------------------
actor = (
    User.objects.filter(is_superuser=True).first()
    or User.objects.filter(role__in=["ROOT", "ADMINISTRADOR"]).first()
    or User.objects.first()
)

# ---------------------------------------------------------------------------
# 1. Ciudades
#    Nacionales: capitales principales de Colombia (regla de rutas nacionales)
#    Internacionales: origen/destino autorizado según flags del modelo
# ---------------------------------------------------------------------------
TZ_CO = "America/Bogota"

CIUDADES = [
    # nombre, país, zona horaria, capital principal, origen intl, destino intl
    ("Bogotá",       "CO", TZ_CO, True,  True,  True),
    ("Medellín",     "CO", TZ_CO, True,  True,  True),
    ("Cali",         "CO", TZ_CO, True,  False, False),
    ("Cartagena",    "CO", TZ_CO, True,  False, True),
    ("Pereira",      "CO", TZ_CO, True,  False, False),
    ("Barranquilla", "CO", TZ_CO, True,  False, False),
    ("Madrid",       "ES", "Europe/Madrid",     False, False, True),
    ("Miami",        "US", "America/New_York",  False, False, True),
    ("Ciudad de Panamá", "PA", "America/Panama", False, False, True),
    ("Lima",         "PE", "America/Lima",      False, False, True),
]

ciudad_por_nombre = {}
for nombre, pais, tz, capital, origen_int, destino_int in CIUDADES:
    c, created = Ciudad.objects.get_or_create(
        nombre=nombre,
        defaults={
            "codigo_pais": pais,
            "zona_horaria": TZ_CO if pais == "CO" else dict(
                (n, z) for n, _, z, *_ in CIUDADES
            )[nombre],
            "es_capital_principal": capital,
            "origen_internacional": origen_int,
            "destino_internacional": destino_int,
            "activa": True,
        },
    )
    ciudad_por_nombre[nombre] = c
    print(f"{'[nueva]' if created else '[ya existe]'} Ciudad: {c}")

# ---------------------------------------------------------------------------
# 2. Rutas autorizadas
#    (origen, destino, tipo, duración en minutos)
# ---------------------------------------------------------------------------
RUTAS = [
    # Nacionales (capitales principales CO -> CO)
    ("Bogotá", "Pereira",       TipoVuelo.NACIONAL, 55),
    ("Bogotá", "Medellín",      TipoVuelo.NACIONAL, 60),
    ("Bogotá", "Cali",          TipoVuelo.NACIONAL, 65),
    ("Bogotá", "Cartagena",     TipoVuelo.NACIONAL, 85),
    ("Bogotá", "Barranquilla",  TipoVuelo.NACIONAL, 90),
    ("Medellín", "Bogotá",      TipoVuelo.NACIONAL, 60),
    ("Medellín", "Cartagena",   TipoVuelo.NACIONAL, 75),
    ("Cali", "Bogotá",          TipoVuelo.NACIONAL, 65),
    ("Pereira", "Bogotá",       TipoVuelo.NACIONAL, 55),
    ("Cartagena", "Bogotá",     TipoVuelo.NACIONAL, 85),
    # Internacionales (origen habilitado -> destino habilitado)
    ("Bogotá", "Madrid",        TipoVuelo.INTERNACIONAL, 590),
    ("Bogotá", "Miami",         TipoVuelo.INTERNACIONAL, 230),
    ("Bogotá", "Ciudad de Panamá", TipoVuelo.INTERNACIONAL, 95),
    ("Bogotá", "Lima",          TipoVuelo.INTERNACIONAL, 180),
    ("Medellín", "Miami",       TipoVuelo.INTERNACIONAL, 220),
    ("Medellín", "Madrid",      TipoVuelo.INTERNACIONAL, 600),
]

ruta_por_par = {}
for origen, destino, tipo, dur in RUTAS:
    try:
        r = crear_ruta(
            origen_id=ciudad_por_nombre[origen].id,
            destino_id=ciudad_por_nombre[destino].id,
            tipo_vuelo=tipo,
            duracion_min=dur,
        )
        print(f"[nueva] Ruta: {r}")
    except fl_errors.DuplicateRoute:
        r = Ruta.objects.get(
            origen=ciudad_por_nombre[origen], destino=ciudad_por_nombre[destino]
        )
        print(f"[ya existe] Ruta: {r}")
    ruta_por_par[(origen, destino)] = r

# ---------------------------------------------------------------------------
# 3. Vuelos de demostración
#    Mezcla: nacional/internacional, mañana/tarde/noche, barato/caro,
#    fines de semana y entre semana, próximos días y próximas semanas.
#    (origen, destino, días desde hoy, hora salida, tarifa económica COP)
# ---------------------------------------------------------------------------
HOY = date.today()

VUELOS = [
    # --- Nacionales económicos, alta frecuencia ---
    ("Bogotá", "Pereira",       1, time(6, 0),   Decimal("145000")),
    ("Bogotá", "Pereira",       1, time(16, 0),  Decimal("250000")),  # tarde, más caro
    ("Bogotá", "Medellín",      2, time(7, 30),  Decimal("160000")),
    ("Bogotá", "Medellín",      3, time(19, 45), Decimal("198000")),
    ("Bogotá", "Cali",          2, time(9, 15),  Decimal("175000")),
    ("Bogotá", "Cartagena",     2, time(11, 0),  Decimal("210000")),
    ("Bogotá", "Barranquilla",  4, time(14, 20), Decimal("230000")),
    ("Medellín", "Cartagena",   3, time(8, 40),  Decimal("195000")),
    ("Medellín", "Bogotá",      1, time(18, 10), Decimal("152000")),
    ("Cali", "Bogotá",          5, time(6, 50),  Decimal("168000")),
    ("Cartagena", "Bogotá",     6, time(20, 5),  Decimal("225000")),
    ("Pereira", "Bogotá",       7, time(10, 30), Decimal("155000")),
    # --- Internacionales ---
    ("Bogotá", "Miami",         2, time(9, 0),   Decimal("1150000")),
    ("Bogotá", "Madrid",        3, time(20, 45), Decimal("2800000")),  # nocturno, llega al día siguiente
    ("Bogotá", "Madrid",        10, time(22, 15), Decimal("2450000")), # más lejano, más barato
    ("Bogotá", "Ciudad de Panamá", 4, time(13, 30), Decimal("780000")),
    ("Bogotá", "Lima",          5, time(17, 0),  Decimal("980000")),
    ("Medellín", "Miami",       6, time(10, 15), Decimal("1250000")),
    ("Medellín", "Madrid",      12, time(21, 0), Decimal("2690000")),
]

creados, omitidos = 0, 0
for origen, destino, dias, hora, costo in VUELOS:
    try:
        v = programar_vuelo(
            origen_id=ciudad_por_nombre[origen].id,
            destino_id=ciudad_por_nombre[destino].id,
            fecha_salida=HOY + timedelta(days=dias),
            hora_salida=hora,
            costo_persona_economica=costo,
            costo_persona_primera=None,  # 1.5x automático (regla de negocio)
            actor=actor,
            ip_origen="127.0.0.1",
        )
        creados += 1
        print(
            f"[vuelo] {v.codigo_vuelo} {origen} -> {destino} "
            f"{v.fecha_salida} {v.hora_salida} ${costo:,.0f} COP"
        )
    except fl_errors.DepartureInPast:
        omitidos += 1
        print(f"[omitido] {origen} -> {destino} en {dias} día(s): fecha/hora en el pasado")

print("\n===============================================")
print(f"Resumen: {creados} vuelos creados, {omitidos} omitidos.")
print(f"Ciudades: {Ciudad.objects.count()} | Rutas: {Ruta.objects.count()}")
print("Listo para la demostración.")
print("===============================================")
