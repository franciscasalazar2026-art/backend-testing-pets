"""Pruebas unitarias de PetsRepository usando una sesión simulada de SQLAlchemy."""

from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.pets.models import PetModel
from app.pets.repository import PetsRepository
from app.shared.datetimes import utc_now

pytestmark = pytest.mark.unit


@pytest.fixture
def repo_and_db():
    """Devuelve una instancia de PetsRepository junto a su sesión simulada."""
    db = MagicMock()
    return PetsRepository(db), db


def test_find_all_by_student_returns_ordered_list(repo_and_db, make_pet_model):
    """Verifica que find_all_by_student ejecute scalars() y devuelva la lista de mascotas."""
    repo, db = repo_and_db
    student_id = uuid4()
    now = utc_now()
    pet_1 = make_pet_model(studentId=student_id, name="Firulais", createdAt=now)
    pet_2 = make_pet_model(
        studentId=student_id,
        name="Michi",
        species="gato",
        createdAt=now + timedelta(seconds=5),
    )
    db.scalars.return_value = iter([pet_2, pet_1])

    result = repo.find_all_by_student(student_id)

    assert result == [pet_2, pet_1]
    db.scalars.assert_called_once()


def test_find_by_id_returns_matching_pet(repo_and_db, make_pet_model):
    """Verifica que find_by_id recupere la mascota mediante db.get()."""
    repo, db = repo_and_db
    pet = make_pet_model(name="Firulais")
    db.get.return_value = pet

    result = repo.find_by_id(pet.id)

    assert result == pet
    db.get.assert_called_once_with(PetModel, pet.id)


def test_find_by_id_returns_none_when_missing(repo_and_db):
    """Verifica que find_by_id devuelva None si la mascota no existe."""
    repo, db = repo_and_db
    pet_id = uuid4()
    db.get.return_value = None

    result = repo.find_by_id(pet_id)

    assert result is None
    db.get.assert_called_once_with(PetModel, pet_id)


def test_find_by_student_and_name_returns_existing_pet(repo_and_db, make_pet_model):
    """Verifica que find_by_student_and_name busque por dueño y nombre."""
    repo, db = repo_and_db
    student_id = uuid4()
    pet = make_pet_model(studentId=student_id, name="Firulais")
    db.scalar.return_value = pet

    result = repo.find_by_student_and_name(student_id, "Firulais")

    assert result == pet
    db.scalar.assert_called_once()


def test_add_adds_pet_and_flushes(repo_and_db, make_pet_model):
    """Verifica que add agregue el modelo a la sesión y ejecute flush()."""
    repo, db = repo_and_db
    pet = make_pet_model(name="Toby")

    created = repo.add(pet)

    assert created is pet
    db.add.assert_called_once_with(pet)
    db.flush.assert_called_once()


def test_delete_removes_pet_and_flushes(repo_and_db, make_pet_model):
    """Verifica que delete elimine el modelo de la sesión y ejecute flush()."""
    repo, db = repo_and_db
    pet = make_pet_model(name="Toby")

    repo.delete(pet)

    db.delete.assert_called_once_with(pet)
    db.flush.assert_called_once()
