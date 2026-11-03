from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.flights.catalogo import cargar_catalogo
from apps.flights.models import Ciudad, EstadoVuelo, Ruta, Vuelo
from apps.flights.services import cancelar_vuelo, programar_vuelo
from apps.users.models import User
from apps.users.services import provision_root
from apps.wallets.models import Wallet


class Command(BaseCommand):
    help = "Genera datos de prueba para desarrollo local (usuarios y vuelos de prueba)."

    def handle(self, *args, **options):
        del args, options
        self.stdout.write(self.style.NOTICE("==> Sembrando catálogo de ciudades y rutas..."))
        cargar_catalogo()

        # 1. Crear o asegurar usuario ROOT
        root_user, root_created = provision_root(
            root_id="root",
            password="Root12345678!",
            email="root@alas.com",
        )
        if root_created:
            self.stdout.write(self.style.SUCCESS("✓ Usuario ROOT creado (root / Root12345678!)"))
        else:
            self.stdout.write("  Usuario ROOT ya existía.")

        # 2. Crear Administrador de prueba
        admin_user = User.objects.filter(email="admin@alas.com").first()
        if not admin_user:
            admin_user = User.objects.create(
                email="admin@alas.com",
                username="admin_ops",
                first_name="Carlos",
                last_name="Administrador",
                document_number="1000000001",
                role=User.Role.ADMINISTRADOR,
                is_active=True,
                is_staff=False,
                is_superuser=False,
                is_email_verified=True,
            )
            admin_user.set_password("Admin12345!")
            admin_user.save()
            Wallet.objects.get_or_create(user=admin_user, defaults={"balance": Decimal("0.00")})
            self.stdout.write(self.style.SUCCESS("✓ Administrador creado (admin@alas.com / Admin12345!)"))
        else:
            self.stdout.write("  Administrador admin@alas.com ya existía.")

        # 3. Crear Cliente de prueba con saldo en billetera
        cliente_user = User.objects.filter(email="cliente@alas.com").first()
        if not cliente_user:
            cliente_user = User.objects.create(
                email="cliente@alas.com",
                username="mariana_rios",
                first_name="Mariana",
                last_name="Ríos",
                document_number="1088123456",
                role=User.Role.CLIENTE,
                is_active=True,
                is_staff=False,
                is_superuser=False,
                is_email_verified=True,
            )
            cliente_user.set_password("Cliente12345!")
            cliente_user.save()
            Wallet.objects.get_or_create(user=cliente_user, defaults={"balance": Decimal("5000000.00")})
            self.stdout.write(self.style.SUCCESS("✓ Cliente creado (cliente@alas.com / Cliente12345! - Saldo: $5.000.000 COP)"))
        else:
            self.stdout.write("  Cliente cliente@alas.com ya existía.")

        # 4. Crear vuelos de prueba si la tabla está vacía o tiene pocos registros
        if Vuelo.objects.count() >= 5:
            self.stdout.write("  Ya existen suficientes vuelos de prueba en la base de datos.")
            return

        self.stdout.write(self.style.NOTICE("==> Generando vuelos de prueba comerciales..."))

        bogota = Ciudad.objects.get(nombre="Bogotá")
        pereira = Ciudad.objects.get(nombre="Pereira")
        medellin = Ciudad.objects.get(nombre="Medellín")
        cartagena = Ciudad.objects.get(nombre="Cartagena")
        madrid = Ciudad.objects.get(nombre="Madrid")
        miami = Ciudad.objects.get(nombre="Miami")

        today = date.today()

        # Vuelo 1: Nacional Programado (Bogotá -> Pereira)
        v1 = programar_vuelo(
            origen_id=bogota.id,
            destino_id=pereira.id,
            fecha_salida=today + timedelta(days=2),
            hora_salida=time(9, 0),
            costo_persona_economica=Decimal("150000.00"),
            costo_persona_primera=Decimal("225000.00"),
            actor=admin_user,
        )
        self.stdout.write(self.style.SUCCESS(f"✓ Vuelo programado {v1.codigo_vuelo} (Bogotá -> Pereira)"))

        # Vuelo 2: Nacional Programado (Pereira -> Bogotá)
        v2 = programar_vuelo(
            origen_id=pereira.id,
            destino_id=bogota.id,
            fecha_salida=today + timedelta(days=3),
            hora_salida=time(15, 30),
            costo_persona_economica=Decimal("155000.00"),
            costo_persona_primera=Decimal("230000.00"),
            actor=admin_user,
        )
        self.stdout.write(self.style.SUCCESS(f"✓ Vuelo programado {v2.codigo_vuelo} (Pereira -> Bogotá)"))

        # Vuelo 3: Internacional Programado (Bogotá -> Madrid)
        v3 = programar_vuelo(
            origen_id=bogota.id,
            destino_id=madrid.id,
            fecha_salida=today + timedelta(days=5),
            hora_salida=time(20, 0),
            costo_persona_economica=Decimal("1249000.00"),
            costo_persona_primera=Decimal("1990000.00"),
            actor=admin_user,
        )
        self.stdout.write(self.style.SUCCESS(f"✓ Vuelo programado {v3.codigo_vuelo} (Bogotá -> Madrid)"))

        # Vuelo 4: Internacional Programado (Medellín -> Miami)
        v4 = programar_vuelo(
            origen_id=medellin.id,
            destino_id=miami.id,
            fecha_salida=today + timedelta(days=7),
            hora_salida=time(11, 0),
            costo_persona_economica=Decimal("980000.00"),
            costo_persona_primera=Decimal("1470000.00"),
            actor=admin_user,
        )
        self.stdout.write(self.style.SUCCESS(f"✓ Vuelo programado {v4.codigo_vuelo} (Medellín -> Miami)"))

        # Vuelo 5: Nacional Cancelado (Cartagena -> Bogotá)
        v5 = programar_vuelo(
            origen_id=cartagena.id,
            destino_id=bogota.id,
            fecha_salida=today + timedelta(days=4),
            hora_salida=time(18, 0),
            costo_persona_economica=Decimal("160000.00"),
            costo_persona_primera=Decimal("240000.00"),
            actor=admin_user,
        )
        cancelar_vuelo(
            vuelo_id=v5.id,
            motivo="Mantenimiento preventivo de aeronave.",
            alternativa="REINTEGRO",
            actor=admin_user,
        )
        self.stdout.write(self.style.SUCCESS(f"✓ Vuelo cancelado {v5.codigo_vuelo} (Cartagena -> Bogotá)"))

        # Vuelo 6: Histórico / Realizado (Bogotá -> Medellín)
        v6 = programar_vuelo(
            origen_id=bogota.id,
            destino_id=medellin.id,
            fecha_salida=today + timedelta(days=1),
            hora_salida=time(8, 0),
            costo_persona_economica=Decimal("140000.00"),
            costo_persona_primera=Decimal("210000.00"),
            actor=admin_user,
        )
        # Marcamos como realizado para pruebas de filtrado
        v6.estado = EstadoVuelo.REALIZADO
        v6.save(update_fields=["estado"])
        self.stdout.write(self.style.SUCCESS(f"✓ Vuelo realizado {v6.codigo_vuelo} (Bogotá -> Medellín)"))

        self.stdout.write(self.style.SUCCESS("==> Datos de prueba generados exitosamente."))
