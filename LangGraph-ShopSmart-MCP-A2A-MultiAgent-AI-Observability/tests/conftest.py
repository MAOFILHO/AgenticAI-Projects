"""Shared test fixtures for the ShopSmart support system."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from shopsmart.data_loader import load_all
from shopsmart.pii import build_known_names

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@pytest.fixture(scope="session")
def data_dir():
    return Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="session")
def data(data_dir):
    return load_all(data_dir)


@pytest.fixture(scope="session")
def customers_db(data):
    return data["customers_db"]


@pytest.fixture(scope="session")
def orders_db(data):
    return data["orders_db"]


@pytest.fixture(scope="session")
def products_db(data):
    return data["products_db"]


@pytest.fixture(scope="session")
def tickets(data):
    return data["tickets"]


@pytest.fixture(scope="session")
def customer_orders(data):
    return data["customer_orders"]


@pytest.fixture(scope="session")
def policies_text(data):
    return data["policies_text"]


@pytest.fixture(scope="session")
def known_names(customers_db):
    full_names, _, _ = build_known_names(customers_db)
    return full_names


@pytest.fixture(scope="session")
def sample_ticket(tickets):
    return tickets[0]


OPENAI_KEY_SET = bool(os.getenv("OPENAI_API_KEY"))

requires_openai = pytest.mark.skipif(
    not OPENAI_KEY_SET,
    reason="OPENAI_API_KEY not set",
)
