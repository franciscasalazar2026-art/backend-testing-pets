"""Pruebas E2E de la API de Pets."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.pets.models import PetModel

pytestmark = pytest.mark.e2e


def create_pet(client, student_id: str, payload: dict[str, object]) -> dict[str, object]:
    response = client.post(f"/api/students/{student_id}/pets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", f"/api/students/{uuid4()}/pets", None),
        (
            "POST",
            f"/api/students/{uuid4()}/pets",
            {"name": "Firulais", "species": "perro", "age": 3},
        ),
        ("PATCH", f"/api/students/{uuid4()}/pets/{uuid4()}", {"name": "Max"}),
        ("DELETE", f"/api/students/{uuid4()}/pets/{uuid4()}", None),
    ],
    ids=["listar", "crear", "actualizar", "eliminar"],
)
def test_requires_session(client, method, path, payload):
    response = client.request(method, path, json=payload)

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]


def test_list_pets_empty(auth_client, created_student):
    student_id = created_student["id"]

    response = auth_client.get(f"/api/students/{student_id}/pets")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "Operación exitosa"
    assert body["data"] == {"total": 0, "items": []}


def test_create_pet(auth_client, created_student, pet_payload):
    student_id = created_student["id"]

    response = auth_client.post(
        f"/api/students/{student_id}/pets", json=pet_payload()
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 201
    assert body["success"] is True
    assert body["message"] == "Recurso creado"
    data = body["data"]
    assert data["name"] == "Firulais"
    assert data["species"] == "perro"
    assert data["age"] == 3
    assert data["studentId"] == student_id
    assert UUID(data["id"])
    assert data["createdAt"].endswith("Z")
    assert data["updatedAt"].endswith("Z")


def test_create_pet_duplicate_name_returns_409(
    auth_client, created_student, pet_payload
):
    student_id = created_student["id"]
    create_pet(auth_client, student_id, pet_payload())

    response = auth_client.post(
        f"/api/students/{student_id}/pets", json=pet_payload()
    )

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False


def test_create_pet_invalid_payload_returns_422(auth_client, created_student):
    student_id = created_student["id"]

    response = auth_client.post(
        f"/api/students/{student_id}/pets",
        json={"name": "", "species": "perro", "age": -2},
    )

    assert response.status_code == 422


def test_list_pets_only_owned_by_student(
    auth_client, created_student, student_payload, pet_payload
):
    student_a_id = created_student["id"]
    other_response = auth_client.post(
        "/api/students",
        json=student_payload(
            name="Beto", username="beto", email="beto@example.com"
        ),
    )
    student_b_id = other_response.json()["data"]["id"]

    pet_1 = create_pet(auth_client, student_a_id, pet_payload(name="Firulais"))
    pet_2 = create_pet(
        auth_client, student_a_id, pet_payload(name="Michi", species="gato")
    )
    create_pet(auth_client, student_b_id, pet_payload(name="Rex"))

    response = auth_client.get(f"/api/students/{student_a_id}/pets")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert {item["id"] for item in data["items"]} == {pet_1["id"], pet_2["id"]}


def test_update_pet(auth_client, created_student, pet_payload):
    student_id = created_student["id"]
    created = create_pet(auth_client, student_id, pet_payload())

    response = auth_client.patch(
        f"/api/students/{student_id}/pets/{created['id']}",
        json={"name": "Max", "age": 5},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == created["id"]
    assert data["name"] == "Max"
    assert data["age"] == 5
    assert data["species"] == "perro"


def test_update_pet_from_another_student_returns_404(
    auth_client, created_student, student_payload, pet_payload
):
    owner_id = created_student["id"]
    other_response = auth_client.post(
        "/api/students",
        json=student_payload(
            name="Beto", username="beto", email="beto@example.com"
        ),
    )
    other_id = other_response.json()["data"]["id"]
    pet = create_pet(auth_client, owner_id, pet_payload())

    response = auth_client.patch(
        f"/api/students/{other_id}/pets/{pet['id']}",
        json={"name": "Intruso"},
    )

    assert response.status_code == 404


def test_delete_pet(auth_client, db_session, created_student, pet_payload):
    student_id = created_student["id"]
    created = create_pet(auth_client, student_id, pet_payload())

    response = auth_client.delete(
        f"/api/students/{student_id}/pets/{created['id']}"
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == created["id"]
    in_db = db_session.get(PetModel, UUID(created["id"]))
    assert in_db is None


def test_delete_student_cascades_pets(
    auth_client, db_session, created_student, pet_payload
):
    student_id = created_student["id"]
    create_pet(auth_client, student_id, pet_payload(name="Firulais"))
    create_pet(auth_client, student_id, pet_payload(name="Michi", species="gato"))

    response = auth_client.delete(f"/api/students/{student_id}")
    assert response.status_code == 200

    remaining = db_session.scalars(
        select(PetModel).where(PetModel.studentId == UUID(student_id))
    ).all()
    assert remaining == []