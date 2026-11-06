CIUDADES_INICIALES = [
    # 5 orígenes autorizados tanto para vuelos nacionales como internacionales
    {
        "nombre": "Pereira",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": True,
        "destino_internacional": False,
    },
    {
        "nombre": "Bogotá",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": True,
        "destino_internacional": False,
    },
    {
        "nombre": "Medellín",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": True,
        "destino_internacional": False,
    },
    {
        "nombre": "Cali",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": True,
        "destino_internacional": False,
    },
    {
        "nombre": "Cartagena",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": True,
        "destino_internacional": False,
    },
    # Otras capitales principales nacionales
    {
        "nombre": "Barranquilla",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Bucaramanga",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Santa Marta",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Cúcuta",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Manizales",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Armenia",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Ibagué",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Pasto",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Villavicencio",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Montería",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Neiva",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Valledupar",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Popayán",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Riohacha",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Sincelejo",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "San Andrés",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    {
        "nombre": "Leticia",
        "codigo_pais": "CO",
        "zona_horaria": "America/Bogota",
        "es_capital_principal": True,
        "origen_internacional": False,
        "destino_internacional": False,
    },
    # 5 destinos internacionales autorizados
    {
        "nombre": "Madrid",
        "codigo_pais": "ES",
        "zona_horaria": "Europe/Madrid",
        "es_capital_principal": False,
        "origen_internacional": False,
        "destino_internacional": True,
    },
    {
        "nombre": "Londres",
        "codigo_pais": "GB",
        "zona_horaria": "Europe/London",
        "es_capital_principal": False,
        "origen_internacional": False,
        "destino_internacional": True,
    },
    {
        "nombre": "Nueva York",
        "codigo_pais": "US",
        "zona_horaria": "America/New_York",
        "es_capital_principal": False,
        "origen_internacional": False,
        "destino_internacional": True,
    },
    {
        "nombre": "Buenos Aires",
        "codigo_pais": "AR",
        "zona_horaria": "America/Argentina/Buenos_Aires",
        "es_capital_principal": False,
        "origen_internacional": False,
        "destino_internacional": True,
    },
    {
        "nombre": "Miami",
        "codigo_pais": "US",
        "zona_horaria": "America/New_York",
        "es_capital_principal": False,
        "origen_internacional": False,
        "destino_internacional": True,
    },
]

RUTAS_INICIALES = [
    # Rutas nacionales principales (origen, destino, duracion_min)
    ("Bogotá", "Pereira", 55),
    ("Pereira", "Bogotá", 55),
    ("Bogotá", "Medellín", 50),
    ("Medellín", "Bogotá", 50),
    ("Bogotá", "Cali", 60),
    ("Cali", "Bogotá", 60),
    ("Bogotá", "Cartagena", 85),
    ("Cartagena", "Bogotá", 85),
    ("Bogotá", "Barranquilla", 90),
    ("Barranquilla", "Bogotá", 90),
    ("Bogotá", "Bucaramanga", 60),
    ("Bucaramanga", "Bogotá", 60),
    ("Bogotá", "Santa Marta", 95),
    ("Santa Marta", "Bogotá", 95),
    ("Bogotá", "Cúcuta", 70),
    ("Cúcuta", "Bogotá", 70),
    ("Bogotá", "Pasto", 85),
    ("Pasto", "Bogotá", 85),
    ("Bogotá", "San Andrés", 130),
    ("San Andrés", "Bogotá", 130),
    ("Medellín", "Cali", 50),
    ("Cali", "Medellín", 50),
    ("Medellín", "Cartagena", 65),
    ("Cartagena", "Medellín", 65),
    ("Medellín", "Barranquilla", 70),
    ("Barranquilla", "Medellín", 70),
    ("Medellín", "Santa Marta", 75),
    ("Santa Marta", "Medellín", 75),
    ("Cali", "Cartagena", 85),
    ("Cartagena", "Cali", 85),
    ("Pereira", "Medellín", 45),
    ("Medellín", "Pereira", 45),
    ("Pereira", "Cartagena", 80),
    ("Cartagena", "Pereira", 80),
    # Rutas internacionales autorizadas (5 orígenes CO hacia 5 destinos exterior)
    ("Bogotá", "Madrid", 590),
    ("Bogotá", "Londres", 620),
    ("Bogotá", "Nueva York", 345),
    ("Bogotá", "Buenos Aires", 360),
    ("Bogotá", "Miami", 240),
    ("Medellín", "Madrid", 600),
    ("Medellín", "Londres", 630),
    ("Medellín", "Nueva York", 330),
    ("Medellín", "Buenos Aires", 380),
    ("Medellín", "Miami", 215),
    ("Cali", "Madrid", 615),
    ("Cali", "Londres", 645),
    ("Cali", "Nueva York", 360),
    ("Cali", "Buenos Aires", 370),
    ("Cali", "Miami", 245),
    ("Cartagena", "Madrid", 580),
    ("Cartagena", "Londres", 610),
    ("Cartagena", "Nueva York", 295),
    ("Cartagena", "Buenos Aires", 410),
    ("Cartagena", "Miami", 175),
    ("Pereira", "Madrid", 610),
    ("Pereira", "Londres", 640),
    ("Pereira", "Nueva York", 350),
    ("Pereira", "Buenos Aires", 375),
    ("Pereira", "Miami", 235),
]


def cargar_catalogo(apps_registry=None):
    """Carga de ciudades y rutas iniciales autorizadas de forma idempotente."""
    if apps_registry:
        Ciudad = apps_registry.get_model("flights", "Ciudad")
        Ruta = apps_registry.get_model("flights", "Ruta")
        SecuenciaCodigoVuelo = apps_registry.get_model("flights", "SecuenciaCodigoVuelo")
    else:
        from apps.flights.models import Ciudad, Ruta, SecuenciaCodigoVuelo

    ciudades_map = {}
    for c_data in CIUDADES_INICIALES:
        ciudad, _ = Ciudad.objects.update_or_create(nombre=c_data["nombre"], defaults=c_data)
        ciudades_map[ciudad.nombre] = ciudad

    for origen_nombre, destino_nombre, duracion in RUTAS_INICIALES:
        origen = ciudades_map.get(origen_nombre)
        destino = ciudades_map.get(destino_nombre)
        if origen and destino:
            tipo = "INTERNACIONAL" if destino.destino_internacional else "NACIONAL"
            Ruta.objects.update_or_create(
                origen=origen,
                destino=destino,
                defaults={"tipo_vuelo": tipo, "duracion_min": duracion, "activa": True},
            )

    SecuenciaCodigoVuelo.objects.get_or_create(prefijo="XX", defaults={"ultimo_consecutivo": 0})
