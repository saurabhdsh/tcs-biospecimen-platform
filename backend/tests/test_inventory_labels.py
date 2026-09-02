from tests.test_manifest_and_auth import _commit_new_shipment


def _walk_positions(client, headers, parent_id=None):
    nodes = client.get("/api/v1/inventory/tree", headers=headers, params={"parent_id": parent_id} if parent_id else None).json()
    found = []
    for node in nodes:
        if node["location_type"] == "POSITION":
            found.append(node)
        else:
            found.extend(_walk_positions(client, headers, node["id"]))
    return found


def _position_ids(client, headers, n=4):
    free = []
    for pos in _walk_positions(client, headers):
        occ = client.get(f"/api/v1/inventory/locations/{pos['id']}/occupancy", headers=headers).json()
        if occ["available"] > 0:
            free.append(pos["id"])
        if len(free) >= n:
            break
    assert len(free) >= n, "Not enough free storage positions for test"
    return free


def _custodian_id(client, headers):
    return client.get("/api/v1/custodians", headers=headers).json()[0]["id"]


def test_storage_occupancy_and_move(client, operator):
    samples, _ = _commit_new_shipment(client, operator)
    sid = samples[0]
    client.post(f"/api/v1/samples/{sid}/accession", headers=operator)
    positions = _position_ids(client, operator)
    a, b = positions[0], positions[1]
    assigned = client.post(
        f"/api/v1/samples/{sid}/storage",
        headers=operator,
        json={"storage_location_id": a, "reason": "initial putaway"},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "IN_STORAGE"
    other_samples, _ = _commit_new_shipment(client, operator)
    other = other_samples[0]
    client.post(f"/api/v1/samples/{other}/accession", headers=operator)
    conflict = client.post(
        f"/api/v1/samples/{other}/storage",
        headers=operator,
        json={"storage_location_id": a, "reason": "should fail"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "POSITION_OCCUPIED"
    moved = client.post(
        f"/api/v1/samples/{sid}/move",
        headers=operator,
        json={"destination_location_id": b, "reason": "relocate to adjacent position"},
    )
    assert moved.status_code == 200, moved.text


def test_checkout_return_and_labels(client, operator):
    samples, _ = _commit_new_shipment(client, operator)
    sid = samples[0]
    client.post(f"/api/v1/samples/{sid}/accession", headers=operator)
    positions = _position_ids(client, operator)
    client.post(
        f"/api/v1/samples/{sid}/storage",
        headers=operator,
        json={"storage_location_id": positions[2], "reason": "putaway"},
    )
    cid = _custodian_id(client, operator)
    cust = client.post(
        f"/api/v1/samples/{sid}/custodian",
        headers=operator,
        json={"custodian_id": cid, "reason": "bench ownership"},
    )
    assert cust.status_code == 200
    label = client.post(f"/api/v1/samples/{sid}/labels", headers=operator)
    assert label.status_code == 200
    lid = label.json()["id"]
    png = client.get(f"/api/v1/labels/{lid}/png", headers=operator)
    assert png.status_code == 200
    assert png.headers["content-type"] == "image/png"
    blank = client.post(f"/api/v1/labels/{lid}/reprint", headers=operator, json={"reason": "  "})
    assert blank.status_code == 400
    reprint = client.post(
        f"/api/v1/labels/{lid}/reprint",
        headers=operator,
        json={"reason": "Label smudged during handling"},
    )
    assert reprint.status_code == 200
    assert reprint.json()["print_count"] >= 2
    checkout = client.post(
        f"/api/v1/samples/{sid}/checkout",
        headers=operator,
        json={"purpose": "Aliquot preparation"},
    )
    assert checkout.status_code == 200
    assert checkout.json()["status"] == "CHECKED_OUT"
    dup = client.post(f"/api/v1/samples/{sid}/checkout", headers=operator, json={"purpose": "again"})
    assert dup.status_code == 409
    ret = client.post(
        f"/api/v1/samples/{sid}/return",
        headers=operator,
        json={"storage_location_id": positions[3]},
    )
    assert ret.status_code == 200
    assert ret.json()["status"] == "IN_STORAGE"
