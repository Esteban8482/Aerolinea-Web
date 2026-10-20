"""Corpus local inmutable: SHA-1 solo para pertenencia; contraseñas con Argon2id."""

import hashlib
import json
import mmap
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from .errors import RegistrationUnavailable

RECORD_BYTES = 20


def prepare_corpus(source, destination, *, label, synthetic=False):
    """Importa HASH:COUNT ordenado por hash, sin cargar el conjunto en memoria."""
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    count = 0
    digest = hashlib.sha256()
    previous = None
    try:
        with Path(source).open("rb") as incoming, (destination / "sha1.bin").open("xb") as output:
            for line in incoming:
                value, separator, frequency = line.strip().partition(b":")
                if (
                    len(value) != 40
                    or not separator
                    or not frequency.isdigit()
                    or int(frequency) < 1
                ):
                    raise ValueError("El corpus debe contener líneas SHA1:COUNT válidas.")
                try:
                    record = bytes.fromhex(value.decode("ascii"))
                except (ValueError, UnicodeError):
                    raise ValueError("El corpus contiene un hash no válido.") from None
                if len(record) != RECORD_BYTES or (previous is not None and record <= previous):
                    raise ValueError("El corpus debe estar ordenado por hash, sin duplicados.")
                output.write(record)
                digest.update(record)
                count += 1
                previous = record
        if not count:
            raise ValueError("El corpus no puede estar vacío.")
        manifest = {
            "format": "sha1-binary-sorted-v1",
            "count": count,
            "sha256": digest.hexdigest(),
            "label": label,
            "synthetic": synthetic,
            "source": "synthetic-test" if synthetic else "Pwned Passwords",
        }
        (destination / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (destination / "sha1.bin").chmod(0o600)
        (destination / "manifest.json").chmod(0o600)
    except Exception:
        # Solo archivos creados por esta ejecución, nunca un destino preexistente.
        for name in ["sha1.bin", "manifest.json"]:
            (destination / name).unlink(missing_ok=True)
        destination.rmdir()
        raise
    return count


@lru_cache(maxsize=4)
def _validate_snapshot(directory, data_identity, manifest_identity):
    root = Path(directory)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    count = manifest["count"]
    if (
        manifest["format"] != "sha1-binary-sorted-v1"
        or type(count) is not int
        or count < 1
        or data_identity[2] != count * RECORD_BYTES
        or type(manifest["synthetic"]) is not bool
        or not manifest["label"]
    ):
        raise ValueError("Corpus inválido.")
    with (root / "sha1.bin").open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != manifest["sha256"]:
            raise ValueError("Corpus corrupto.")
    return manifest


def _identity(path):
    status = path.stat()
    return status.st_ino, status.st_mtime_ns, status.st_size, status.st_ctime_ns


def is_compromised(password):
    if not settings.PASSWORD_CORPUS_DIR:
        raise RegistrationUnavailable()
    try:
        root = Path(settings.PASSWORD_CORPUS_DIR)
        data = root / "sha1.bin"
        manifest_file = root / "manifest.json"
        identity = _identity(data)
        manifest = _validate_snapshot(str(root), identity, _identity(manifest_file))
        if settings.REGISTRATION_PRODUCTION and manifest["synthetic"]:
            raise ValueError("Corpus de prueba en producción.")
        needle = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).digest()
        with (
            data.open("rb") as source,
            mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as content,
        ):
            if _identity(data) != identity:
                raise ValueError("El corpus cambió durante la consulta.")
            low, high = 0, manifest["count"]
            while low < high:
                middle = (low + high) // 2
                record = content[middle * RECORD_BYTES : (middle + 1) * RECORD_BYTES]
                if record < needle:
                    low = middle + 1
                else:
                    high = middle
            return (
                low < manifest["count"]
                and content[low * RECORD_BYTES : (low + 1) * RECORD_BYTES] == needle
            )
    except (OSError, ValueError, KeyError, TypeError, UnicodeError):
        raise RegistrationUnavailable() from None


def validate_registration_password(password):
    if is_compromised(password):
        raise ValidationError(
            "Esta contraseña aparece en el corpus de contraseñas comprometidas. Elige otra.",
            code="password_compromised",
        )
