"""Launches the Phase 1 protocol servers (REST, GraphQL, gRPC) as subprocesses
for the duration of the test_protocols session, and resets fault-mode env
vars between tests.
"""

import os
import subprocess
import sys
import time

import httpx
import pytest


def _wait_for_health(url: str, timeout_s: float = 15.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"Server at {url} did not become healthy in time")


@pytest.fixture(scope="session")
def rest_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "shopsmart.protocols.rest_server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_health("http://127.0.0.1:8001/health")
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def graphql_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "shopsmart.protocols.graphql_server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_health("http://127.0.0.1:8002/health")
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def grpc_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "shopsmart.protocols.grpc_pricing_server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)  # gRPC has no simple HTTP health endpoint here
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def webhook_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "shopsmart.protocols.webhook_server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_health("http://127.0.0.1:8004/health")
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def websocket_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "shopsmart.protocols.websocket_server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)  # no simple HTTP health check for a raw ws server
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


def _broker_reachable(host: str, port: int) -> bool:
    import socket

    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def mqtt_responder():
    from shopsmart.config import get_mqtt_broker_host, get_mqtt_broker_port

    if not _broker_reachable(get_mqtt_broker_host(), get_mqtt_broker_port()):
        pytest.skip("Mosquitto broker not reachable — run `make brokers-up` first")

    proc = subprocess.Popen(
        [sys.executable, "-m", "shopsmart.protocols.mqtt_responder"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def amqp_responder():
    if not _broker_reachable("127.0.0.1", 5672):
        pytest.skip("RabbitMQ broker not reachable — run `make brokers-up` first")

    proc = subprocess.Popen(
        [sys.executable, "-m", "shopsmart.protocols.amqp_responder"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def soap_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "shopsmart.protocols.soap_server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_health("http://127.0.0.1:8006/health")
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(autouse=True)
def _reset_fault_modes():
    keys = [
        "FAULT_MODE_REST",
        "FAULT_MODE_GRAPHQL",
        "FAULT_MODE_GRPC",
        "FAULT_MODE_WEBHOOK",
        "FAULT_MODE_WS",
        "FAULT_MODE_MQTT",
        "FAULT_MODE_AMQP",
        "FAULT_MODE_SOAP",
    ]
    saved = {k: os.environ.get(k) for k in keys}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
