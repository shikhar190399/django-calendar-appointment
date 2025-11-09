# Appointment Scheduling – Django + Postgres + DRF

A production-ready starter that exposes a REST API for booking, rescheduling, listing, and cancelling 30-minute appointment slots. The project uses Poetry for dependency management, PostgreSQL for persistence, and Django REST Framework to serve the API.

> **Features**
> - Week-based availability with pagination (current week + future weeks)
> - Booking validation: business hours, half-hour increments, no past bookings, and double-booking protection
> - CRUD endpoints for appointments (`GET`, `POST`, `PATCH`, `DELETE`)
> - CORS configuration for SPA/front-end integration

## 1. Prerequisites

- Python 3.11 or newer (3.13 supported)
- [Poetry](https://python-poetry.org/docs/#installation)
- PostgreSQL database (local or hosted)

## 2. Bootstrap the project

```bash
git clone https://github.com/shikhar190399/django-calendar-appointment.git
cd django-calendar-appointment

poetry env use python3                # optional if multiple Python versions installed
poetry install

cp .env.example .env                  # edit credentials to match your environment
```

Update `.env` with your database URL, secret key, and CORS origins.

## 3. Database & migrations

```bash
poetry run python manage.py migrate
# Optional: create an admin user for the Django admin site
poetry run python manage.py createsuperuser
```

The default database URL is `postgresql://postgres:postgres@localhost:5432/appointment_scheduling`. Override `DATABASE_URL` in `.env` for production/hosted instances.

## 4. Run the development server

```bash
poetry run python manage.py runserver
```

API base URL (default): `http://127.0.0.1:8000/api/`

## 5. Running tests & linters

```bash
poetry run pytest           # unit/integration tests
poetry run black .          # formatting (already configured)
poetry run isort .          # import sorting
```

## 6. REST API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/appointments?page=0` | Paginated appointments for the given week (0 = current) |
| `POST` | `/api/appointments` | Book a new appointment |
| `PATCH` | `/api/appointments/<id>` | Update appointment details or reschedule to a new slot |
| `DELETE` | `/api/appointments/<id>` | Cancel an appointment |
| `GET` | `/api/appointments/<id>` | Fetch a single appointment |
| `GET` | `/api/appointments/available?page=0` | Available slots for the given week |

### Example `curl` commands

```bash
# Create
curl -X POST http://127.0.0.1:8000/api/appointments \
  -H "Content-Type: application/json" \
  -d '{"start_time":"2025-11-10T17:00:00Z","name":"Ada Lovelace","email":"ada@example.com"}'

# Update / reschedule
curl -X PATCH http://127.0.0.1:8000/api/appointments/1 \
  -H "Content-Type: application/json" \
  -d '{"start_time":"2025-11-11T15:30:00Z","reason":"Rescheduled"}'

# Cancel
curl -X DELETE http://127.0.0.1:8000/api/appointments/1

# Availability (next week)
curl http://127.0.0.1:8000/api/appointments/available?page=1
```

Responses use ISO8601 timestamps and include pagination metadata (`page`, `next_page`, etc.).

## 7. Environment variables

All configuration is loaded from `.env` at start-up. Defaults are aimed at local development.

| Variable | Purpose | Default |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Django crypto key | `django-insecure-change-me` |
| `DJANGO_DEBUG` | Enable/disable debug mode | `true` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames | `localhost,127.0.0.1` |
| `DJANGO_TIME_ZONE` | Server time zone | `UTC` |
| `DATABASE_URL` | Postgres connection URI | `postgresql://postgres:postgres@localhost:5432/appointment_scheduling` |
| `DATABASE_CONN_MAX_AGE` | Persistent connection lifetime | `600` |
| `DATABASE_SSL_REQUIRE` | Force SSL for DB connection | `false` |
| `CORS_ALLOWED_ORIGINS` | Allowed front-end origins | `http://localhost:3000,http://127.0.0.1:3000` |
| `CORS_ALLOW_CREDENTIALS` | Include cookies/credentials in CORS responses | `false` |

> **Pro tip:** For production, set `DJANGO_DEBUG=false`, generate a strong `DJANGO_SECRET_KEY`, and adjust `DJANGO_ALLOWED_HOSTS`.

## 8. Deploy / production checklist

- Run `poetry install --no-dev` on the server or build stage
- Configure environment variables (`DATABASE_URL`, etc.)
- Apply migrations: `poetry run python manage.py migrate`
- Collect static assets if serving via Django: `poetry run python manage.py collectstatic`
- Configure a WSGI/ASGI server (Gunicorn/Uvicorn) behind a reverse proxy
- Ensure CORS origins match deployed front-end URLs
- (Optional) add monitoring, logging, and scheduled jobs if needed

## 9. Contributing / local development

1. Fork and clone the repository
2. Install dependencies with Poetry
3. Make changes in a feature branch
4. Run tests/linters before opening a pull request

---

Happy building! Let us know via issues or pull requests if you add features or find bugs.

