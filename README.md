# CRUD Students & Pets (FastAPI)

Proyecto FastAPI que implementa un **CRUD** para la entidad `Student` y sus `Pet`, con persistencia en **PostgreSQL**, repositorios SQLAlchemy y migraciones Alembic.

## Tecnologías

- Python 3.13
- FastAPI + SQLAlchemy + PostgreSQL
- Alembic para las migraciones y pytest para las pruebas
- HTML + JS + Tailwind CSS (frontend estático)

## Resumen funcional

La API expone operaciones CRUD completas sobre estudiantes y mascotas:

**Estudiantes** — `/api/students`

- **Crear**: `POST /api/students` (opcionalmente con `pets[]` para crear el estudiante y sus mascotas en una sola petición)
- **Listar**: `GET /api/students`
- **Buscar por id**: `GET /api/students/:id`
- **Actualizar**: `PATCH /api/students/:id`
- **Eliminar**: `DELETE /api/students/:id` (elimina también sus mascotas)

**Mascotas** — `/api/students/:studentId/pets`

- **Listar**: `GET /api/students/:studentId/pets`
- **Crear**: `POST /api/students/:studentId/pets`
- **Actualizar**: `PATCH /api/students/:studentId/pets/:petId`
- **Eliminar**: `DELETE /api/students/:studentId/pets/:petId`

**Autenticación** — `/api/auth`

- **Registro**: `POST /api/auth/register`
- **Inicio de sesión**: `POST /api/auth/login`
- **Cierre de sesión**: `POST /api/auth/logout`
- **Sesión actual**: `GET /api/auth/me`
- **Solicitar recuperación**: `POST /api/auth/password/forgot`
- **Restablecer contraseña**: `POST /api/auth/password/reset`

### Recuperación de contraseña

El flujo usa dos endpoints y un enlace con un JWT de vida corta.

**Solicitar el enlace**

```http
POST /api/auth/password/forgot
Content-Type: application/json

{ "email": "ana@example.com" }
```

Si el correo existe, la API genera un JWT con `sub` (id del usuario), `jti` (identificador único), `purpose: "password_reset"` y `exp` de 15 minutos. El `jti` queda pendiente en la tabla `password_reset_tokens` y la respuesta incluye el enlace:

```json
{
	"code": 200,
	"success": true,
	"message": "Operación exitosa",
	"timestamp": "2026-11-17T16:00:00.000Z",
	"data": {
		"reset_link": "http://localhost:3000/reset-password.html?token=..."
	}
}
```

Si el correo no existe, la respuesta mantiene el mismo formato pero con `reset_link: null` y no se crea ningún token. Al pedir un enlace nuevo se invalida el anterior del mismo usuario.

> En esta demo el correo no se envía: la API devuelve el enlace y la UI lo muestra como un enlace clickeable dentro de un bloque de "correo simulado". En producción el enlace debe enviarse por correo y no incluirse en la respuesta.

**Restablecer la contraseña**

```http
POST /api/auth/password/reset
Content-Type: application/json

{
	"reset_token": "...",
	"new_password": "nueva-clave-123"
}
```

La API valida firma, expiración y `purpose`, busca el `jti` pendiente y comprueba que no esté usado. Luego actualiza la contraseña, marca el token como usado y elimina todas las sesiones del usuario en una sola transacción. Responde `204 No Content`.

Si el token es inválido, expiró o ya fue usado, responde `401` con el mensaje `El enlace de recuperación no es válido o expiró`.

> El `204` es la única respuesta que no usa el envelope JSON, porque no tiene cuerpo. El middleware y el cliente estático lo manejan como caso especial.

### Alta de estudiante con mascotas

`POST /api/students` acepta un arreglo opcional `pets`:

```json
{
	"name": "Ana Pérez",
	"username": "ana_perez",
	"email": "ana@example.com",
	"age": 21,
	"pets": [
		{ "name": "Firulais", "species": "perro", "age": 3 },
		{ "name": "Michi", "species": "gato" }
	]
}
```

