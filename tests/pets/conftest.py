"""Dobles de prueba y datos reutilizables para los tests de Pets.

Los repositorios falsos permiten probar PetsService sin PostgreSQL.
"""

from uuid import UUID, uuid4

import pytest

from app.pets.models import PetModel
from app.shared.datetimes import utc_now
from app.students.models import StudentModel


class FakeStudentsRepository:
    """Repositorio en memoria con la interfaz necesaria para StudentsService."""

    def __init__(self) -> None:
        self.students: list[StudentModel] = []

    def find_by_id(self, student_id: UUID) -> StudentModel | None:
        return next(
            (student for student in self.students if student.id == student_id), None
        )


class FakePetsRepository:
    """Repositorio en memoria con la misma interfaz que PetsRepository."""

    def __init__(self) -> None:
        self.pets: list[PetModel] = []

    def find_all_by_student(self, student_id: UUID) -> list[PetModel]:
        matching = [pet for pet in self.pets if pet.studentId == student_id]
        return sorted(matching, key=lambda pet: pet.createdAt, reverse=True)

    def find_by_id(self, pet_id: UUID) -> PetModel | None:
        return next((pet for pet in self.pets if pet.id == pet_id), None)

    def find_by_student_and_name(self, student_id: UUID, name: str) -> PetModel | None:
        return next(
            (
                pet
                for pet in self.pets
                if pet.studentId == student_id and pet.name == name
            ),
            None,
        )

    def add(self, pet: PetModel) -> PetModel:
        pet.id = uuid4()
        now = utc_now()
        pet.createdAt = now
        pet.updatedAt = now
        self.pets.append(pet)
        return pet

    def delete(self, pet: PetModel) -> None:
        self.pets.remove(pet)


@pytest.fixture
def fake_students_repository() -> FakeStudentsRepository:
    return FakeStudentsRepository()


@pytest.fixture
def fake_pets_repository() -> FakePetsRepository:
    return FakePetsRepository()


@pytest.fixture
def student_payload():
    def build(**overrides: object) -> dict[str, object]:
        data: dict[str, object] = {
            "name": "Ana Pérez",
            "username": "ana_perez",
            "email": "ana@example.com",
            "age": 21,
        }
        data.update(overrides)
        return data

    return build


@pytest.fixture
def pet_payload():
    def build(**overrides: object) -> dict[str, object]:
        data: dict[str, object] = {
            "name": "Firulais",
            "species": "perro",
            "age": 3,
        }
        data.update(overrides)
        return data

    return build


@pytest.fixture
def make_student_model():
    def build(**overrides: object) -> StudentModel:
        now = utc_now()
        values: dict[str, object] = {
            "id": uuid4(),
            "name": "Ana Pérez",
            "username": "ana_perez",
            "email": "ana@example.com",
            "age": 21,
            "createdAt": now,
            "updatedAt": now,
        }
        values.update(overrides)
        return StudentModel(**values)

    return build


@pytest.fixture
def make_pet_model():
    def build(**overrides: object) -> PetModel:
        now = utc_now()
        values: dict[str, object] = {
            "id": uuid4(),
            "studentId": uuid4(),
            "name": "Firulais",
            "species": "perro",
            "age": 3,
            "createdAt": now,
            "updatedAt": now,
        }
        values.update(overrides)
        return PetModel(**values)

    return build


@pytest.fixture
def created_student(auth_client, student_payload) -> dict[str, object]:
    response = auth_client.post("/api/students", json=student_payload())
    assert response.status_code == 201, response.text
    return response.json()["data"]
