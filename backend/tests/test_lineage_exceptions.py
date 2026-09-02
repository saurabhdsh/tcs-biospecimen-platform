from decimal import Decimal

from tests.test_inventory_labels import _position_ids
from tests.test_manifest_and_auth import _commit_new_shipment


def test_quantity_and_cycle_and_quarantine(client, operator, reviewer):
    samples, _ = _commit_new_shipment(client, operator)
    parent = samples[0]
    other = samples[1]
    client.post(f"/api/v1/samples/{parent}/accession", headers=operator)
    client.post(f"/api/v1/samples/{other}/accession", headers=operator)
    positions = _position_ids(client, operator)
    client.post(
        f"/api/v1/samples/{parent}/storage",
        headers=operator,
        json={"storage_location_id": positions[0], "reason": "putaway"},
    )
    client.post(
        f"/api/v1/samples/{other}/storage",
        headers=operator,
        json={"storage_location_id": positions[1], "reason": "putaway"},
    )

    over = client.post(
        f"/api/v1/samples/{parent}/children",
        headers=operator,
        json={
            "relationship_type": "ALIQUOT",
            "output_quantity": 1,
            "output_unit": "mL",
            "parent_quantity_consumed": 999,
            "child_sample_type": "Plasma",
        },
    )
    assert over.status_code == 400
    assert over.json()["code"] == "INSUFFICIENT_QUANTITY"

    child = client.post(
        f"/api/v1/samples/{parent}/children",
        headers=operator,
        json={
            "relationship_type": "ALIQUOT",
            "output_quantity": 1,
            "output_unit": "mL",
            "parent_quantity_consumed": 1,
            "child_sample_type": "Plasma Aliquot",
        },
    )
    assert child.status_code == 200, child.text
    child_id = child.json()["id"]
    parent_after = client.get(f"/api/v1/samples/{parent}", headers=operator).json()
    assert float(parent_after["quantity_remaining"]) == 9

    cycle = client.post(
        f"/api/v1/samples/{child_id}/children",
        headers=operator,
        json={
            "relationship_type": "DERIVATIVE",
            "output_quantity": 0.1,
            "output_unit": "mL",
            "parent_quantity_consumed": 0.1,
            "child_sample_type": "Cycle",
            "existing_child_id": parent,
        },
    )
    assert cycle.status_code == 400
    assert cycle.json()["code"] == "LINEAGE_CYCLE"

    graph = client.get(f"/api/v1/samples/{parent}/lineage", headers=operator)
    assert graph.status_code == 200
    assert len(graph.json()["nodes"]) >= 2

    env = client.post(
        f"/api/v1/samples/{parent}/environmental-events/json",
        headers=operator,
        json={
            "measured_value": -10,
            "unit": "C",
            "acceptable_min": -86,
            "acceptable_max": -70,
            "source": "probe",
            "notes": "test excursion",
            "create_exception": True,
        },
    )
    assert env.status_code == 200, env.text
    quarantined = client.get(f"/api/v1/samples/{parent}", headers=operator).json()
    assert quarantined["status"] == "QUARANTINED"
    blocked = client.post(
        f"/api/v1/samples/{parent}/move",
        headers=operator,
        json={"destination_location_id": positions[2], "reason": "should fail"},
    )
    assert blocked.status_code == 400
    assert blocked.json()["code"] == "SAMPLE_QUARANTINED"

    cases = client.get("/api/v1/exceptions", headers=operator).json()
    case = next(c for c in cases if c["sample_id"] == parent)
    denied = client.post(
        f"/api/v1/exceptions/{case['id']}/resolve",
        headers=operator,
        json={"resolution_comment": "try", "disposition": "RELEASE_TO_INVENTORY"},
    )
    assert denied.status_code == 403
    resolved = client.post(
        f"/api/v1/exceptions/{case['id']}/resolve",
        headers=reviewer,
        json={"resolution_comment": "Logger drift confirmed; material still viable.", "disposition": "RELEASE_TO_INVENTORY"},
    )
    assert resolved.status_code == 200, resolved.text
    after = client.get(f"/api/v1/samples/{parent}", headers=operator).json()
    assert after["status"] == "IN_STORAGE"


def test_search_audit_reports_traceability(client, operator, admin):
    samples, tag = _commit_new_shipment(client, operator)
    sid = samples[0]
    body = client.get(f"/api/v1/samples/{sid}", headers=operator).json()
    found = client.get(f"/api/v1/search?q={body['sample_id']}", headers=operator)
    assert found.status_code == 200
    assert any(x["label"] == body["sample_id"] for x in found.json())
    bc = client.get(f"/api/v1/search?q=BC-{tag}-1", headers=operator)
    assert any(x["kind"] == "sample" for x in bc.json())
    hist = client.get(f"/api/v1/reports/sample-history/{sid}", headers=operator)
    assert hist.status_code == 200
    assert hist.json()["identity"]["sample_id"] == body["sample_id"]
    inv = client.get("/api/v1/reports/inventory", headers=operator)
    assert inv.status_code == 200
    assert inv.json()["row_count"] if False else inv.json()["rows"]
    audit = client.get("/api/v1/audit?event_type=SAMPLE_CREATED", headers=operator)
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1
    trace = client.get("/api/v1/traceability", headers=operator)
    assert trace.status_code == 200
    codes = {row["requirement_code"] for row in trace.json()}
    assert "REQ-C1-001" in codes
    assert "REQ-C4-010" in codes
    users = client.get("/api/v1/admin/users", headers=admin)
    assert users.status_code == 200
    dash = client.get("/api/v1/dashboard", headers=operator)
    assert dash.status_code == 200
    assert dash.json()["total_samples"] >= 1
    health = client.get("/health")
    assert health.json()["status"] == "ok"
    ready = client.get("/ready")
    assert ready.json()["status"] == "ready"
