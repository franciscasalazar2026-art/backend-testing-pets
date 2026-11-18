from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.pets.schemas import Pet, PetList

pytestmark = pytest.mark.unit


def test_serializacion_pet():
    pet_id = uuid4()
    student_id = uuid4()
    ahora = datetime(2026, 11, 18, 12, 0, 0, tzinfo=timezone.utc)

    dto = Pet(
        id=pet_id,
        studentId=student_id,
        name="Firulais",
        species="perro",
        age=3,
        createdAt=ahora,
        updatedAt=ahora,
    )

    assert dto.id == pet_id
    assert dto.studentId == student_id
    assert dto.name == "Firulais"
    assert dto.species == "perro"
    assert dto.age == 3
    assert dto.createdAt == ahora
    assert dto.updatedAt == ahora


def test_pet_edad_nula():
    ahora = datetime.now(timezone.utc)

    dto = Pet(
        id=uuid4(),
        studentId=uuid4(),
        name="Michi",
        species="gato",
        age=None,
        createdAt=ahora,
        updatedAt=ahora,
    )

    assert dto.age is None


def test_pet_list():
    ahora = datetime.now(timezone.utc)
    student_id = uuid4()

    items = [
        Pet(
            id=uuid4(),
            studentId=student_id,
            name="Firulais",
            species="perro",
            age=3,
            createdAt=ahora,
            updatedAt=ahora,
        ),
        Pet(
            id=uuid4(),
            studentId=student_id,
            name="Michi",
            species="gato",
            age=None,
            createdAt=ahora,
            updatedAt=ahora,
        ),
    ]

    respuesta = PetList(total=2, items=items)

    assert respuesta.total == 2
    assert len(respuesta.items) == 2
    assert respuesta.items[0].name == "Firulais"
    assert respuesta.items[1].age is None


def test_pet_campos_obligatorios_faltantes():
    with pytest.raises(ValidationError):
        Pet(name="Firulais", species="perro")