Si no se envía `pets` (o se envía vacío), el comportamiento es exactamente el mismo de antes.

> **Punto de transacción:** el estudiante y sus mascotas se insertan dentro de una sola transacción SQLAlchemy. El servicio confirma los cambios con `commit()` al finalizar; si una mascota provoca un conflicto antes de ese paso, el cierre de la sesión revierte las escrituras pendientes. La suite E2E verifica que los nombres duplicados no dejen al estudiante persistido.

### Modelo de datos

| Estudiante | Mascota        |
| ---------- | -------------- |
| id (UUID)  | id (UUID)      |
| name       | studentId      |
| username   | name           |
| email      | species        |
| age        | age (opcional) |
| createdAt  | createdAt      |
| updatedAt  | updatedAt      |

### Validación y unicidad

La validación se realiza con Pydantic v2:

- `name` (estudiante): texto de 3 a 100 caracteres, sin etiquetas HTML.
- `username`: texto de 3 a 30 caracteres, solo minúsculas, números y guiones bajos (`^[a-z0-9_]+$`).
- `email`: dirección de correo electrónico válida.
- `age` (estudiante): entero entre 18 y 99.
- `name` / `species` (mascota): texto de 1 a 50 caracteres, sin etiquetas HTML.
- `age` (mascota): entero entre 0 y 100 (opcional).

Unicidad (rechazado con `409 Conflict`):

- Estudiante: `email` y `username` deben ser únicos.
- Mascota: `name` debe ser único dentro de un mismo estudiante, sin distinguir mayúsculas y minúsculas (`Firulais` y `FIRULAIS` generan un conflicto).

## Estándar de respuesta JSON

Toda respuesta de la API — exitosa o de error — usa el mismo **envelope** `ApiResponse`, definido en [`app/shared/api_response.py`](app/shared/api_response.py). Esto permite que el frontend interprete cualquier respuesta de forma uniforme.

### Envelope común

| Campo       | Tipo                | Descripción                                                               |
| ----------- | ------------------- | ------------------------------------------------------------------------- |
| `code`      | `number`            | Código de estado HTTP (coincide con el status de la respuesta).           |
| `success`   | `boolean`           | `true` si la operación se completó, `false` si hubo error.                |
| `message`   | `string`            | Resumen legible del resultado (varía según el método HTTP).               |
| `timestamp` | `string`            | Fecha/hora en ISO 8601 de la respuesta.                                   |
| `data`      | `object \| null`    | Datos de la operación. Presente en éxito; `null` en errores.              |
| `error`     | `string` (opcional) | Mensaje de error para errores simples (404, 500).                         |
| `errors`    | `object` (opcional) | Errores por campo para validación (400) y conflicto (409). Ver más abajo. |

### Respuestas de éxito

Un middleware global ([`api_response.py`](app/shared/api_response.py)) envuelve el retorno de los controladores en `data`:

- **Recurso único** (`GET :id`, `POST`, `PATCH`, `DELETE`): `data` contiene la entidad directamente.
- **Listado** (`GET` colección): `data` contiene `{ total, items }`.

```json
{
  "code": 201,
  "success": true,
  "message": "Recurso creado",
  "timestamp": "2026-09-09T16:49:33.368Z",
  "data": {
    "id": "c3600646-abe8-4be3-8096-d6ad629388e2",
    "name": "Juan Pérez",
    "username": "juanperez",
    "email": "juan@example.com",
    "age": 20,
    "createdAt": "2026-09-09T16:49:33.000Z",
    "updatedAt": "2026-09-09T16:49:33.000Z"
  }
}
```

`message` según el método HTTP:

| Método   | `message`             | `code` |
| -------- | --------------------- | ------ |
| `GET`    | `Operación exitosa`   | 200    |
| `POST`   | `Recurso creado`      | 201    |
| `PATCH`  | `Recurso actualizado` | 200    |
| `DELETE` | `Recurso eliminado`   | 200    |

### Errores simples (404, 500)

Los errores sin detalle por campo usan el campo `error`:

