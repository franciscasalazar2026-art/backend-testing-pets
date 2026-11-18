"""Pruebas unitarias de los schemas de Pets."""

import pytest
from pydantic import ValidationError

from app.pets.schemas import CreatePetDto, UpdatePetDto

pytestmark = pytest.mark.unit


def test_create_pet_valid(pet_payload):
    dto = CreatePetDto(**pet_payload())

    assert dto.name == "Firulais"
    assert dto.species == "perro"
    assert dto.age == 3


def test_create_pet_without_age(pet_payload):
    payload = pet_payload()
    del payload["age"]

    dto = CreatePetDto(**payload)

    assert dto.age is None


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("", "El nombre no puede estar vacío"),
        ("a" * 51, "El nombre debe tener entre 1 y 50 caracteres"),
        ("<b>Firulais</b>", "No se permiten etiquetas HTML"),
        (123, "El nombre debe ser un texto"),
        (None, "El nombre debe ser un texto"),
    ],
    ids=["vacio", "largo", "html", "no-texto", "none"],
)
def test_create_pet_invalid_name(pet_payload, name, message):
    with pytest.raises(ValidationError) as error:
        CreatePetDto(**pet_payload(name=name))

    assert message in str(error.value)


@pytest.mark.parametrize(
    ("species", "message"),
    [
        ("", "La especie no puede estar vacía"),
        ("a" * 51, "La especie debe tener entre 1 y 50 caracteres"),
        ("<script>gato</script>", "No se permiten etiquetas HTML"),
        (456, "La especie debe ser un texto"),
        (None, "La especie debe ser un texto"),
    ],
    ids=["vacio", "largo", "html", "no-texto", "none"],
)
def test_create_pet_invalid_species(pet_payload, species, message):
    with pytest.raises(ValidationError) as error:
        CreatePetDto(**pet_payload(species=species))

    assert message in str(error.value)


@pytest.mark.parametrize(
    ("age", "message"),
    [
        (-1, "La edad debe ser al menos 0"),
        (101, "La edad debe ser como máximo 100"),
        ("tres", "La edad debe ser un número entero"),
    ],
    ids=["negativa", "mayor-100", "no-entero"],
)
def test_create_pet_invalid_age(pet_payload, age, message):
    with pytest.raises(ValidationError) as error:
        CreatePetDto(**pet_payload(age=age))

    assert message in str(error.value)


def test_create_pet_forbids_extra_fields(pet_payload):
    with pytest.raises(ValidationError):
        CreatePetDto(**pet_payload(color="café"))


def test_update_pet_partial_valid():
    dto = UpdatePetDto(name="Max")

    assert dto.name == "Max"
    assert dto.species is None
    assert dto.age is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": "a" * 51}, "El nombre debe tener entre 1 y 50 caracteres"),
        ({"name": "<i>Max</i>"}, "No se permiten etiquetas HTML"),
        ({"species": "a" * 51}, "La especie debe tener entre 1 y 50 caracteres"),
        ({"species": "<gato>"}, "No se permiten etiquetas HTML"),
        ({"age": -5}, "La edad debe ser al menos 0"),
        ({"age": 150}, "La edad debe ser como máximo 100"),
    ],
    ids=[
        "name-largo",
        "name-html",
        "species-largo",
        "species-html",
        "age-negativa",
        "age-mayor-100",
    ],
)
def test_update_pet_invalid_fields(overrides, message):
    with pytest.raises(ValidationError) as error:
        UpdatePetDto(**overrides)

    assert message in str(error.value)