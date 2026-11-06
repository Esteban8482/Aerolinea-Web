from decimal import Decimal

from django.conf import settings
from django.db import models


class TipoVuelo(models.TextChoices):
    NACIONAL = "NACIONAL", "Nacional"
    INTERNACIONAL = "INTERNACIONAL", "Internacional"


class EstadoVuelo(models.TextChoices):
    PROGRAMADO = "PROGRAMADO", "Programado"
    REALIZADO = "REALIZADO", "Realizado"
    CANCELADO = "CANCELADO", "Cancelado"


class ClaseTiquete(models.TextChoices):
    PRIMERA_CLASE = "PRIMERA_CLASE", "Primera Clase"
    ECONOMICA = "ECONOMICA", "Clase Económica"


class EstadoSilla(models.TextChoices):
    DISPONIBLE = "DISPONIBLE", "Disponible"
    RESERVADA = "RESERVADA", "Reservada"
    OCUPADA = "OCUPADA", "Ocupada"


class Ciudad(models.Model):
    codigo_pais = models.CharField(max_length=2)
    nombre = models.CharField(max_length=80, unique=True)
    zona_horaria = models.CharField(max_length=64)
    es_capital_principal = models.BooleanField(default=False)
    origen_internacional = models.BooleanField(default=False)
    destino_internacional = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ciudad"
        verbose_name_plural = "Ciudades"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo_pais})"


class Ruta(models.Model):
    origen = models.ForeignKey(Ciudad, on_delete=models.PROTECT, related_name="rutas_origen")
    destino = models.ForeignKey(Ciudad, on_delete=models.PROTECT, related_name="rutas_destino")
    tipo_vuelo = models.CharField(max_length=15, choices=TipoVuelo.choices)
    duracion_min = models.PositiveIntegerField(help_text="Duración estimada del vuelo en minutos")
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ruta"
        verbose_name_plural = "Rutas"
        constraints = [
            models.UniqueConstraint(
                fields=["origen", "destino"], name="unique_ruta_origen_destino"
            ),
            models.CheckConstraint(
                condition=~models.Q(origen=models.F("destino")),
                name="check_ruta_origen_distinto_destino",
            ),
        ]
        ordering = ["origen__nombre", "destino__nombre"]

    def __str__(self):
        return (
            f"{self.origen.nombre} -> {self.destino.nombre} "
            f"({self.tipo_vuelo}, {self.duracion_min}m)"
        )


class SecuenciaCodigoVuelo(models.Model):
    """Contador preexistente y atómico en base de datos para generar códigos según DEC-01."""

    prefijo = models.CharField(max_length=2, default="XX", unique=True)
    ultimo_consecutivo = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Secuencia de código de vuelo"


