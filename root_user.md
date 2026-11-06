# Gestión y Creación del Usuario ROOT (HU-008 / HU-009)

Este documento detalla el funcionamiento, la creación y la administración de la cuenta con rol **ROOT** en la plataforma Aerolínea Web, conforme a las decisiones de arquitectura y seguridad del proyecto (DEC-10, DEC-15 y DEC-21).

---

## 1. Principios de Seguridad y Modelo de Datos

1. **Sin credenciales por defecto:**
   Por lineamientos de seguridad, el sistema **no incluye contraseñas quemadas ni usuarios creados automáticamente** en migraciones o semillas fijas.
2. **Cuenta Única:**
   La base de datos en PostgreSQL impone la restricción `users_single_root_account`, garantizando que solo pueda existir una única cuenta con rol `ROOT` en todo el sistema.
3. **Identificación por `root_id`:**
   A diferencia de los roles `CLIENTE` y `ADMINISTRADOR` (quienes inician sesión mediante su correo electrónico), **ROOT se autentica exclusivamente a través de su `root_id`** (DEC-15).
4. **Billetera Asociada:**
   Al crear la cuenta ROOT, se inicializa automáticamente su billetera con saldo en cero en una transacción atómica.

---

## 2. Creación del Usuario ROOT

La inicialización de la cuenta ROOT se realiza mediante el comando interactivo de gestión de Django: `create_root`.

### Pasos con Docker Compose (Recomendado)

1. Asegúrate de que los contenedores del backend y la base de datos estén activos:
   ```bash
   # En Windows PowerShell
   .\dev.ps1

   # O en Bash / WSL / Linux
   ./dev.sh
   ```

2. Ejecuta el comando de aprovisionamiento en el contenedor del backend:
   ```bash
   docker compose exec backend python manage.py create_root --root-id root
   ```

3. El sistema solicitará la contraseña de forma interactiva en la terminal:
   ```text
   Contraseña: 
   Confirme la contraseña: 
   ```
   *Si la contraseña es válida y coincide, verás el mensaje:*
   ```text
   Cuenta ROOT creada con su billetera.
   ```

### Opciones y Parámetros del Comando

* `--root-id <identificador>`: **(Obligatorio)** Identificador único de acceso (ejemplo: `root` o `superadmin`). Sensible a mayúsculas y sin espacios al inicio/final.
* `--email <correo>`: **(Opcional)** Asocia un correo electrónico a la cuenta ROOT (ejemplo: `--email root@example.invalid`). Permite habilitar flujos de recuperación de contraseña vía correo.

> [!NOTE]
> El comando `create_root` es **idempotente**. Si ya existe una cuenta ROOT registrada, no modificará las credenciales existentes y notificará: `Ya existe la cuenta ROOT; no se modificó.`

---

## 3. Requisitos de la Contraseña

Toda contraseña asignada a ROOT debe cumplir los validadores configurados en el sistema:
* **Longitud mínima:** Al menos **8 caracteres**.
* **Contenido:** Debe incluir **al menos un número** (`0-9`).
* **Seguridad externa:** Se valida contra la API de *Pwned Passwords* mediante consulta por rango SHA-1 para asegurar que no sea una credencial públicamente comprometida.

---

## 4. Inicio de Sesión (Login)

### Desde la Interfaz Web (Frontend)

1. Ingresa a la pantalla de inicio de sesión: [http://localhost:5173/login](http://localhost:5173/login).
2. En el campo **"Correo electrónico o Usuario Root"**, ingresa el `root_id` exacto (por ejemplo: `root`).
3. Ingresa la contraseña establecida.
4. Al autenticarte, el encabezado mostrará el distintivo **ROOT** y tendrás acceso a las funcionalidades exclusivas de HU-009 (alta y listado paginado de administradores).

### Mediante la API HTTP (REST)

Se envía una solicitud `POST` a `/api/v1/auth/login/` con el encabezado `X-CSRFToken`:

```json
{
  "root_id": "root",
  "password": "TuContraseñaSegura123"
}
```

*Respuesta exitosa (200 OK):*
```json
{
  "authenticated": true,
  "role": "ROOT",
  "is_email_verified": false
}
```

---

## 5. Mantenimiento y Recuperación de Emergencia

### Opción A: Cambio de contraseña propia autenticado (HU-009)

Con una sesión activa de ROOT, se puede cambiar la contraseña mediante el endpoint `POST /api/v1/users/root/password/`:
* Requiere: `current_password`, `password` (nueva) y `password_confirmation`.
* Al cambiar la contraseña, todas las demás sesiones activas quedan invalidadas inmediatamente.

### Opción B: Restablecimiento manual desde Django Shell

Si olvidaste las credenciales de ROOT en tu entorno de desarrollo, puedes consultar el identificador o asignar una nueva clave directamente desde el shell de Django:

1. Abre el shell interactivo:
   ```bash
   docker compose exec backend python manage.py shell
   ```

2. Ejecuta el siguiente script en Python:
   ```python
   from apps.users.models import User

   root = User.objects.filter(role=User.Role.ROOT).first()
   if root:
       print(f"El identificador de ROOT actual es: {root.root_id}")
       root.set_password("NuevaContraseña123")
       root.save()
       print("Contraseña actualizada con éxito.")
   else:
       print("No existe un usuario ROOT en la base de datos.")

   exit()
   ```

---

## 6. Datos Sintéticos en Pruebas Automatizadas

En la suite de pruebas unitarias e integración (`tests/test_administration.py`), se utilizan los siguientes valores simulados:
* **`root_id`:** `root-test`
* **Contraseña:** `acceso-largo-sintetico-para-pruebas-2026`

