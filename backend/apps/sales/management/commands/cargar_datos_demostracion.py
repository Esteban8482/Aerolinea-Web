from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.flights.catalogo import cargar_catalogo
from apps.flights.models import Ciudad, EstadoVuelo, Vuelo
from apps.flights.services import programar_vuelo
from apps.sales.models import Compra, Reserva
from apps.sales.services import comprar_tiquetes, crear_reserva
from apps.users.models import User
from apps.wallets.models import Wallet
from apps.wallets.services import depositar


class Command(BaseCommand):
    help = "Carga datos de prueba completos para vuelos, usuarios, billeteras, reservas y compras."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Cargando catálogo base de ciudades y rutas...")
        cargar_catalogo()

        # 1. Crear usuarios de demostración si no existen
        admin, _ = User.objects.get_or_create(
            email="admin.demo@aerolinea.local",
            defaults={
                "role": User.Role.ADMINISTRADOR,
                "first_name": "Admin",
                "last_name": "Demo",
                "is_email_verified": True,
            },
        )
        if not admin.has_usable_password():
            admin.set_password("AdminDemo2026*")
            admin.save()

        cliente1, _ = User.objects.get_or_create(
            email="carlos.viajero@aerolinea.local",
            defaults={
                "role": User.Role.CLIENTE,
                "username": "carlos_viajero",
                "first_name": "Carlos",
                "last_name": "Gómez",
                "document_number": "1002003001",
                "birth_date": date(1989, 4, 12),
                "birth_place": "Pereira",
                "billing_address": "Carrera 7 # 15-20",
                "gender": "M",
                "is_email_verified": True,
            },
        )
        if not cliente1.has_usable_password():
            cliente1.set_password("CarlosViajero2026*")
            cliente1.save()

        cliente2, _ = User.objects.get_or_create(
            email="maria.turista@aerolinea.local",
            defaults={
                "role": User.Role.CLIENTE,
                "username": "maria_turista",
                "first_name": "María",
                "last_name": "Rodríguez",
                "document_number": "1002003002",
                "birth_date": date(1995, 8, 24),
                "birth_place": "Bogotá",
                "billing_address": "Calle 100 # 19-45",
                "gender": "F",
                "is_email_verified": True,
            },
        )
        if not cliente2.has_usable_password():
            cliente2.set_password("MariaTurista2026*")
            cliente2.save()

        # 2. Billeteras con saldo
        w1, _ = Wallet.objects.get_or_create(user=cliente1)
        if w1.balance < Decimal("1000000.00"):
            depositar(w1.pk, Decimal("3000000.00"), "Saldo demo inicial")

        w2, _ = Wallet.objects.get_or_create(user=cliente2)
        if w2.balance < Decimal("1000000.00"):
            depositar(w2.pk, Decimal("5000000.00"), "Saldo demo inicial")

        # 3. Vuelos programados
        bogota = Ciudad.objects.get(nombre="Bogotá")
        pereira = Ciudad.objects.get(nombre="Pereira")
        cartagena = Ciudad.objects.get(nombre="Cartagena")
        madrid = Ciudad.objects.get(nombre="Madrid")

        hoy = date.today()

        # Vuelo 1: PEI -> BOG (mañana)
        if not Vuelo.objects.filter(
            ruta__origen=pereira,
            ruta__destino=bogota,
            fecha_salida=hoy + timedelta(days=2),
        ).exists():
            vuelo1 = programar_vuelo(
                origen_id=pereira.pk,
                destino_id=bogota.pk,
                fecha_salida=hoy + timedelta(days=2),
                hora_salida=time(8, 30),
                costo_persona_economica=Decimal("160000.00"),
                costo_persona_primera=Decimal("240000.00"),
                actor=admin,
            )
            self.stdout.write(f"Creado vuelo {vuelo1.codigo_vuelo} (PEI -> BOG)")

        # Vuelo 2: BOG -> PEI (regreso)
        if not Vuelo.objects.filter(
            ruta__origen=bogota,
            ruta__destino=pereira,
            fecha_salida=hoy + timedelta(days=6),
        ).exists():
            vuelo2 = programar_vuelo(
                origen_id=bogota.pk,
                destino_id=pereira.pk,
                fecha_salida=hoy + timedelta(days=6),
                hora_salida=time(17, 15),
                costo_persona_economica=Decimal("170000.00"),
                costo_persona_primera=Decimal("255000.00"),
                actor=admin,
            )
            self.stdout.write(f"Creado vuelo {vuelo2.codigo_vuelo} (BOG -> PEI)")

        # Vuelo 3: BOG -> CTG
        if not Vuelo.objects.filter(
            ruta__origen=bogota,
            ruta__destino=cartagena,
            fecha_salida=hoy + timedelta(days=4),
        ).exists():
            vuelo3 = programar_vuelo(
                origen_id=bogota.pk,
                destino_id=cartagena.pk,
                fecha_salida=hoy + timedelta(days=4),
                hora_salida=time(11, 0),
                costo_persona_economica=Decimal("210000.00"),
                costo_persona_primera=Decimal("315000.00"),
                actor=admin,
            )
            self.stdout.write(f"Creado vuelo {vuelo3.codigo_vuelo} (BOG -> CTG)")

        # Vuelo 4: BOG -> MAD (Internacional)
        if not Vuelo.objects.filter(
            ruta__origen=bogota,
            ruta__destino=madrid,
            fecha_salida=hoy + timedelta(days=10),
        ).exists():
            vuelo4 = programar_vuelo(
                origen_id=bogota.pk,
                destino_id=madrid.pk,
                fecha_salida=hoy + timedelta(days=10),
                hora_salida=time(20, 45),
                costo_persona_economica=Decimal("2800000.00"),
                costo_persona_primera=Decimal("4200000.00"),
                actor=admin,
            )
            self.stdout.write(f"Creado vuelo {vuelo4.codigo_vuelo} (BOG -> MAD)")

        # 4. Crear una compra de prueba para Carlos
        vuelo_compra = Vuelo.objects.filter(
            ruta__origen=pereira,
            ruta__destino=bogota,
            estado=EstadoVuelo.PROGRAMADO,
        ).first()
        if vuelo_compra and not Compra.objects.filter(cliente=cliente1).exists():
            compra = comprar_tiquetes(
                cliente=cliente1,
                vuelo_id=vuelo_compra.pk,
                clase="ECONOMICA",
                viajeros_data=[
                    {
                        "documento": "1002003001",
                        "tipo_documento": "CC",
                        "nombres": "Carlos",
                        "apellidos": "Gómez",
                        "fecha_nacimiento": date(1989, 4, 12),
                        "genero": "M",
                        "telefono": "3001234567",
                        "correo": "carlos.viajero@aerolinea.local",
                    }
                ],
            )
            self.stdout.write(f"Creada compra demo #{compra.localizador} con tiquetes asignados.")

        # 5. Crear una reserva de prueba para María
        vuelo_reserva = Vuelo.objects.filter(
            ruta__origen=bogota,
            ruta__destino=cartagena,
            estado=EstadoVuelo.PROGRAMADO,
        ).first()
        if vuelo_reserva and not Reserva.objects.filter(cliente=cliente2).exists():
            reserva = crear_reserva(
                cliente=cliente2,
                vuelo_id=vuelo_reserva.pk,
                clase="ECONOMICA",
                viajeros_data=[
                    {
                        "documento": "1002003002",
                        "tipo_documento": "CC",
                        "nombres": "María",
                        "apellidos": "Rodríguez",
                        "fecha_nacimiento": date(1995, 8, 24),
                        "genero": "F",
                        "telefono": "3109876543",
                        "correo": "maria.turista@aerolinea.local",
                    }
                ],
            )
            self.stdout.write(f"Creada reserva demo #{reserva.pk} para {cliente2.email}.")

        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados exitosamente."))
