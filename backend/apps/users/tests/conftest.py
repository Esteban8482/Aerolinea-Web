"""Frontera HTTP simulada; las pruebas de HU-007 nunca consultan Internet."""

import io
from unittest.mock import MagicMock

import pytest


def range_body(*, suffix=None, count=1):
    records = {f"{i:035X}": 0 for i in range(800)}
    if suffix is not None:
        records[suffix] = count
    return b"\r\n".join(f"{key}:{value}".encode() for key, value in records.items())


@pytest.fixture(autouse=True)
def deny_provider_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Prueba sin frontera HTTP simulada")

    monkeypatch.setattr("apps.users.password_check.http.client.HTTPSConnection", forbidden)


@pytest.fixture
def provider(monkeypatch, deny_provider_network):
    state = {"body": range_body(), "status": 200, "headers": {}, "error": None}
    connections = []

    def create(*args, **kwargs):
        connection = MagicMock()
        connections.append(connection)
        if state["error"] is not None:
            connection.connect.side_effect = state["error"]
        body = state["body"]
        headers = {"Content-Type": "text/plain; charset=utf-8", "Content-Length": str(len(body))}
        headers.update(state["headers"])
        response = MagicMock(status=state["status"], chunked=state.get("chunked", False))
        response.getheader.side_effect = lambda name, default=None: headers.get(name, default)
        response.read1.side_effect = io.BytesIO(body).read1
        connection.getresponse.return_value = response
        return connection

    factory = MagicMock(side_effect=create)
    monkeypatch.setattr("apps.users.password_check.http.client.HTTPSConnection", factory)
    state.update(factory=factory, connections=connections)
    return state
