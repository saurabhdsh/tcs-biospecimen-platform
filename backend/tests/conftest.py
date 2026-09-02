from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str, password: str = "LabOps@2026") -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def operator(client):
    token = login(client, "operator@biospecimen.local")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def reviewer(client):
    token = login(client, "reviewer@biospecimen.local")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(client):
    token = login(client, "admin@biospecimen.local")
    return {"Authorization": f"Bearer {token}"}


def unique_tag() -> str:
    import uuid

    return uuid.uuid4().hex[:8].upper()


def make_csv(tag: str, extra_rows: list[str] | None = None) -> bytes:
    ref = f"SHP-TEST-{tag}"
    rows = [
        "shipment_reference,sample_external_id,external_barcode,sample_type,material_type,quantity,quantity_unit,collection_date,received_date,source_location,temperature_requirement",
        f"{ref},EXT-{tag}-1,BC-{tag}-1,Whole Blood,Blood,10,mL,2026-08-01,2026-08-03,London,-80C",
        f"{ref},EXT-{tag}-2,BC-{tag}-2,Plasma,Plasma,5,mL,2026-08-01,2026-08-03,London,-80C",
    ]
    if extra_rows:
        rows.extend(extra_rows)
    return ("\n".join(rows) + "\n").encode()