class Vuelo(models.Model):
    codigo_vuelo = models.CharField(max_length=6, unique=True, db_index=True)
    ruta = models.ForeignKey(Ruta, on_delete=models.PROTECT, related_name="vuelos")
    tipo_vuelo = models.CharField(max_length=15, choices=TipoVuelo.choices)

    # Horarios de salida (local origen y UTC)
    fecha_salida = models.DateField()
    hora_salida = models.TimeField()
    salida_utc = models.DateTimeField(db_index=True)

    # Duración y horarios de llegada (local destino y UTC)
    tiempo_vuelo_min = models.PositiveIntegerField()
    fecha_llegada = models.DateField()
    hora_llegada = models.TimeField()
    llegada_utc = models.DateTimeField()

    # Tarifas base
    costo_persona_economica = models.DecimalField(max_digits=12, decimal_places=2)
    costo_persona_primera = models.DecimalField(max_digits=12, decimal_places=2)

    # Capacidad y cupos
    capacidad_total = models.PositiveIntegerField()
    cupos_primera_clase = models.PositiveIntegerField()
    cupos_economica = models.PositiveIntegerField()
    cupos_disponibles_primera = models.PositiveIntegerField()
    cupos_disponibles_economica = models.PositiveIntegerField()

    # Estado y auditoría del vuelo
    estado = models.CharField(
        max_length=20, choices=EstadoVuelo.choices, default=EstadoVuelo.PROGRAMADO, db_index=True
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vuelos_creados"
    )
    motivo_cancelacion = models.TextField(blank=True, default="")
    cancelado_en = models.DateTimeField(null=True, blank=True)
    cancelado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vuelos_cancelados",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vuelo"
        verbose_name_plural = "Vuelos"
        ordering = ["-salida_utc"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(costo_persona_economica__gt=Decimal("0.00")),
                name="check_vuelo_costo_economica_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(costo_persona_primera__gt=Decimal("0.00")),
                name="check_vuelo_costo_primera_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(cupos_disponibles_primera__gte=0),
                name="check_vuelo_cupos_disponibles_primera_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(cupos_disponibles_economica__gte=0),
                name="check_vuelo_cupos_disponibles_economica_gte_0",
            ),
        ]

    def __str__(self):
        return (
            f"{self.codigo_vuelo} "
            f"({self.ruta.origen.nombre} -> {self.ruta.destino.nombre}) [{self.estado}]"
        )


class Silla(models.Model):
    vuelo = models.ForeignKey(Vuelo, on_delete=models.CASCADE, related_name="sillas")
    numero_silla = models.PositiveIntegerField()
    clase = models.CharField(max_length=20, choices=ClaseTiquete.choices)
    estado = models.CharField(
        max_length=20, choices=EstadoSilla.choices, default=EstadoSilla.DISPONIBLE
    )
    espacio_extra = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Silla"
        verbose_name_plural = "Sillas"
        ordering = ["vuelo", "numero_silla"]
        constraints = [
            models.UniqueConstraint(fields=["vuelo", "numero_silla"], name="unique_vuelo_silla")
        ]

    def __str__(self):
        return f"{self.vuelo.codigo_vuelo} - Silla {self.numero_silla} ({self.clase})"


class NoticiaVuelo(models.Model):
    vuelo = models.ForeignKey(Vuelo, on_delete=models.CASCADE, related_name="noticias")
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    tipo = models.CharField(max_length=30, default="VUELO_PROGRAMADO")
    vigente = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Noticia de Vuelo"
        verbose_name_plural = "Noticias de Vuelos"
        ordering = ["-creada_en"]


class BitacoraVuelo(models.Model):
    class Evento(models.TextChoices):
        PROGRAMACION = "PROGRAMACION", "Programación de vuelo"
        EDICION = "EDICION", "Edición de vuelo"
        CANCELACION = "CANCELACION", "Cancelación de vuelo"

    vuelo = models.ForeignKey(Vuelo, on_delete=models.CASCADE, related_name="eventos_bitacora")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    tipo_evento = models.CharField(max_length=30, choices=Evento.choices)
    ip_origen = models.CharField(max_length=45, blank=True, default="")
    detalles = models.JSONField(default=dict)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bitácora de Vuelo"
        verbose_name_plural = "Eventos de Bitácora de Vuelos"
        ordering = ["-creado_en"]


class NotificacionAfectacion(models.Model):
    class Tipo(models.TextChoices):
        REPROGRAMACION = "REPROGRAMACION", "Reprogramación"
        CANCELACION = "CANCELACION", "Cancelación"

    vuelo = models.ForeignKey(
        Vuelo, on_delete=models.CASCADE, related_name="notificaciones_afectacion"
    )
    destinatario = models.EmailField()
    tipo_afectacion = models.CharField(max_length=30, choices=Tipo.choices)
    motivo = models.TextField(blank=True, default="")
    datos_adicionales = models.JSONField(default=dict)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificación de Afectación"
        verbose_name_plural = "Notificaciones de Afectación"
        ordering = ["-creada_en"]
