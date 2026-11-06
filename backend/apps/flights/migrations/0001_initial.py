from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Ciudad",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("codigo_pais", models.CharField(max_length=2)),
                ("nombre", models.CharField(max_length=80, unique=True)),
                ("zona_horaria", models.CharField(max_length=64)),
                ("es_capital_principal", models.BooleanField(default=False)),
                ("origen_internacional", models.BooleanField(default=False)),
                ("destino_internacional", models.BooleanField(default=False)),
                ("activa", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Ciudad",
                "verbose_name_plural": "Ciudades",
                "ordering": ["nombre"],
            },
        ),
        migrations.CreateModel(
            name="SecuenciaCodigoVuelo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("prefijo", models.CharField(default="XX", max_length=2, unique=True)),
                ("ultimo_consecutivo", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Secuencia de código de vuelo",
            },
        ),
        migrations.CreateModel(
            name="Ruta",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "tipo_vuelo",
                    models.CharField(
                        choices=[("NACIONAL", "Nacional"), ("INTERNACIONAL", "Internacional")],
                        max_length=15,
                    ),
                ),
                (
                    "duracion_min",
                    models.PositiveIntegerField(help_text="Duración estimada del vuelo en minutos"),
                ),
                ("activa", models.BooleanField(default=True)),
                (
                    "destino",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rutas_destino",
                        to="flights.ciudad",
                    ),
                ),
                (
                    "origen",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rutas_origen",
                        to="flights.ciudad",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ruta",
                "verbose_name_plural": "Rutas",
                "ordering": ["origen__nombre", "destino__nombre"],
            },
        ),
        migrations.CreateModel(
            name="Vuelo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("codigo_vuelo", models.CharField(db_index=True, max_length=6, unique=True)),
                (
                    "tipo_vuelo",
                    models.CharField(
                        choices=[("NACIONAL", "Nacional"), ("INTERNACIONAL", "Internacional")],
                        max_length=15,
                    ),
                ),
                ("fecha_salida", models.DateField()),
                ("hora_salida", models.TimeField()),
                ("salida_utc", models.DateTimeField(db_index=True)),
                ("tiempo_vuelo_min", models.PositiveIntegerField()),
                ("fecha_llegada", models.DateField()),
                ("hora_llegada", models.TimeField()),
                ("llegada_utc", models.DateTimeField()),
                (
                    "costo_persona_economica",
                    models.DecimalField(decimal_places=2, max_digits=12),
                ),
                (
                    "costo_persona_primera",
                    models.DecimalField(decimal_places=2, max_digits=12),
                ),
                ("capacidad_total", models.PositiveIntegerField()),
                ("cupos_primera_clase", models.PositiveIntegerField()),
                ("cupos_economica", models.PositiveIntegerField()),
                ("cupos_disponibles_primera", models.PositiveIntegerField()),
                ("cupos_disponibles_economica", models.PositiveIntegerField()),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PROGRAMADO", "Programado"),
                            ("REALIZADO", "Realizado"),
                            ("CANCELADO", "Cancelado"),
                        ],
                        db_index=True,
                        default="PROGRAMADO",
                        max_length=20,
                    ),
                ),
                ("motivo_cancelacion", models.TextField(blank=True, default="")),
                ("cancelado_en", models.DateTimeField(blank=True, null=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                (
                    "cancelado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="vuelos_cancelados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "creado_por",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="vuelos_creados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ruta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="vuelos",
                        to="flights.ruta",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vuelo",
                "verbose_name_plural": "Vuelos",
                "ordering": ["-salida_utc"],
            },
        ),
        migrations.CreateModel(
            name="Silla",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("numero_silla", models.PositiveIntegerField()),
                (
                    "clase",
                    models.CharField(
                        choices=[
                            ("PRIMERA_CLASE", "Primera Clase"),
                            ("ECONOMICA", "Clase Económica"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("DISPONIBLE", "Disponible"),
                            ("RESERVADA", "Reservada"),
                            ("OCUPADA", "Ocupada"),
                        ],
                        default="DISPONIBLE",
                        max_length=20,
                    ),
                ),
                ("espacio_extra", models.BooleanField(default=False)),
                (
                    "vuelo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sillas",
                        to="flights.vuelo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Silla",
                "verbose_name_plural": "Sillas",
                "ordering": ["vuelo", "numero_silla"],
            },
        ),
        migrations.CreateModel(
            name="NoticiaVuelo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("titulo", models.CharField(max_length=200)),
                ("contenido", models.TextField()),
                ("tipo", models.CharField(default="VUELO_PROGRAMADO", max_length=30)),
                ("vigente", models.BooleanField(default=True)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                (
                    "vuelo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="noticias",
                        to="flights.vuelo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Noticia de Vuelo",
                "verbose_name_plural": "Noticias de Vuelos",
                "ordering": ["-creada_en"],
            },
        ),
        migrations.CreateModel(
            name="NotificacionAfectacion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("destinatario", models.EmailField(max_length=254)),
                (
                    "tipo_afectacion",
                    models.CharField(
                        choices=[
                            ("REPROGRAMACION", "Reprogramación"),
                            ("CANCELACION", "Cancelación"),
                        ],
                        max_length=30,
                    ),
                ),
                ("motivo", models.TextField(blank=True, default="")),
                ("datos_adicionales", models.JSONField(default=dict)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                (
                    "vuelo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notificaciones_afectacion",
                        to="flights.vuelo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Notificación de Afectación",
                "verbose_name_plural": "Notificaciones de Afectación",
                "ordering": ["-creada_en"],
            },
        ),
        migrations.CreateModel(
            name="BitacoraVuelo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "tipo_evento",
                    models.CharField(
                        choices=[
                            ("PROGRAMACION", "Programación de vuelo"),
                            ("EDICION", "Edición de vuelo"),
                            ("CANCELACION", "Cancelación de vuelo"),
                        ],
                        max_length=30,
                    ),
                ),
                ("ip_origen", models.CharField(blank=True, default="", max_length=45)),
                ("detalles", models.JSONField(default=dict)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "vuelo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="eventos_bitacora",
                        to="flights.vuelo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Bitácora de Vuelo",
                "verbose_name_plural": "Eventos de Bitácora de Vuelos",
                "ordering": ["-creado_en"],
            },
        ),
        migrations.AddConstraint(
            model_name="ruta",
            constraint=models.UniqueConstraint(
                fields=("origen", "destino"), name="unique_ruta_origen_destino"
            ),
        ),
        migrations.AddConstraint(
            model_name="ruta",
            constraint=models.CheckConstraint(
                condition=models.Q(("origen", models.F("destino")), _negated=True),
                name="check_ruta_origen_distinto_destino",
            ),
        ),
        migrations.AddConstraint(
            model_name="vuelo",
            constraint=models.CheckConstraint(
                condition=models.Q(("costo_persona_economica__gt", Decimal("0.00"))),
                name="check_vuelo_costo_economica_gt_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="vuelo",
            constraint=models.CheckConstraint(
                condition=models.Q(("costo_persona_primera__gt", Decimal("0.00"))),
                name="check_vuelo_costo_primera_gt_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="vuelo",
            constraint=models.CheckConstraint(
                condition=models.Q(("cupos_disponibles_primera__gte", 0)),
                name="check_vuelo_cupos_disponibles_primera_gte_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="vuelo",
            constraint=models.CheckConstraint(
                condition=models.Q(("cupos_disponibles_economica__gte", 0)),
                name="check_vuelo_cupos_disponibles_economica_gte_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="silla",
            constraint=models.UniqueConstraint(
                fields=("vuelo", "numero_silla"), name="unique_vuelo_silla"
            ),
        ),
    ]
