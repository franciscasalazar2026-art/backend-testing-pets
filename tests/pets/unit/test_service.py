"""Pruebas unitarias de PetsService."""

from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.pets.schemas import CreatePetDto, UpdatePetDto
from app.pets.service import PetsService
from app.shared.datetimes import utc_now

pytestmark = pytest.mark.unit


@pytest.fixture
def service(fake_pets_repository, fake_students_repository):
    db = MagicMock()
    pets_service = PetsService(db)
    pets_service.repository = fake_pets_repository
    pets_service.students_service.repository = fake_students_repository
    return pets_service


def test_find_all_for_student(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
):
    student = make_student_model()
    other_student = make_student_model(username="beto", email="beto@example.com")
    fake_students_repository.students.extend([student, other_student])

    now = utc_now()
    fake_pets_repository.pets.extend(
        [
            make_pet_model(studentId=student.id, name="Firulais", createdAt=now),
            make_pet_model(
                studentId=student.id,
                name="Michi",
                species="gato",
                createdAt=now + timedelta(seconds=1),
            ),
            make_pet_model(studentId=other_student.id, name="Rex"),
        ]
    )

    result = service.find_all_for_student(str(student.id))

    assert result.total == 2
    assert [pet.name for pet in result.items] == ["Michi", "Firulais"]


def test_find_all_for_student_not_found(service):
    with pytest.raises(HTTPException) as error:
        service.find_all_for_student(str(uuid4()))

    assert error.value.status_code == 404
    assert error.value.detail == "Estudiante no encontrado"


@pytest.mark.parametrize(
    "invalid_student_id",
    ["no-es-uuid", "12345", ""],
    ids=["texto", "numeros", "vacio"],
)
def test_find_all_for_student_invalid_uuid_returns_404(service, invalid_student_id):
    """Verifica que un studentId con formato inválido devuelva 404."""
    with pytest.raises(HTTPException) as error:
        service.find_all_for_student(invalid_student_id)

    assert error.value.status_code == 404
    assert error.value.detail == "Estudiante no encontrado"
    service.db.commit.assert_not_called()


def test_create_pet(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    pet_payload,
):
    student = make_student_model()
    fake_students_repository.students.append(student)

    result = service.create(str(student.id), CreatePetDto(**pet_payload()))

    assert result.name == "Firulais"
    assert result.species == "perro"
    assert result.age == 3
    assert result.studentId == student.id
    assert len(fake_pets_repository.pets) == 1
    service.db.commit.assert_called_once()


def test_create_pet_student_not_found(service, pet_payload):
    with pytest.raises(HTTPException) as error:
        service.create(str(uuid4()), CreatePetDto(**pet_payload()))

    assert error.value.status_code == 404
    service.db.commit.assert_not_called()


def test_create_pet_duplicate_name_same_student(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
    pet_payload,
):
    student = make_student_model()
    fake_students_repository.students.append(student)
    fake_pets_repository.pets.append(
        make_pet_model(studentId=student.id, name="Firulais")
    )

    with pytest.raises(HTTPException) as error:
        service.create(str(student.id), CreatePetDto(**pet_payload(name="Firulais")))

    assert error.value.status_code == 409
    assert "name" in error.value.detail["errors"]
    service.db.commit.assert_not_called()


def test_create_pet_case_insensitive_duplicate_name(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
    pet_payload,
):
    """Verifica que nombres iguales con distinta capitalización también den 409."""
    student = make_student_model()
    fake_students_repository.students.append(student)
    pet = make_pet_model(studentId=student.id, name="Firulais")
    fake_pets_repository.pets.append(pet)

    with pytest.raises(HTTPException) as error:
        service.create(str(student.id), CreatePetDto(**pet_payload(name="FIRULAIS")))

    assert error.value.status_code == 409
    assert "name" in error.value.detail["errors"]
    assert fake_pets_repository.pets == [pet]
    service.db.commit.assert_not_called()


def test_create_pet_same_name_different_students(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
    pet_payload,
):
    student_a = make_student_model()
    student_b = make_student_model(username="beto", email="beto@example.com")
    fake_students_repository.students.extend([student_a, student_b])
    fake_pets_repository.pets.append(
        make_pet_model(studentId=student_a.id, name="Firulais")
    )

    result = service.create(
        str(student_b.id), CreatePetDto(**pet_payload(name="Firulais"))
    )

    assert result.name == "Firulais"
    assert result.studentId == student_b.id
    assert len(fake_pets_repository.pets) == 2
    service.db.commit.assert_called_once()


def test_update_pet(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
):
    student = make_student_model()
    pet = make_pet_model(studentId=student.id, name="Firulais", age=3)
    fake_students_repository.students.append(student)
    fake_pets_repository.pets.append(pet)

    result = service.update(
        str(student.id), str(pet.id), UpdatePetDto(name="Max", age=4)
    )

    assert result.name == "Max"
    assert result.age == 4
    assert result.species == "perro"
    service.db.commit.assert_called_once()


