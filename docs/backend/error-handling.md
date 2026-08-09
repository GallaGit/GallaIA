# Error Handling

## Purpose

Define a consistent JSON error shape and map application exceptions to HTTP responses.

## Status

Draft (reflects current implementation)

## Scope

- Existing: `AppError` hierarchy in `app/exceptions/base.py`; handlers in `app/exceptions/handlers.py`; registered in `main.py`.
- Planned: richer codes (validation catalogs, upstream providers).
- Future: problem+json or public error catalog if needed.

## Response shape

```json
{
  "error": {
    "code": "not_found",
    "message": "Resource not found"
  }
}
```

Do not confuse with FastAPI’s default `{"detail": "..."}` (used when a route is missing). Application errors use the `error` object above.

## Types today

| Class | code | status |
|-------|------|--------|
| `NotFoundError` | `not_found` | 404 |
| `BadRequestError` | `bad_request` | 400 |
| Unhandled `Exception` | `internal_error` | 500 (no stack to client) |

## Usage

Raise in handlers/services: `raise NotFoundError("...")`. Do not hand-build error JSON in routes.

Demo route (learning only): `GET /api/v1/demo-error`.

## Code

- [`backend/app/exceptions/base.py`](../../backend/app/exceptions/base.py)
- [`backend/app/exceptions/handlers.py`](../../backend/app/exceptions/handlers.py)
- [`backend/app/main.py`](../../backend/app/main.py)

## TODO

- Remove or gate the demo-error route before production-facing releases.
- Align validation (`RequestValidationError`) with the same envelope if desired.