```json
{
  "code": 404,
  "success": false,
  "message": "Estudiante no encontrado",
  "timestamp": "2026-09-09T16:49:53.816Z",
  "data": null,
  "error": "Estudiante no encontrado"
}
```

### Validación (400) y conflicto (409)

Ambos casos comparten el **mismo esquema** para que el frontend los trate igual: el campo `errors` es un mapa `{ campo: { message } }`, donde la clave es el nombre del campo que falla.

```json
{
  "code": 400,
  "success": false,
  "message": "Error de validación",
  "timestamp": "2026-09-09T16:39:30.397Z",
  "data": null,
  "errors": {
    "name": { "message": "El nombre debe tener entre 3 y 100 caracteres" },
    "email": { "message": "El correo electrónico no es válido" }
  }
}
```

```json
{
  "code": 409,
  "success": false,
  "message": "Conflicto con datos existentes",
  "timestamp": "2026-09-09T16:49:45.110Z",
  "data": null,
  "errors": {
    "email": { "message": "El correo electrónico ya está en uso" }
  }
}
```

- `400 Bad Request`: cuando falla la validación. Los DTOs replican las reglas y mensajes de class-validator (NestJS) en español; el handler global ([`exceptions.py`](app/shared/exceptions.py)) convierte los errores al mapa `{ campo: { message } }` (si un campo falla varias reglas, los mensajes se concatenan con `", "`; las propiedades no permitidas devuelven `errors: {}`).
- `409 Conflict`: cuando se viola una restricción de unicidad. Los servicios lanzan una `HTTPException` con el mismo mapa `errors`, por lo que es indistinguible de una validación a nivel de estructura.

### Interpretación en el frontend

El cliente estático (`public/`) consume este estándar de forma uniforme:

- `public/js/api.js` expone `api()` (hace `fetch` y devuelve `data` en éxito o lanza el envelope en error) y `normalizeErrors()` (convierte `{ campo: { message } }` en `{ campo: message }`).
- En los formularios, si la respuesta trae `errors`, cada mensaje se muestra bajo su input correspondiente; si trae `error`, se muestra como notificación global (toast).

## Contexto técnico

- **Backend**: FastAPI
- **Persistencia**: PostgreSQL mediante SQLAlchemy; esquema gestionado con Alembic
- **Validación**: Pydantic v2
- **Autenticación**: sesiones en PostgreSQL; recuperación de contraseña con JWT firmado (PyJWT)
- **Frontend**: archivos estáticos en `public/` (Alpine.js + Tailwind CSS + vanilla-sonner, vía CDN)
- **Gestor de dependencias**: uv
- **Documentación**: Swagger en `/docs`

La recuperación de contraseña se configura con `PASSWORD_RESET_SECRET` y `PASSWORD_RESET_TTL_MINUTES`. Los valores de desarrollo están en [`.env.example`](.env.example) y el secreto debe cambiarse en producción.

## Ejecución local

1. Instalar dependencias:

    ```bash
    make install
    ```

    O directamente con uv:

    ```bash
    uv sync
    ```

2. Levantar PostgreSQL de desarrollo:

    ```bash
    docker compose up -d --wait db
    ```

3. Aplicar las migraciones y levantar el servidor en modo desarrollo:

    ```bash
    make dev
    ```

    O usando uv:

    ```bash
    uv run alembic upgrade head
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
    ```

La aplicación queda disponible en:

- `http://localhost:3000`
- `http://localhost:3000/docs`

> PostgreSQL de desarrollo usa el volumen `pgdata`: los datos se conservan al reiniciar la API y al ejecutar `docker compose down`. La base de pruebas usa datos temporales independientes.

## Pruebas

La suite cubre las entidades `Student` y `Pet`, con tests unitarios y E2E.