def test_update_pet_same_name_allowed(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
):
    student = make_student_model()
    pet = make_pet_model(studentId=student.id, name="Firulais")
    fake_students_repository.students.append(student)
    fake_pets_repository.pets.append(pet)

    result = service.update(
        str(student.id), str(pet.id), UpdatePetDto(name="Firulais", age=5)
    )

    assert result.name == "Firulais"
    assert result.age == 5
    service.db.commit.assert_called_once()


def test_update_pet_duplicate_name_conflict(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
):
    student = make_student_model()
    pet_1 = make_pet_model(studentId=student.id, name="Firulais")
    pet_2 = make_pet_model(studentId=student.id, name="Michi", species="gato")
    fake_students_repository.students.append(student)
    fake_pets_repository.pets.extend([pet_1, pet_2])

    with pytest.raises(HTTPException) as error:
        service.update(str(student.id), str(pet_2.id), UpdatePetDto(name="Firulais"))

    assert error.value.status_code == 409
    assert "name" in error.value.detail["errors"]
    service.db.commit.assert_not_called()


def test_update_pet_owned_by_another_student_returns_404(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
):
    owner = make_student_model()
    intruder = make_student_model(username="beto", email="beto@example.com")
    pet = make_pet_model(studentId=owner.id)
    fake_students_repository.students.extend([owner, intruder])
    fake_pets_repository.pets.append(pet)

    with pytest.raises(HTTPException) as error:
        service.update(str(intruder.id), str(pet.id), UpdatePetDto(name="Hack"))

    assert error.value.status_code == 404
    assert error.value.detail == "Mascota no encontrada"
    service.db.commit.assert_not_called()


def test_delete_pet(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
):
    student = make_student_model()
    pet = make_pet_model(studentId=student.id)
    fake_students_repository.students.append(student)
    fake_pets_repository.pets.append(pet)

    deleted = service.delete(str(student.id), str(pet.id))

    assert deleted.id == pet.id
    assert fake_pets_repository.pets == []
    service.db.commit.assert_called_once()


@pytest.mark.parametrize(
    "pet_id",
    [str(uuid4()), "uuid-invalido"],
    ids=["inexistente", "uuid-invalido"],
)
def test_delete_pet_not_found(
    service, fake_students_repository, make_student_model, pet_id
):
    student = make_student_model()
    fake_students_repository.students.append(student)

    with pytest.raises(HTTPException) as error:
        service.delete(str(student.id), pet_id)

    assert error.value.status_code == 404
    assert error.value.detail == "Mascota no encontrada"
    service.db.commit.assert_not_called()


@pytest.mark.parametrize(
    "pet_id",
    [str(uuid4()), "id-no-valido"],
    ids=["inexistente", "uuid-invalido"],
)
def test_update_pet_not_found(
    service, fake_students_repository, make_student_model, pet_id
):
    """Verifica que actualizar una mascota inexistente o con UUID inválido dé 404."""
    student = make_student_model()
    fake_students_repository.students.append(student)

    with pytest.raises(HTTPException) as error:
        service.update(str(student.id), pet_id, UpdatePetDto(name="Max"))

    assert error.value.status_code == 404
    assert error.value.detail == "Mascota no encontrada"
    service.db.commit.assert_not_called()


def test_update_pet_student_not_found_returns_404(service):
    """Verifica que actualizar mascota de un estudiante inexistente dé 404."""
    with pytest.raises(HTTPException) as error:
        service.update(str(uuid4()), str(uuid4()), UpdatePetDto(name="Max"))

    assert error.value.status_code == 404
    assert error.value.detail == "Estudiante no encontrado"
    service.db.commit.assert_not_called()


def test_delete_pet_student_not_found_returns_404(service):
    """Verifica que eliminar mascota de un estudiante inexistente dé 404."""
    with pytest.raises(HTTPException) as error:
        service.delete(str(uuid4()), str(uuid4()))

    assert error.value.status_code == 404
    assert error.value.detail == "Estudiante no encontrado"
    service.db.commit.assert_not_called()


def test_update_pet_can_clear_age_to_none(
    service,
    fake_students_repository,
    fake_pets_repository,
    make_student_model,
    make_pet_model,
):
    """Verifica que actualizar age=None limpie la edad registrada."""
    student = make_student_model()
    pet = make_pet_model(studentId=student.id, name="Firulais", age=5)
    fake_students_repository.students.append(student)
    fake_pets_repository.pets.append(pet)

    result = service.update(str(student.id), str(pet.id), UpdatePetDto(age=None))

    assert result.age is None
    assert result.name == "Firulais"
    service.db.commit.assert_called_once()
