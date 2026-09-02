from io import BytesIO

from tests.conftest import make_csv, unique_tag


def test_login_success(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "operator@biospecimen.local", "password": "LabOps@2026"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert "OPERATOR" in r.json()["user"]["roles"]


def test_login_failure(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "operator@biospecimen.local", "password": "wrong"},
    )
    assert r.status_code == 401
    assert r.json()["code"] == "INVALID_CREDENTIALS"


def test_reviewer_cannot_upload_manifest(client, reviewer):
    tag = unique_tag()
    r = client.post(
        "/api/v1/manifests",
        headers=reviewer,
        files={"file": ("m.csv", BytesIO(make_csv(tag)), "text/csv")},
    )
    assert r.status_code == 403


def _commit_new_shipment(client, operator):
    tag = unique_tag()
    up = client.post(
        "/api/v1/manifests",
        headers=operator,
        files={"file": (f"{tag}.csv", BytesIO(make_csv(tag)), "text/csv")},
    )
    assert up.status_code == 200, up.text
    mid = up.json()["id"]
    val = client.post(f"/api/v1/manifests/{mid}/validate", headers=operator)
    assert val.status_code == 200, val.text
    assert val.json()["status"] == "VALIDATED"
    commit = client.post(f"/api/v1/manifests/{mid}/commit", headers=operator)
    assert commit.status_code == 200, commit.text
    assert commit.json()["status"] == "COMMITTED"
    double = client.post(f"/api/v1/manifests/{mid}/commit", headers=operator)
    assert double.status_code == 409
    samples = [row["committed_sample_id"] for row in commit.json()["rows"] if row["committed_sample_id"]]
    return samples, tag


def test_manifest_validate_and_commit(client, operator):
    samples, _ = _commit_new_shipment(client, operator)
    assert len(samples) == 2
    s = client.get(f"/api/v1/samples/{samples[0]}", headers=operator)
    assert s.status_code == 200
    body = s.json()
    assert body["sample_id"].startswith("SMP-")
    assert body["status"] == "RECEIVED"


def test_manifest_duplicate_and_invalid_rows(client, operator):
    tag = unique_tag()
    ref = f"SHP-TEST-{tag}"
    csv = "\n".join(
        [
            "shipment_reference,sample_external_id,external_barcode,sample_type,material_type,quantity,quantity_unit,collection_date,received_date,source_location,temperature_requirement",
            f"{ref},EXT-{tag}-1,BC-{tag}-1,Whole Blood,Blood,10,mL,2026-08-01,2026-08-03,London,-80C",
            f"{ref},EXT-{tag}-1,BC-{tag}-2,Plasma,Plasma,-5,mL,2026-08-01,2026-08-03,London,-80C",
            f"{ref},EXT-{tag}-3,BC-{tag}-3,Serum,Serum,4,widgets,2026-08-01,2026-08-03,London,-80C",
        ]
    ).encode()
    up = client.post(
        "/api/v1/manifests",
        headers=operator,
        files={"file": ("bad.csv", BytesIO(csv), "text/csv")},
    )
    mid = up.json()["id"]
    val = client.post(f"/api/v1/manifests/{mid}/validate", headers=operator)
    assert val.status_code == 200
    body = val.json()
    assert body["status"] == "VALIDATION_FAILED"
    assert body["invalid_row_count"] >= 2
    codes = {e["code"] for e in body["validation_errors"]}
    assert "DUPLICATE_SAMPLE_ID_IN_UPLOAD" in codes
    assert "QUANTITY_NOT_POSITIVE" in codes
    commit = client.post(f"/api/v1/manifests/{mid}/commit", headers=operator)
    assert commit.status_code == 200
    committed = [r for r in commit.json()["rows"] if r["committed_sample_id"]]
    assert len(committed) == 1


def test_accession_once_only(client, operator):
    samples, tag = _commit_new_shipment(client, operator)
    sid = samples[0]
    lookup = client.get(f"/api/v1/samples/lookup?q=BC-{tag}-1", headers=operator)
    assert lookup.status_code == 200
    r = client.post(f"/api/v1/samples/{sid}/accession", headers=operator)
    assert r.status_code == 200
    assert r.json()["status"] == "ACCESSIONED"
    again = client.post(f"/api/v1/samples/{sid}/accession", headers=operator)
    assert again.status_code == 400
