from datetime import date

from django.conf import settings
from django.db import models

from apps.flights.models import ClaseTiquete, Silla, Vuelo


class TipoTrayecto(models.TextChoices):
    UNICO = "UNICO", "Trayecto único (Solo ida)"
    COMPLETO = "COMPLETO", "Trayecto completo (Ida y regreso)"


class EstadoReserva(models.TextChoices):
    VIGENTE = "VIGENTE", "Vigente"
    COMPRADA = "COMPRADA", "Convertida en compra"
    VENCIDA = "VENCIDA", "Vencida"
    CANCELADA = "CANCELADA", "Cancelada"


class EstadoCompra(models.TextChoices):
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    CANCELADA = "CANCELADA", "Cancelada"


class EstadoTiquete(models.TextChoices):
    ACTIVO = "ACTIVO", "Activo"
    CANCELADO = "CANCELADO", "Cancelado"


class EstadoCheckin(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    CONFIRMADO = "CONFIRMADO", "Confirmado"


class Viajero(models.Model):
    documento = models.CharField(max_length=30, db_index=True)
    tipo_documento = models.CharField(max_length=20, default="CC")
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=20)
    telefono = models.CharField(max_length=30)
    correo = models.EmailField()
    nombre_contacto = models.CharField(max_length=100, blank=True, default="")
    telefono_contacto = models.CharField(max_length=30, blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Viajero"
        verbose_name_plural = "Viajeros"

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.tipo_documento}: {self.documento})"

    def calcular_edad(self, fecha_referencia: date) -> int:
        born = self.fecha_nacimiento
        if isinstance(born, str):
            born = date.fromisoformat(born)
        if isinstance(fecha_referencia, str):
            fecha_referencia = date.fromisoformat(fecha_referencia)
        return (
            fecha_referencia.year
            - born.year
            - ((fecha_referencia.month, fecha_referencia.day) < (born.month, born.day))
        )

    def es_mayor_de_edad(self, fecha_referencia: date) -> bool:
        return self.calcular_edad(fecha_referencia) >= 18


class Reserva(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservas"
    )
    vuelo = models.ForeignKey(
        Vuelo, on_delete=models.PROTECT, related_name="reservas_ida"
    )
    vuelo_regreso = models.ForeignKey(
        Vuelo, on_delete=models.PROTECT, null=True, blank=True, related_name="reservas_regreso"
    )
    tipo_trayecto = models.CharField(
        max_length=20, choices=TipoTrayecto.choices, default=TipoTrayecto.UNICO
    )
    clase = models.CharField(max_length=20, choices=ClaseTiquete.choices)
    limite_vigencia = models.DateTimeField(db_index=True)
    estado = models.CharField(
        max_length=20, choices=EstadoReserva.choices, default=EstadoReserva.VIGENTE, db_index=True
    )
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ["-creada_en"]

    def __str__(self):
        return f"Reserva #{self.pk} - {self.cliente.email} ({self.estado})"


class ReservaViajero(models.Model):
    reserva = models.ForeignKey(
        Reserva, on_delete=models.CASCADE, related_name="viajeros_reserva"
    )
    viajero = models.ForeignKey(
        Viajero, on_delete=models.PROTECT, related_name="reservas_asociadas"
    )

    class Meta:
        verbose_name = "Viajero en Reserva"
        verbose_name_plural = "Viajeros en Reserva"
        constraints = [
            models.UniqueConstraint(
                fields=["reserva", "viajero"], name="unique_viajero_por_reserva"
            )
        ]


class Compra(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="compras"
    )
    localizador = models.CharField(max_length=6, unique=True, db_index=True)
    valor_pagado = models.DecimalField(max_digits=14, decimal_places=2)
    tipo_trayecto = models.CharField(
        max_length=20, choices=TipoTrayecto.choices, default=TipoTrayecto.UNICO
    )
    estado = models.CharField(
        max_length=20, choices=EstadoCompra.choices, default=EstadoCompra.CONFIRMADA, db_index=True
    )
    reserva_origen = models.ForeignKey(
        Reserva, on_delete=models.SET_NULL, null=True, blank=True, related_name="compras_derivadas"
    )
    fecha_compra = models.DateTimeField(auto_now_add=True)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ["-fecha_compra"]

    def __str__(self):
        return f"Compra {self.localizador} - {self.cliente.email} (${self.valor_pagado})"


class Tiquete(models.Model):
    compra = models.ForeignKey(
        Compra, on_delete=models.PROTECT, related_name="tiquetes"
    )
    vuelo = models.ForeignKey(
        Vuelo, on_delete=models.PROTECT, related_name="tiquetes"
    )
    viajero = models.ForeignKey(
        Viajero, on_delete=models.PROTECT, related_name="tiquetes"
    )
    silla = models.ForeignKey(
        Silla, on_delete=models.PROTECT, related_name="tiquetes"
    )
    clase = models.CharField(max_length=20, choices=ClaseTiquete.choices)
    precio_pagado = models.DecimalField(max_digits=12, decimal_places=2)
    codigo_tiquete = models.CharField(max_length=25, unique=True, db_index=True)
    numero_cambios_silla = models.PositiveIntegerField(default=0)
    estado_checkin = models.CharField(
        max_length=20, choices=EstadoCheckin.choices, default=EstadoCheckin.PENDIENTE
    )
    fecha_checkin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=EstadoTiquete.choices, default=EstadoTiquete.ACTIVO, db_index=True
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tiquete"
        verbose_name_plural = "Tiquetes"
        ordering = ["-creado_en"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(numero_cambios_silla__lte=1),
                name="check_maximo_un_cambio_silla",
            )
        ]

    def __str__(self):
        silla_num = self.silla.numero_silla if self.silla else "S/A"
        return f"Tiquete {self.codigo_tiquete} - Silla {silla_num} ({self.viajero.nombres})"

    @property
    def checkin_confirmado(self) -> bool:
        return self.estado_checkin == EstadoCheckin.CONFIRMADO



class HistorialBusqueda(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="busquedas_historial"
    )
    origen = models.CharField(max_length=80)
    destino = models.CharField(max_length=80)
    tipo_trayecto = models.CharField(max_length=20, default=TipoTrayecto.UNICO)
    fecha_salida = models.DateField(null=True, blank=True)
    fecha_regreso = models.DateField(null=True, blank=True)
    pasajeros = models.PositiveIntegerField(default=1)
    clase = models.CharField(max_length=20, blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de Búsqueda"
        verbose_name_plural = "Historial de Búsquedas"
        ordering = ["-creado_en"]
