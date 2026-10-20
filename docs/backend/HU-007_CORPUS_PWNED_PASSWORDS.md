# HU-007 — aprovisionamiento del corpus real de Pwned Passwords

Preparado el **2026-10-20**. **No se ejecutaron descarga masiva, transformación del corpus
real ni importación.** No hay corpus en Git, imágenes Docker ni CI. Los datos sintéticos
de pruebas no acreditan un corpus real instalado. La **política de datos aprobada sigue
pendiente**; no cambiar sus flags para ejecutar este procedimiento ni declarar producción
preparada. La verificación de HU-007 en Docker/PostgreSQL 17.11 ya fue comunicada por el
usuario: [reporte y atribución](HU-007.md#verificación-en-dockerpostgresql-1711--ejecutada-por-el-usuario).

## Fuente oficial y contrato inspeccionado

Fuentes consultadas el 2026-10-20:

- [HIBP: descarga offline](https://haveibeenpwned.com/API/v3#DownloadingAllPwnedPasswordsHashes).
- [Descargador oficial](https://github.com/HaveIBeenPwned/PwnedPasswordsDownloader).
- [Paquete 0.5.2608.1930](https://www.nuget.org/packages/haveibeenpwned-downloader/0.5.2608.1930),
  fijado para este procedimiento; necesita SDK .NET 10 para instalarse.

Se usa SHA-1 completo a un archivo con `--single`, paralelismo 4 y hasta 5 reintentos por
prefijo. Según el README oficial, el descargador comprueba `Content-MD5` por rango;
conservar versión, log y código de salida. Son **16^5 = 1.048.576 prefijos** posibles.
No usar NTLM ni búsquedas de contraseñas de cuentas: el trabajo obtiene todos los rangos,
sin enviar credenciales. Se instalará dentro de un contenedor SDK temporal, sin instalar
.NET globalmente en WSL ni incorporarlo al backend. `--tool-path` está documentado en
[.NET CLI](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-tool-install).

Se inspeccionaron `backend/apps/users/password_corpus.py` y
`management/commands/prepare_password_corpus.py`. La entrada es texto ASCII:

- Una línea `SHA1:COUNT` por hash: **40 caracteres hexadecimales completos**, no sufijos.
- `COUNT` decimal positivo, no una contraseña ni el total de registros.
- Orden ascendente estricto **por hash**, sin duplicados; no ordenar por frecuencia.
- Sin cabecera, BOM, líneas vacías ni filas de relleno con contador cero.
- El lector admite LF/CRLF; aquí se normaliza a LF y hex en mayúsculas.

No deduplicar ni filtrar filas inválidas para aparentar éxito. El destino debe ser nuevo,
con padre existente y escribible por `app`; el importador no sobrescribe corpus anteriores.
Produce `sha1.bin` de **20 bytes por hash**, sin contadores, y `manifest.json` con formato,
conteo, SHA-256 del binario, etiqueta, procedencia y `synthetic=false`. La conversión binaria
la realiza el comando existente; la fase externa solo normaliza/ordena. El lector usa
mmap y búsqueda binaria, comprueba integridad y rechaza corpus sintético en producción.
Las contraseñas de cuentas siguen almacenándose mediante Argon2id.

## Estimación antes de descargar

No se dispone de una cantidad exacta del conjunto vivo. Estos son **escenarios de
planificación**, no su conteo actual. Sea `N` el número de hashes y `R` el texto bruto:
reservar conservadoramente `R ≈ 55N` bytes; el binario necesita exactamente `20N` bytes.

| Componente | Presupuesto | Ejemplo N = 1.000 millones |
|---|---:|---:|
| Texto descargado | R | 51,2 GiB |
| Texto normalizado/ordenado | R | 51,2 GiB |
| Reserva para temporales de sort | hasta 2R | 102,4 GiB |
| Nuevo binario Docker | 20N | 18,6 GiB |
| Total conservador sin margen | 4R + 20N | 223,5 GiB |
| Reserva recomendada inicial | margen ≥25 %, redondeado | **300 GiB** |

Para 2.000 millones, reservar aproximadamente **600 GiB**. Una actualización que conserva
un binario anterior similar requiere aproximadamente **330 / 660 GiB**, respectivamente.
Añadir backups, imágenes y demás consumos. La suma es conservadora: temporales y binario
nuevo no coexisten toda la ejecución, pero el plan no depende de borrados automáticos.
Si WSL y Docker usan discos distintos, revisar cada uno: WSL hasta 4R; Docker 20N nuevos
más corpus anteriores y margen.

En esta inspección `df -h . /tmp` mostró **938 GiB disponibles** en el filesystem WSL del
clon. No demuestra espacio físico del host Windows ni del VHDX de Docker Desktop.
Antes de descargar, desde **WSL**:

```bash
df -h . /tmp
docker system df
docker compose exec -T backend df -h /var/lib/aerolinea/passwords
```

Comprobar además el disco que aloja los VHDX en Windows/Docker Desktop. No hacer `prune`,
borrar volúmenes o mover la base para obtener espacio. Si el tamaño supera el escenario,
recalcular antes de seguir. Después de descargar, usar bytes/filas medidos para presupuestar
el ordenamiento y la importación.

## 1. Preparar captura y descargar

Todos los bloques Bash parten de la **raíz del repositorio, en la misma terminal WSL**.
El ordenamiento se hace en almacenamiento Linux. No se modifica `.env` ni sus secretos.

```bash
set -euo pipefail
umask 077
corpus_run="$(pwd)/backend/private-passwords/hibp-$(date -u +%Y%m%dT%H%M%SZ)"
corpus_label="$(basename "$corpus_run")"
mkdir -p backend/private-passwords
mkdir "$corpus_run"
mkdir "$corpus_run/sort-tmp"
git check-ignore "$corpus_run/download.txt" "$corpus_run/ordered.txt"
df -h "$corpus_run"
```

`backend/private-passwords/` ya está excluido por `.gitignore` y `.dockerignore`.
`password_corpus` es un volumen fuera de Git. No usar `git add -f`, subir el corpus a un PR
ni añadirlo al Dockerfile. El directorio nuevo evita sobrescribir otra captura.

**El siguiente bloque descarga el conjunto completo. Ejecutarlo solo después de comprobar
el presupuesto. No se ejecutó en esta preparación.** La etiqueta SDK es mutable: se registra
su digest. No se instala nada globalmente en el host.

```bash
docker pull mcr.microsoft.com/dotnet/sdk:10.0
docker image inspect --format '{{json .RepoDigests}}' mcr.microsoft.com/dotnet/sdk:10.0 > "$corpus_run/sdk-image-digests.json"
date -u +%FT%TZ > "$corpus_run/download-started-at.txt"
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env DOTNET_CLI_HOME=/tmp/hibp-cli \
  --env NUGET_PACKAGES=/tmp/hibp-packages \
  --env DOTNET_CLI_TELEMETRY_OPTOUT=1 \
  --mount "type=bind,source=$corpus_run,target=/corpus" \
  --workdir /corpus \
  mcr.microsoft.com/dotnet/sdk:10.0 sh -eu -c '
    dotnet tool install haveibeenpwned-downloader --version 0.5.2608.1930 --tool-path /tmp/hibp-tool
    /tmp/hibp-tool/haveibeenpwned-downloader /corpus/download --single --parallelism 4 --max-retries 5
  ' > "$corpus_run/download.log" 2>&1
date -u +%FT%TZ > "$corpus_run/download-finished-at.txt"
test -s "$corpus_run/download.txt"
```

Conservar log exitoso y versión. Si falla/interrumpe, no importar el parcial: revisar el
error/espacio y obtener otra captura completa en directorio nuevo. Esta ruta `--single`
no promete reanudación. No ocultar fallos con sobrescritura. Es una captura durante un
intervalo, no una publicación oficial inmutable que corresponda a un instante global.

## 2. Transformación y checksums de origen

```bash
wc -l -c "$corpus_run/download.txt" > "$corpus_run/download-size.txt"
df -h "$corpus_run"
```

Con R y N medidos, queda por reservar R para texto ordenado, hasta 2R para temporales,
20N para binario y margen. `--buffer-size=1G` es un objetivo de buffer, no un límite de
RAM estricto. Ajustarlo a la memoria disponible. No presumir orden estricto por usar
`--single`; no usar `sort -u` para esconder duplicados.

```bash
python3 -c '
import re, sys
pattern = re.compile(rb"[0-9A-F]{40}:[0-9]+")
with open(sys.argv[1], "rb") as incoming:
    for number, line in enumerate(incoming, 1):
        value = line.rstrip(b"\r\n").removeprefix(b"\xef\xbb\xbf").upper()
        if not pattern.fullmatch(value) or int(value[41:]) < 1:
            raise SystemExit(f"Formato no válido en línea {number}; captura rechazada.")
        sys.stdout.buffer.write(value + b"\n")
' "$corpus_run/download.txt" \
  | LC_ALL=C sort --field-separator=: --key=1,1 --parallel=2 \
      --buffer-size=1G --temporary-directory="$corpus_run/sort-tmp" \
  > "$corpus_run/ordered.part"
mv "$corpus_run/ordered.part" "$corpus_run/ordered.txt"
LC_ALL=C sort --check --field-separator=: --key=1,1 "$corpus_run/ordered.txt"
corpus_count="$(wc -l < "$corpus_run/ordered.txt")"
test "$corpus_count" -gt 0
test "$(wc -l < "$corpus_run/download.txt")" -eq "$corpus_count"
printf '%s\n' "$corpus_count" > "$corpus_run/expected-count.txt"
(
  cd "$corpus_run"
  sha256sum download.txt ordered.txt > sources.sha256
  sha256sum --check sources.sha256
)
```

El normalizador conserva todas las filas, valida su formato/contador y retira un BOM
UTF-8 únicamente al comienzo de cada línea, además de normalizar mayúsculas y saltos.
Esto cubre marcadores de codificación al concatenar rangos; no elimina bytes arbitrarios
ni tolera encabezados. El [código oficial de escritura de rangos](https://github.com/HaveIBeenPwned/PwnedPasswordsDownloader/blob/main/src/HaveIBeenPwned.PwnedPasswords.Downloader/Program.cs)
usa escritores UTF-8. El importador verificará además formato y unicidad: investigar
cualquier rechazo, sin filtrar contenido. Este flujo no usa archivo comprimido ni necesita 7-Zip; no se asume
el tamaño de un `.7z` histórico como si fuese el actual.

Los SHA-256 locales identifican los archivos y detectan cambios posteriores; **no son
una firma independiente del editor**. No se inventa un checksum oficial para el conjunto
vivo completo. La procedencia combina HTTPS oficial, herramienta fijada y verificaciones
por rango, log, fechas, conteo y checksums propios.

## 3. Montaje de entrada e importación

El backend corre como `app`. El directorio que se monta debe poder atravesarlo ese UID;
solo el texto ordenado/conteo necesitan ser legibles. El padre WSL privado se conserva.
Son hashes del conjunto público, no credenciales en texto plano. El bind será solo lectura.

```bash
chmod 0755 "$corpus_run"
chmod 0444 "$corpus_run/ordered.txt" "$corpus_run/expected-count.txt"
docker compose -f compose.yaml run --rm --no-deps \
  --volume "$corpus_run:/corpus-input:ro" \
  backend python manage.py prepare_password_corpus \
  --source /corpus-input/ordered.txt \
  --destination "/var/lib/aerolinea/passwords/$corpus_label" \
  --label "$corpus_label"
```

`python manage.py …` corre **dentro del contenedor**. Reutiliza la imagen y el volumen
`password_corpus` de Compose, sin levantar dependencias, publicar puertos ni migrar la
base. El Dockerfile prepara el padre para `app`. Se usa el Compose base para permitir
**escritura durante importación**; no usar el overlay de solo lectura todavía.
No pasar `--synthetic` ni cambiar la marca de una muestra para promoverla como real:
la marca no prueba procedencia, hace falta el expediente completo.

Revisión sin imprimir credenciales de `.env`:

```bash
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml run --rm --no-deps backend id
docker compose -f compose.yaml run --rm --no-deps backend df -h /var/lib/aerolinea/passwords
```

Si fallan permisos/espacio, resolver el destino; no cambiar recursivamente permisos de
volúmenes ajenos ni reutilizar un directorio existente.

## 4. Verificar el binario y el lector con volumen de solo lectura

Se incorpora [compose.corpus-readonly.yaml](../../compose.corpus-readonly.yaml), optativo:
conserva volumen/destino con `read_only: true` para backend. La combinación por destino
está documentada en [Compose](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/).
No activa producción ni modifica la política.

```bash
docker compose -f compose.yaml -f compose.corpus-readonly.yaml config --quiet
docker compose -f compose.yaml -f compose.corpus-readonly.yaml run --rm --no-deps \
  --env "PASSWORD_CORPUS_DIR=/var/lib/aerolinea/passwords/$corpus_label" \
  --env "CORPUS_EXPECTED_COUNT=$corpus_count" \
  backend python -c '
import hashlib, json, os, time
from pathlib import Path
started = time.perf_counter()
root = Path(os.environ["PASSWORD_CORPUS_DIR"])
manifest = json.loads((root / "manifest.json").read_text())
assert manifest["synthetic"] is False
assert manifest["format"] == "sha1-binary-sorted-v1"
assert manifest["source"] == "Pwned Passwords"
assert manifest["count"] == int(os.environ["CORPUS_EXPECTED_COUNT"])
binary = root / "sha1.bin"
assert binary.stat().st_size == 20 * manifest["count"]
with binary.open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == manifest["sha256"]
print(json.dumps({"manifest": manifest, "binary_bytes": binary.stat().st_size, "validation_seconds": round(time.perf_counter() - started, 2)}))
' > "$corpus_run/import-verification.json"
```

Relee todo el binario: presupuestar tiempo de I/O. Conservar salida y copia de
`manifest.json` con el expediente. No atribuir estos resultados antes de ejecutar el
paso con datos reales. Después, comprobar el lector sin imprimir contraseñas ni requerir
una política aprobada:

```bash
docker compose -f compose.yaml -f compose.corpus-readonly.yaml run --rm --no-deps \
  --env "PASSWORD_CORPUS_DIR=/var/lib/aerolinea/passwords/$corpus_label" \
  backend python -c '
import django
django.setup()
from apps.users.password_corpus import is_compromised
assert is_compromised("password")
print("Lector offline: pertenencia comprobada.")
'
```

La cadena es un valor público conocido, no una credencial de cuenta. Este ensayo no
verifica HTTP ni calienta cachés de workers: cada proceso valida su propio snapshot.
Medir primer acceso real y preparar el arranque antes de habilitar tráfico productivo.

## 5. Activación posterior y conservación

Tras una verificación correcta, configurar **solo** `PASSWORD_CORPUS_DIR` en el `.env`
existente como `/var/lib/aerolinea/passwords/<etiqueta-real>`, preservando las otras
variables. Usar la etiqueta real verificada, no escribir literalmente el placeholder.
Recrear backend en el entorno local acordado con el overlay:

```bash
docker compose -f compose.yaml -f compose.corpus-readonly.yaml up -d --no-deps backend
```

Esta operación tampoco se ejecutó en la preparación. Conservar ambos `-f` en comandos
posteriores: solo el Compose base vuelve a declarar el volumen como escritura.
Comprobar el montaje efectivo sin mostrar variables:

```bash
docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/aerolinea/passwords"}}{{println .Destination "RW=" .RW}}{{end}}{{end}}' "$(docker compose ps -q backend)"
```

Debe indicar `RW=false`. No ejecutar `down -v` ni borrar corpus anterior. Para actualizar,
usar nuevo directorio y cambiar el puntero tras validar. Para volver atrás, elegir el
directorio anterior conservado y recrear backend con el mismo overlay. Revisar retención
antes de limpiar textos/temporales; este procedimiento no elimina datos automáticamente.

El expediente **fuera de Git** conserva fuentes/versión, digest de SDK, fechas/log de
éxito, bytes/conteo, `sources.sha256`, etiqueta, manifiesto y verificación del binario.
Los hashes locales aseguran integridad de esa captura; no actualización instantánea.

**Pendientes vigentes:** descarga/importación/verificación reales, medición de arranque,
política aprobada, frontend/correo y demás verificaciones operativas. **Retirado:** repetir
las 157 pruebas y verificaciones de HU-007 en Docker/PostgreSQL 17.11, comunicadas por
el usuario. No se declara producción preparada ni HU completa.