| Módulo | Pruebas unitarias | Pruebas E2E |
| --- | --- | --- |
| Students | Validación de schemas y reglas de `StudentsService` con repositorios falsos. | CRUD autenticado, validación, conflictos, recursos inexistentes, alta con mascotas, rollback y eliminación en cascada. |
| Pets | Schemas de entrada y salida (`Pet` y `PetList`), lógica de `PetsService` con repositorios falsos y llamadas de `PetsRepository` con una sesión SQLAlchemy simulada. | CRUD autenticado, listado por estudiante, validación (`400`), nombres duplicados sin distinguir mayúsculas y minúsculas, acceso a mascotas de otro estudiante, alta anidada y eliminación en cascada. |

Los tests unitarios no requieren PostgreSQL. Los E2E usan `TestClient`, una sesión autenticada real y PostgreSQL de prueba; recorren las rutas, dependencias, servicios, repositorios y respuestas de la API.

Los casos de borde del servicio de Pets comprueban los `404` para identificadores inválidos o recursos inexistentes, los conflictos `409` por nombre sin distinguir mayúsculas y minúsculas, y la actualización parcial que permite limpiar la edad con `age=None` sin cambiar los demás campos. Las operaciones rechazadas no deben ejecutar `commit()`.

### Conteo verificado en esta revisión

| Módulo | Unitarios aprobados | E2E aprobados | Total |
| --- | ---: | ---: | ---: |
| Students | 55 | 24 | 79 |
| Pets | 55 | 18 | 73 |
| **Total** | **110** | **42** | **152** |

Los casos parametrizados cuentan una vez por cada variante ejecutada. Este conteo incluye las pruebas de esta revisión y debe actualizarse al integrar nuevas pruebas.

La base de test es independiente de la de desarrollo:

- Servicio `db-test` definido en `docker-compose.test.yml`.
- Puerto `5433`.
- Base `icinf1108_test`.
- Datos en `tmpfs`, por lo que se pierden al bajar el contenedor.
- El esquema se crea con las migraciones de Alembic.
- Las tablas se truncan antes de cada test.

Comandos:

```bash
make test-unit           # unitarios, sin base de datos
make test-e2e            # levanta db-test y ejecuta los E2E
make test                # suite completa
make test-down           # baja db-test y elimina sus datos
```

También se puede ejecutar directamente, en este orden, desde la raíz del repositorio y con Docker Desktop iniciado:

```bash
uv sync
uv run pytest -m unit
docker compose -f docker-compose.test.yml up -d --wait
uv run pytest -m e2e
```

Con la base de prueba levantada, se puede ejecutar toda la suite y después detener el contenedor:

```bash
uv run pytest
docker compose -f docker-compose.test.yml down -v
```

Si necesitas apuntar a otra base, define `TEST_DATABASE_URL`. El nombre de la base debe terminar en `_test` para evitar truncar una base de desarrollo por error.

### Cómo leer los tests

- Los nombres de las funciones indican el comportamiento esperado; algunos casos incluyen un docstring con más detalle.
- Los casos parametrizados usan `ids` legibles, por ejemplo `vacio`, `corto` o `html`.
- `tests/conftest.py` documenta las fixtures de base de datos, `TestClient` y sesión autenticada.
- `tests/students/conftest.py` y `tests/pets/conftest.py` contienen los repositorios falsos y los datos reutilizables de cada módulo.
- `tests/pets/unit/` agrupa los tests de schemas, servicio y repositorio; `tests/pets/e2e/test_pets_api.py` contiene los escenarios HTTP de mascotas.
- Los tests unitarios no tocan PostgreSQL. Los E2E usan la base de test y una sesión real.

Para ejecutar un test puntual:

```bash
uv run pytest tests/students/unit/test_service.py::test_create_without_pets -v
uv run pytest tests/pets/unit/test_service.py::test_update_pet_not_found -v
uv run pytest tests/pets/e2e/test_pets_api.py -v
```

## Comandos útiles

- `make install` — sincroniza dependencias con uv
- `make dev` — arranca uvicorn en modo reload
- `make lint` — ejecuta Ruff (con autocorrección)
- `make format` — formatea el código con Ruff
- `make format-check` — verifica el formato
- `make clean` — elimina `.venv`, cachés y artefactos
