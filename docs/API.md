# REST API

Base URL: `/api/v1/`. Interactive docs (Swagger UI): `/api/v1/docs/`. Raw OpenAPI schema: `/api/v1/schema/`.

Intended for future mobile app clients. The server-rendered web pages don't use this API - they use Django views/templates directly.

## Authentication

JWT (via `djangorestframework-simplejwt`). Access tokens last 30 minutes, refresh tokens 7 days (refresh tokens rotate on use).

```bash
# Get a token pair
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -d "username=staff_london&password=staffpass123"
# -> {"access": "...", "refresh": "..."}

# Use it
curl http://localhost:8000/api/v1/complaints/ \
  -H "Authorization: Bearer <access_token>"

# Refresh when it expires
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -d "refresh=<refresh_token>"
```

Public endpoints (missions, appointment slots, the assistant) don't require a token.

## Permissions

Every mission-scoped endpoint uses the exact same `missions/utils/permissions.py` helpers the web views use (`user_is_ministry_admin`, `user_can_manage_mission`, `missions_for_user`) - the API cannot be used to see or act on data the same user couldn't see/act on through the web UI.

## Endpoints

| Endpoint | Methods | Auth | Notes |
|---|---|---|---|
| `/missions/` | GET | None | Public mission directory. Filter: `?country=`, `?mission_type=`. Search: `?search=`. |
| `/appointment-slots/` | GET | None | Public, upcoming slots only. Filter: `?mission=`, `?service=`. |
| `/appointments/` | GET | Required | List: scoped to own missions (staff) or all (ministry admin). |
| `/appointments/` | POST | None | Book an appointment. Same no-double-booking guarantee as the web form - a full slot auto-waitlists instead of erroring. |
| `/queue-tickets/` | GET | Required | Today's tickets, scoped like appointments. |
| `/queue-tickets/` | POST | None | Join the walk-in queue; returns a sequential ticket number. |
| `/complaints/` | GET | Required | Read-only. Complaint *creation* stays on the web form only (it has anti-spam CAPTCHA and rate limiting this API doesn't replicate yet). |
| `/notifications/` | GET | Required | Own notifications only. |
| `/notifications/{id}/mark_read/` | POST | Required | Mark one notification read. 404 if it's not yours. |
| `/notifications/mark_all_read/` | POST | Required | Mark all of your notifications read. |
| `/assistant/ask/` | POST | None | `{"question": "..."}` -> matched topic + answer + suggested action. Rate-limited to 30/hour per IP. |
| `/kpi/summary/` | GET | Required | Mission-scoped complaint/appointment/queue counts. 403 if you have no mission access at all. |

Standard DRF pagination (`?page=N`), search (`?search=`), and ordering (`?ordering=field`) apply where listed above.

## Versioning

Everything lives under `/api/v1/`. A future breaking change would ship as `/api/v2/` alongside it, not replace v1 in place.
