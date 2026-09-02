from tests.conftest import unique_tag


def test_operator_cannot_list_users(client, operator):
    r = client.get("/api/v1/admin/users", headers=operator)
    assert r.status_code == 403


def test_admin_create_and_delete_user(client, admin):
    tag = unique_tag().lower()
    email = f"lab.{tag}@biospecimen.local"
    created = client.post(
        "/api/v1/admin/users",
        headers=admin,
        json={
            "email": email,
            "full_name": "Bench Scientist",
            "password": "LabOps@2026",
            "roles": ["OPERATOR"],
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["email"] == email
    assert body["roles"] == ["OPERATOR"]
    assert body["is_active"] is True

    listed = client.get("/api/v1/admin/users", headers=admin)
    assert listed.status_code == 200
    assert any(u["email"] == email for u in listed.json())

    login = client.post("/api/v1/auth/login", json={"email": email, "password": "LabOps@2026"})
    assert login.status_code == 200

    deleted = client.delete(f"/api/v1/admin/users/{body['id']}", headers=admin)
    assert deleted.status_code == 200, deleted.text

    listed2 = client.get("/api/v1/admin/users", headers=admin)
    assert all(u["email"] != email for u in listed2.json())

    denied = client.post("/api/v1/auth/login", json={"email": email, "password": "LabOps@2026"})
    assert denied.status_code == 401


def test_admin_cannot_delete_self(client, admin):
    me = client.get("/api/v1/auth/me", headers=admin)
    assert me.status_code == 200
    r = client.delete(f"/api/v1/admin/users/{me.json()['id']}", headers=admin)
    assert r.status_code == 400
    assert r.json()["code"] == "CANNOT_DELETE_SELF"
