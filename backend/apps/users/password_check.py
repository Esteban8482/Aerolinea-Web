"""Consulta por rango: solo el prefijo SHA-1 sale del proceso; Argon2id almacena claves."""

import hashlib
import http.client
import re
import ssl
import time
from threading import Event, Thread

from django.conf import settings
from django.core.exceptions import ValidationError

from .errors import PasswordCheckUnavailable

HOST = "api.pwnedpasswords.com"
MAX_RESPONSE_BYTES = 1024 * 1024
RECORD = re.compile(rb"([0-9A-Fa-f]{35}):([0-9]{1,20})")


def _range_response(prefix, timeout):
    # El límite de socket no acota DNS ni la suma de lecturas. El solicitante espera
    # como máximo timeout; este hilo solo hace HTTP, nunca escribe ni recibe la clave.
    done = Event()
    result = []
    deadline = time.monotonic() + timeout

    def fetch():
        connection = None
        try:
            connection = http.client.HTTPSConnection(
                HOST, timeout=timeout, context=ssl.create_default_context()
            )

            def remaining():
                seconds = deadline - time.monotonic()
                if seconds <= 0:
                    raise TimeoutError
                connection.sock.settimeout(seconds)

            connection.connect()
            remaining()
            connection.request(
                "GET",
                "/range/" + prefix,
                headers={
                    "Add-Padding": "true",
                    "Accept": "text/plain",
                    "Accept-Encoding": "identity",
                    "User-Agent": "Aerolinea-Web-HU007",
                },
            )
            remaining()
            response = connection.getresponse()
            length = response.getheader("Content-Length")
            if (
                response.status != 200
                or response.getheader("Content-Type", "").split(";")[0].lower() != "text/plain"
                or response.getheader("Content-Encoding", "identity").lower() != "identity"
                or (length is None and not response.chunked)
                or (
                    length is not None
                    and (
                        not length.isascii()
                        or not length.isdigit()
                        or int(length) > MAX_RESPONSE_BYTES
                    )
                )
            ):
                raise ValueError
            body = bytearray()
            while True:
                remaining()
                chunk = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError
            if length is not None and len(body) != int(length):
                raise ValueError
            result.append(bytes(body))
        except (OSError, ValueError, http.client.HTTPException):
            # Nunca conservar ni registrar excepciones con URL, prefijo o respuesta.
            pass
        finally:
            if connection is not None:
                connection.close()
            done.set()

    Thread(target=fetch, name="password-range-http", daemon=True).start()
    if not done.wait(timeout) or not result:
        raise PasswordCheckUnavailable()
    return result[0]


def is_compromised(password):
    digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    body = _range_response(digest[:5], settings.PWNED_PASSWORDS_TIMEOUT_SECONDS)
    lines = body.split(b"\r\n")
    if lines[-1:] == [b""]:
        lines.pop()
    # Add-Padding garantiza al menos 800 entradas; no impone un máximo actual.
    if len(lines) < 800:
        raise PasswordCheckUnavailable()
    seen = set()
    found = False
    for line in lines:
        match = RECORD.fullmatch(line)
        if match is None:
            raise PasswordCheckUnavailable()
        suffix, count = match.groups()
        suffix = suffix.upper()
        if suffix in seen:
            raise PasswordCheckUnavailable()
        seen.add(suffix)
        if suffix.decode("ascii") == digest[5:] and int(count) > 0:
            found = True
    return found


def validate_registration_password(password):
    if is_compromised(password):
        raise ValidationError(
            "Esta contraseña aparece en contraseñas comprometidas. Elige otra.",
            code="password_compromised",
        )
