# Flutter API Contract — Gym Management System Backend

Generated from the live OpenAPI schema (`GET /openapi.json`) plus source review, against
FastAPI + PostgreSQL 16 + Redis. Base path for all application endpoints: **`/api/v1`**.
Health checks are at the root (no `/api/v1` prefix).

---

## 1. Conventions (read this first)

### Base URL
**Production**: `https://local-gym-backend.onrender.com/api/v1`
WebSocket: `wss://local-gym-backend.onrender.com/api/v1/ws/...`
Interactive docs: `https://local-gym-backend.onrender.com/docs`

Local dev (only if running the backend yourself via `docker compose up`): `http://localhost:8000/api/v1` / `ws://localhost:8000/api/v1/ws/...`

### Authentication
Bearer JWT in the `Authorization` header on every protected request:
```
Authorization: Bearer <access_token>
```
No cookies are used. Access tokens expire in ~20 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`); refresh
tokens in ~14 days. See §2 for the full login/refresh/logout flow.

### Error envelope (uniform across the entire API)
Every non-2xx response (except FastAPI's raw 404 for an unmatched route, and WebSocket close
frames) has this shape:
```json
{ "error": { "code": "not_found", "message": "Member not found" } }
```
Validation errors (422) additionally include a `details` array (Pydantic-style, field-level):
```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input",
    "details": [
      { "type": "string_too_short", "loc": ["body", "password"], "msg": "String should have at least 10 characters", "input": "[redacted]", "ctx": {"min_length": 10} }
    ]
  }
}
```
`input` is redacted to `"[redacted]"` for password/token fields specifically; other fields echo
the submitted value to aid debugging.

**Field name note:** the top-level, always-present field is `error.message` (not `msg`). Only
inside a 422's `details[]` array does the per-field message use Pydantic's own field name `msg`
— that's a different field at a different nesting level, not an inconsistency. For a generic
error display, read `error.message`; only reach into `details[].msg` if you want field-level
inline validation errors.

Common `error.code` values you should branch on in the client: `not_found`, `forbidden`,
`unauthorized`, `conflict`, `bad_request`, `rate_limited` (429, includes a `Retry-After` header),
`validation_error` (422), `internal_error` (500 — generic message only, never a stack trace).
A `429` also carries `Retry-After` as a response header (seconds).

**IDOR note for the client:** requesting another user's resource by ID returns a plain `404`
(`not_found`), not `403` — the API deliberately doesn't distinguish "doesn't exist" from "not
yours". Don't special-case 403 vs 404 as "exists but forbidden" vs "doesn't exist".

### Pagination (uniform shape)
```json
{ "items": [ /* ... */ ], "total": 137, "page": 1, "page_size": 20, "pages": 7 }
```
Query params are always `page` (default 1) and `page_size` (default 20, most endpoints cap at
100). Paginated endpoints: `GET /members`, `GET /store/products`, `GET /store/orders`,
`GET /admin/audit-logs`. (Other list endpoints — exercises, classes, plans, FAQs, etc. — return a
plain JSON array, not paginated; they're expected to be small.)

### IDs
All primary keys are **UUIDv4, lowercase, hyphenated string form** (`"26741657-a75e-4c4c-9f48-e7dc77e9eecb"`).
Consistent everywhere — request bodies, path params, response bodies.

### Timestamps
ISO-8601, **always UTC**, always suffixed `Z` (never a numeric offset), microsecond precision:
```
"2026-09-06T12:12:12.648177Z"
```
`DateTime.parse()` in Dart handles this natively and yields a UTC `DateTime`. Plain `date` fields
(e.g. `date_of_birth`, `expiry_date`, `scheduled_date`) are `"YYYY-MM-DD"` with no time component.

### Money / decimals — important
**Every money/decimal field is serialized as a JSON string, not a number**: `"price": "29.99"`,
not `"price": 29.99`. This is deliberate (avoids float precision loss). Affected fields: all
`price`, `unit_price`, `subtotal`, `discount_total`, `total`, `price_at_purchase`,
`discount_value`, `revenue_month`. **Do not deserialize these as `double`/`num` directly** — parse
the string (`Decimal.parse()` from the `decimal` package, or `double.parse()` if precision loss is
acceptable for display only). On the way *in*, request bodies accept either a JSON number or a
string for these fields (e.g. `"price": 29.99` or `"price": "29.99"` both work) — but expect
**string** back out.

### Enums
Sent/received as their plain uppercase string value (e.g. `"role": "MEMBER"`), not numeric. Full
list in §12.

### Nullability
Optional fields are explicit `"field": null` in responses (fields are never omitted), so Dart
models should mark them nullable rather than relying on key-absence. Request bodies: fields with
no default and not marked optional below are required; omitting them is a 422.

### Multipart uploads
Every upload endpoint takes exactly one field, always named **`file`**, `multipart/form-data`,
and returns the full parent resource (not just a URL) with the new `..._url`/`media_url` field
populated. Uploaded images are re-validated server-side by sniffing actual file bytes (JPEG/PNG/
WEBP accepted, ≤8MB) — the client's declared Content-Type/extension is not trusted, so a renamed
non-image file is rejected with `400 bad_request` regardless of its extension.

**Every accepted image is server-side resized (max 1200px on the longest side, never upscaled)
and re-encoded as JPEG (quality 80), regardless of the upload format** — so the returned URL
always ends in `.jpg`, even if you uploaded a `.png`. This is intentional (keeps storage/bandwidth
usage low with no visible quality loss on a phone screen); don't assume the output matches your
input format or resolution. The stored filename is always randomly generated (never the original
filename), and EXIF metadata (including GPS) is stripped in the process.

### WebSocket
One endpoint: `GET /api/v1/ws/chat/{conversation_id}?token=<access_token>` (upgrade request).
Token is a **query parameter** (not a header — browser/Flutter WS clients can't always set
headers on the handshake). Same access token as REST. Full details in §10.

---

## 2. Auth — `/api/v1/auth/*`

### `POST /auth/register`
Public. Rate-limited (3/min per IP, `RATE_LIMIT_REGISTER_PER_MINUTE`). No role — a `"role"` key in
the body is silently ignored (never trust the client for role assignment; this always creates a
`MEMBER`).
- Body: `{ "email": string(email), "password": string(10–128 chars), "full_name": string(1–150) }`
- 201 → `TokenPairResponse`: `{ "access_token": string, "refresh_token": string, "token_type": "bearer", "role": UserRole }`
  (always `"MEMBER"` for this endpoint — included for shape-consistency with login/refresh, see below)
- Errors: `409 conflict` (email taken), `422 validation_error`

### `POST /auth/login`
Public. Rate-limited (5/min per IP, `RATE_LIMIT_LOGIN_PER_MINUTE`).
- Body: `{ "email": string, "password": string }`
- 200 → `TokenPairResponse` (same shape as register) — **`role` tells the client which
  dashboard/navigation to route to immediately after login, without a follow-up `GET /auth/me` call.**
- Errors: `401 unauthorized` (wrong password OR disabled account — same message either way), `429 rate_limited`

### `POST /auth/refresh`
Public (the refresh token itself is the credential). Rate-limited (20/min per IP).
- Body: `{ "refresh_token": string }`
- 200 → `TokenPairResponse` — **both** tokens are new; the old refresh token is now invalid (rotation).
  `role` is included here too (re-derived from the account on every refresh), so a long-lived session
  always has the current role on hand without re-fetching `/auth/me`.
- Errors: `401 unauthorized` — covers: expired, malformed, unknown, **or already-used** (reuse of a
  rotated token revokes the *entire* session family — every refresh token issued from that login is
  invalidated; the user must log in again). The client must always store the *new* pair from every
  refresh response and discard the old one.

### `POST /auth/logout`
Requires auth. Revokes one refresh session (the one whose token you pass — not necessarily the
caller's current access token's session).
- Body: `{ "refresh_token": string }`
- 200 → `{ "message": string }`

### `POST /auth/logout-all`
Requires auth. Revokes every refresh session for the current user (all devices).
- No body.
- 200 → `{ "message": string }`

### `GET /auth/me`
Requires auth.
- 200 → `CurrentUserResponse`: `{ "id": uuid, "email": string, "role": UserRole, "is_active": bool, "is_email_verified": bool }`

### `POST /auth/change-password`
Requires auth. **Revokes all refresh sessions** on success (forces re-login everywhere).
- Body: `{ "current_password": string, "new_password": string(10–128) }`
- 200 → `{ "message": string }`
- Errors: `400 bad_request` (current password wrong)

### `POST /auth/forgot-password`
Public. Rate-limited (3/min per IP). Always returns 200 with a generic message regardless of
whether the email exists (no account enumeration).
- Body: `{ "email": string }`
- 200 → `ForgotPasswordResponse`: `{ "message": string, "debug_reset_token": string|null }`
- In production, if the email belongs to a real account, a reset email is sent (via Brevo) containing
  the raw reset code as plain text — the user copies it into the app's Reset Password screen. The
  code expires in **30 minutes**. `debug_reset_token` is **only ever populated when the server runs
  with `DEBUG=true`** (local/dev only) — in production it's always `null`, so don't build a Flutter
  flow that reads it; the code only ever arrives by email in production.

### `POST /auth/reset-password`
Public. Rate-limited (5/min per IP). Also revokes all refresh sessions on success.
- Body: `{ "token": string, "new_password": string(10–128) }`
- 200 → `{ "message": string }`
- Errors: `400 bad_request` (invalid/expired/already-used token)

---

## 3. Member profile — `/api/v1/members/*`

### `GET /members/me`
Requires auth (any role with a member profile — i.e. MEMBER accounts).
- 200 → `MemberProfileRead`:
```json
{
  "id": "uuid", "user_id": "uuid", "full_name": "string", "photo_url": "string|null",
  "date_of_birth": "YYYY-MM-DD|null", "phone": "string|null", "height_cm": "number|null",
  "weight_kg": "number|null", "fitness_level": "FitnessLevel|null", "fitness_goal": "string|null",
  "member_code": "string (e.g. M834932)"
}
```

### `PATCH /members/me`
Requires auth (MEMBER). All fields optional (partial update).
- Body: `MemberProfileUpdate` — `full_name`, `date_of_birth`, `phone`, `height_cm`, `weight_kg`,
  `fitness_level` (enum), `fitness_goal` — same shapes as above, all optional.
- 200 → `MemberProfileRead`

### `POST /members/me/photo`
Requires auth (MEMBER). Multipart, field `file`.
- 200 → `MemberProfileRead` (with `photo_url` updated)
- Errors: `400 bad_request` (not a real image)

### `GET /members` (admin only, paginated, searchable)
- Query: `page`, `page_size`, `search` (matches name or email, `ilike`), `is_active` (bool),
  `sort_by` (whitelist: `"full_name"` or `"created_at"` — anything else → `400 bad_request`),
  `sort_desc` (bool, default `true`)
- 200 → `Page<MemberWithAccountRead>` — same fields as `MemberProfileRead` plus `email`, `is_active`.

### `GET /members/{member_id}`
Requires auth. Ownership-checked: MEMBER can only fetch their own (else `404`); TRAINER only
members currently assigned to them (else `404`); ADMIN unrestricted.
- 200 → `MemberProfileRead`

### `PATCH /members/{member_id}` (admin only)
- Body: `MemberAdminUpdate` — everything in `MemberProfileUpdate` **plus** `is_active: bool` (the
  only way to activate/deactivate a member account).
- 200 → `MemberProfileRead`

### `POST /members/assign-trainer` (admin only)
- Body: `{ "member_id": uuid, "trainer_id": uuid }`
- 200 → `{ "id": uuid, "trainer_id": uuid, "member_id": uuid }` — a member has at most **one**
  active trainer at a time; assigning a new one silently supersedes the previous assignment.

### `DELETE /members/{member_id}/trainer` (admin only)
- 200 → `{ "message": string }`
- Errors: `400 bad_request` (no active assignment to remove)

---

## 4. Trainers — `/api/v1/trainers/*`

### `GET /trainers`
Requires auth (any role). Lists active trainers only.
- 200 → `TrainerProfileRead[]`:
```json
{ "id":"uuid","user_id":"uuid","full_name":"string","photo_url":"string|null","bio":"string|null","specialization":"string|null","years_experience":"int|null","is_active":true }
```

### `GET /trainers/me` / `PATCH /trainers/me` / `POST /trainers/me/photo`
Requires auth, **TRAINER role only**. Same pattern as the member-profile equivalents.
`PATCH` body (`TrainerProfileUpdate`): `full_name`, `bio`, `specialization`, `years_experience` — all optional.

### `GET /trainers/me/members`
TRAINER only. Lists members currently assigned to the caller.
- 200 → `MemberProfileRead[]`

*(Known limitation: there is no admin endpoint to deactivate a trainer account — only members
have an `is_active` toggle via `PATCH /members/{id}`.)*

---

## 5. Memberships — `/api/v1/memberships/*`

**No online payment.** Subscribing creates a `PENDING` record; only an admin, in person, confirms
cash payment to activate it. A member can never self-activate.

### `GET /memberships/plans`
Public-ish (requires auth, any role). Query: `active_only` (default `true`).
- 200 → `MembershipPlanRead[]`: `{ "id","created_at","updated_at","name","description","duration_days":int,"price":"string","is_active":bool }`

### `POST /memberships/plans` / `PATCH /memberships/plans/{plan_id}` (admin only)
- Create body: `{ "name": string, "description": string|null, "duration_days": int>0, "price": number|string >0 }`
- Update body: all fields optional, plus `is_active: bool`.

### `GET /memberships/me`
MEMBER only. Latest subscription (any status), or `null` if the member never subscribed.
- 200 → `MembershipSubscriptionRead | null`:
```json
{
  "id":"uuid","created_at":"...","updated_at":"...", "member_id":"uuid","plan_id":"uuid",
  "plan": { "...MembershipPlanRead..." },
  "status":"MembershipStatus","payment_status":"PaymentStatus","price_at_purchase":"string",
  "start_date":"date|null","expiry_date":"date|null","confirmed_by":"uuid|null",
  "confirmed_at":"datetime|null","cancelled_at":"datetime|null","notes":"string|null"
}
```

### `GET /memberships/subscriptions` (admin only, paginated)
The admin-side list — use this to find subscriptions awaiting an in-person cash payment (filter
`status_filter=PENDING`), which is what you act on via `confirm-payment` below.
- Query: `page`, `page_size`, `status_filter` (MembershipStatus), `payment_status_filter` (PaymentStatus)
- 200 → `Page<MembershipSubscriptionAdminRead>` — same fields as `MembershipSubscriptionRead` below,
  **plus an embedded `member: MemberProfileRead`** so you can show who it belongs to without a
  second lookup (the member's own `GET /memberships/me` doesn't embed this — it already knows who
  it belongs to).

### `POST /memberships/subscribe`
MEMBER only.
- Body: `{ "plan_id": uuid }`
- 201 → `MembershipSubscriptionRead` (`status="PENDING"`, `payment_status="PENDING"`)
- Errors: `409 conflict` (already has an open PENDING/ACTIVE subscription — enforced at the DB
  level, safe under concurrent double-taps), `404` (bad/inactive plan)

### `POST /memberships/{subscription_id}/confirm-payment` (admin only)
- Body: `{ "notes": string|null }`
- 200 → `MembershipSubscriptionRead` (now `ACTIVE`/`PAID`, `start_date`/`expiry_date` set)
- Errors: `403 forbidden` if a MEMBER calls this (even for their own subscription) — this is the
  one endpoint the Flutter app should never expose a "confirm" button for.

### `POST /memberships/{subscription_id}/extend` (admin only)
- Body: `{ "additional_days": int, 1–730 }`
- 200 → `MembershipSubscriptionRead`

### `POST /memberships/{subscription_id}/cancel`
MEMBER (own, and only if not yet `PAID`) or ADMIN (any, including paid → refunded).
- No body.
- 200 → `MembershipSubscriptionRead`
- Errors: `400 bad_request` (member trying to cancel an already-paid subscription — admin required), `409 conflict` (already cancelled/expired)

---

## 6. Exercises — `/api/v1/exercises/*`

### `GET /exercises`
Requires auth (any role). Query: `muscle_group` (exact match), `active_only` (default `true`).
- 200 → `ExerciseRead[]`: `{ "id","created_at","updated_at","name","description","muscle_group","equipment","difficulty":"DifficultyLevel|null","instructions","media_url","is_active" }`

### `POST /exercises` / `PATCH /exercises/{exercise_id}` (ADMIN or TRAINER)
- Create body: `{ "name": string, "description"?, "muscle_group"?, "equipment"?, "difficulty"?: DifficultyLevel, "instructions"?, "media_url"? }`
- Update: all optional, plus `is_active`.

### `POST /exercises/{exercise_id}/media` (ADMIN or TRAINER)
Multipart, field `file`. 200 → `ExerciseRead` with `media_url` set.

---

## 7. Workouts — `/api/v1/workouts/*`

### `POST /workouts/programs`
TRAINER only, and only for a member currently assigned to that trainer (else `403`).
- Body (`WorkoutProgramCreate`) — nested create in one call:
```json
{
  "member_id": "uuid", "name": "string", "description": "string|null",
  "start_date": "date|null", "end_date": "date|null",
  "days": [
    {
      "day_number": 1, "name": "Day 1",
      "exercises": [
        { "exercise_id":"uuid", "sets":3, "reps":10, "target_weight_kg":20.0|null, "rest_seconds":60|null, "notes":null, "order_index":0 }
      ]
    }
  ]
}
```
- 201 → `WorkoutProgramRead` (full nested read-back, `days[].exercises[]` each including the full
  embedded `ExerciseRead`).

### `GET /workouts/programs/{program_id}`
Requires auth. Ownership: TRAINER only their own-created programs, MEMBER only their own, ADMIN any (else `404`).
- 200 → `WorkoutProgramRead`

### `GET /workouts/programs/me`
MEMBER only. 200 → `WorkoutProgramSummary[]` (same as `WorkoutProgramRead` minus the nested `days`).

### `GET /workouts/members/{member_id}/programs`
TRAINER or ADMIN, ownership-checked via the same assigned-member rule as `GET /members/{id}`.
- 200 → `WorkoutProgramSummary[]`

### `POST /workouts/sessions`
MEMBER only. Schedules a session from one of their own program's days.
- Body: `{ "workout_day_id": uuid, "scheduled_date": date }`
- 201 → `WorkoutSessionRead`
- Errors: `404` (day not found or not the caller's)

### `GET /workouts/sessions/{session_id}`
MEMBER only, own sessions.
- 200 → `WorkoutSessionRead`:
```json
{
  "id","created_at","updated_at","program_id","member_id","workout_day_id",
  "scheduled_date":"date","completed_at":"datetime|null","status":"WorkoutSessionStatus","notes":"string|null",
  "set_logs": [ { "id","workout_exercise_id","set_number":int,"reps_done":"int|null","weight_used_kg":"number|null","completed":bool } ]
}
```

### `POST /workouts/sessions/{session_id}/complete`
MEMBER only, own session, must not already be completed.
- Body: `{ "set_logs": [ { "workout_exercise_id":uuid, "set_number":int, "reps_done":int|null, "weight_used_kg":number|null, "completed":bool } ], "notes": string|null }`
  — every `workout_exercise_id` must belong to this session's workout day, else `400`.
- 200 → `WorkoutSessionRead` (now `status="COMPLETED"`)

---

## 8. Progress — `/api/v1/progress/*`

All four sub-resources (measurements, photos, records, achievements) share the same access
pattern: **MEMBER** operates on their own data implicitly (no `member_id` needed — and if a MEMBER
passes one anyway, it's ignored and their own id is used regardless); **TRAINER/ADMIN** must pass
`member_id` as a query param and are ownership-checked (trainer → assigned members only).

### `GET/POST /progress/measurements`
- Query (GET) / query (POST, in addition to body): `member_id` (required for staff, ignored for members)
- POST body (`BodyMeasurementCreate`): `{ "recorded_at":datetime, "weight_kg"?, "body_fat_pct"?, "chest_cm"?, "waist_cm"?, "hips_cm"?, "arms_cm"?, "thighs_cm"?, "notes"? }` (all measurement fields optional/nullable)
- 200/201 → `BodyMeasurementRead[]` / `BodyMeasurementRead` (includes `recorded_by: uuid|null`)

### `GET /progress/photos` / `POST /progress/photos`
- `POST` is **MEMBER only** (no trainer-upload path), multipart field `file`.
- 201 → `ProgressPhotoRead`: `{ "id","member_id","photo_url","taken_at":datetime,"notes":null }`

### `GET/POST /progress/records`
- POST body (`PersonalRecordCreate`): `{ "exercise_id":uuid, "value":number, "unit":string, "achieved_at":date }`
- 201 → `PersonalRecordRead`

### `GET /progress/achievements`
- 200 → `MemberAchievementRead[]`: `{ "id","member_id","achievement_id","achieved_at":datetime, "achievement": { "id","name","description","icon" } }`
  (achievements themselves are admin-managed data with no CRUD endpoint exposed in this API version.)

---

## 9. Classes — `/api/v1/classes/*`

### `GET /classes`
Requires auth. Query: `upcoming_only` (default `true`).
- 200 → `GymClassRead[]`:
```json
{
  "id","created_at","updated_at","name","description","trainer_id",
  "trainer": { "...TrainerProfileRead..." },
  "capacity":int, "location":"string|null", "start_time":"datetime", "end_time":"datetime",
  "is_active":bool, "booked_count":int, "available_spots":int
}
```

### `POST /classes` / `PATCH /classes/{class_id}` (admin only)
- Create body: `{ "name","description"?,"trainer_id":uuid,"capacity":int(1–500),"location"?,"start_time":datetime,"end_time":datetime }`

### `POST /classes/{class_id}/book`
MEMBER only. **Concurrency-safe** — capacity is enforced with a DB row lock; under a simultaneous
race for the last seat, exactly one request gets `201` and the other gets `409`.
- 201 → `ClassBookingRead`: `{ "id","class_id","member_id","status":"ClassBookingStatus","booked_at":datetime,"cancelled_at":"datetime|null" }`
- Errors: `409 conflict` (already booked, or class full), `400 bad_request` (class already started), `404` (inactive/missing class)

### `POST /classes/bookings/{booking_id}/cancel`
MEMBER only, own booking, must currently be `BOOKED`.
- 200 → `ClassBookingRead` (now `CANCELLED`)

### `GET /classes/bookings/me`
MEMBER only. 200 → `ClassBookingRead[]`

---

## 10. Chat — REST + WebSocket

### REST — `/api/v1/conversations/*`

**`GET /conversations`** — requires auth. 200 → `ConversationRead[]`:
```json
{ "id","created_at","last_message_at":"datetime|null", "participants":[{ "user_id","last_read_at":"datetime|null" }] }
```

**`POST /conversations`** — requires auth. Starts (or reuses, if one already exists between the
same two users) a 1:1 conversation.
- Body: `{ "other_user_id": uuid }`
- 201 → `ConversationRead`

**`GET /conversations/{conversation_id}/messages`** — requires auth, must be a participant (else
`404`). Cursor-paginated by timestamp (not page-number):
- Query: `before` (datetime, optional — fetch messages older than this), `limit` (1–200, default 50)
- 200 → `MessageRead[]` **in chronological order** (oldest→newest within the page). To load
  history, pass `before` = the `created_at` of the oldest message currently held; there's no
  `total`/`pages` here.

**`POST /conversations/{conversation_id}/messages`** — requires auth, must be a participant.
Rate-limited (30/min per IP). Also broadcasts to the conversation's WebSocket subscribers.
- Body: `{ "content": string(1–4000) }`
- 201 → `MessageRead`: `{ "id","conversation_id","sender_id","content","created_at":datetime }`

**`POST /conversations/{conversation_id}/read`** — requires auth, participant only. No body.
- 200 → `{ "message": string }`

### WebSocket — `GET /api/v1/ws/chat/{conversation_id}?token=<access_token>`

- **Handshake auth**: `token` query param, same JWT access token as REST. Missing/invalid token, OR
  a valid token for a user who isn't a participant in `{conversation_id}` — **both cases reject
  the upgrade itself** (confirmed live: HTTP 403 at handshake, never a connected-then-closed
  socket). The Dart `web_socket_channel` package will surface this as a connection error/exception
  on `.connect()`, not as a message or close event — handle it there, not in your message stream.
- **Sending**: send a text frame containing JSON `{ "content": "string" }` (≤4000 chars; empty or
  oversized frames are silently dropped, not errored).
- **Receiving**: every message sent by *any* participant — whether via this WebSocket or the REST
  `POST .../messages` endpoint — is pushed to all connected sockets for that conversation as a
  JSON text frame shaped exactly like `MessageRead` (see above). Messages persist to the DB
  regardless of delivery.
- **Abuse protection**: 30 messages/minute per user (not per-connection); exceeding it gets you a
  `{"error":"rate_limited"}` text frame back instead of the message being processed (the socket
  stays open).
- **Reconnection**: stateless — reconnect any time with a fresh/still-valid access token; on
  reconnect, catch up on history via the REST `GET .../messages?before=...` endpoint, then resume
  live updates over the socket. When your access token expires, reconnect the socket with a
  refreshed token (the socket itself doesn't auto-refresh).

---

## 11. Notifications — `/api/v1/notifications/*`

### `GET /notifications`
Requires auth. **Not paginated** (returns the full list) — 200 → `NotificationRead[]`:
```json
{ "id","type":"NotificationType","title","body","data":"object|null","read_at":"datetime|null","created_at":"datetime" }
```

### `POST /notifications/{notification_id}/read`
Requires auth, own notification only (else `404`). No body. 200 → `NotificationRead`.

### `POST /notifications/devices`
Requires auth. Registers a push token (idempotent — same token twice is a no-op, not an error).
- Body: `{ "token": string, "platform": "ANDROID"|"IOS"|"WEB" }`
- 201 → `{ "id": uuid }`

*(⚠ Push delivery is currently a no-op even when `PUSH_PROVIDER=fcm` is set — the FCM integration
point in `app/services/push_provider.py` is a stub that only logs, it doesn't call Firebase yet.
Registering a token via this endpoint stores it and returns 201, but no real device notification
will ever arrive. Build the in-app notification list (`GET /notifications`) as the source of truth
for now; treat push as a future enhancement, not something to rely on for v1.)*

---

## 12. Water — `/api/v1/water/*`  (MEMBER only, all endpoints)

- **`GET /water/goal`** → `{ "member_id","daily_target_ml":int }` (auto-created with default 2000 on first access)
- **`PUT /water/goal`** — body `{ "daily_target_ml": int(1–10000) }` → same shape
- **`POST /water/entries`** — body `{ "amount_ml": int(1–5000), "logged_at": datetime|null }` (omit `logged_at` to use server "now") → `WaterEntryRead`: `{ "id","member_id","amount_ml","logged_at" }`
- **`GET /water/days/{day}`** — path param `day` is a `date` (`YYYY-MM-DD`) → `WaterDaySummary`: `{ "day","total_ml":int,"goal_ml":int,"entries":[WaterEntryRead] }`

## 13. Nutrition — `/api/v1/nutrition/*`  (MEMBER only, all endpoints)

- **`GET/PUT /nutrition/goal`** — `PUT` body: `{ "daily_calories"?, "protein_g"?, "carbs_g"?, "fat_g"? }` (all optional numbers) → `NutritionGoalRead`
- **`POST /nutrition/meals`** — body: `{ "name":string, "meal_type":"BREAKFAST"|"LUNCH"|"DINNER"|"SNACK", "calories"?,"protein_g"?,"carbs_g"?,"fat_g"?, "logged_at":datetime|null }` → `MealEntryRead`
- **`GET /nutrition/days/{day}`** — → `NutritionDaySummary`: `{ "day","total_calories","total_protein_g","total_carbs_g","total_fat_g","entries":[MealEntryRead] }`

---

## 14. Store — `/api/v1/store/*`

### Categories
- **`GET /store/categories`** — auth required, query `active_only` (default true) → `ProductCategoryRead[]`
- **`POST`/`PATCH .../{category_id}`** — admin only

### Products
- **`GET /store/products`** — auth required. Query: `page`,`page_size`,`category_id`,`search`,`active_only`
  → `Page<ProductRead>`:
```json
{
  "id","created_at","updated_at","category_id","name","description",
  "price":"string","sku","stock_quantity":int,"is_active":bool,
  "images":[{ "id","url","order_index":int }],
  "effective_price":"string|null"
}
```
  `effective_price` is the price **after** any currently-active, applicable promotion
  (server-computed); it equals `price` when no promotion applies. The field is typed nullable in
  the schema but every endpoint that returns a product always populates it — treat it as
  effectively non-null in practice. **Show `effective_price` to the user as "what they'll pay";
  `price` is the undiscounted list price.**
- **`GET /store/products/{product_id}`** — public shape, same as above, single object.
- **`POST /store/products`** / **`PATCH /store/products/{product_id}`** — admin only.
  Create body: `{ "category_id":uuid,"name":string,"description"?,"price":number|string,"sku":string,"stock_quantity":int≥0 }`.
  **Update body never includes `stock_quantity`** — stock can only change via the dedicated
  endpoint below (this is intentional: every stock change is audited).
- **`POST /store/products/{product_id}/stock`** (admin only) — `{ "delta": int (+/-), "reason": string }` → updated `ProductRead`. Stock can never go negative (enforced with a row lock; a concurrent over-decrement request gets `409`).
- **`POST /store/products/{product_id}/images`** (admin only) — multipart `file` → `ProductRead` with the image appended.

### Cart (MEMBER only)
- **`GET /store/cart`** → `CartRead`: `{ "id","items":[{ "id","product_id","product":ProductRead,"quantity":int,"unit_price":"string","subtotal":"string" }],"subtotal":"string","discount_total":"string","total":"string" }`
  — **all pricing here is server-computed from current product price + active promotions**; the
  client never sends or influences these numbers.
- **`POST /store/cart/items`** — `{ "product_id":uuid,"quantity":int(1–999) }` → `CartRead` (adds, or increments an existing line for the same product)
- **`PATCH /store/cart/items/{item_id}`** — `{ "quantity":int(1–999) }` → `CartRead`
- **`DELETE /store/cart/items/{item_id}`** → `CartRead`

### Checkout (MEMBER only) — cash on delivery, no payment gateway
- **`POST /store/checkout`** — `{ "delivery_address":string,"phone":string,"notes":string|null }`
  (client sends **only** delivery details — never prices) → 201 `OrderRead` (status `PENDING`,
  payment_status `PENDING`). Stock is decremented atomically; **concurrent checkouts racing for
  the last unit of stock**: exactly one gets `201`, the other `409 conflict`.
- Errors: `400 bad_request` (empty cart or a product no longer active), `409 conflict` (insufficient stock)

### Orders
- **`GET /store/orders/me`** (MEMBER) → `OrderRead[]` (not paginated)
- **`GET /store/orders/{order_id}`** (owner MEMBER or ADMIN) → `OrderRead`:
```json
{
  "id","created_at","updated_at","member_id","status":"OrderStatus","payment_status":"PaymentStatus",
  "subtotal":"string","discount_total":"string","total":"string","delivery_address","phone","notes":"string|null",
  "items":[{ "id","product_id","product_name_snapshot","unit_price":"string","quantity":int,"subtotal":"string" }]
}
```
  `product_name_snapshot` is the product's name **at time of order** (won't change if the product
  is later renamed — use this for display, not a live product lookup).
- **`GET /store/orders`** (admin only, paginated) — query: `page`,`page_size`,`status_filter` (OrderStatus) → `Page<OrderRead>`
- **`POST /store/orders/{order_id}/status`** (admin only) — `{ "status": OrderStatus }`. Valid
  transitions only (client cannot skip states): `PENDING→CONFIRMED|CANCELLED`,
  `CONFIRMED→PREPARING|CANCELLED`, `PREPARING→OUT_FOR_DELIVERY`, `OUT_FOR_DELIVERY→DELIVERED`.
  Cancelling restocks inventory automatically. Invalid transition → `400 bad_request`.
- **`POST /store/orders/{order_id}/confirm-payment`** (admin only) — no body; only valid once the
  order is `OUT_FOR_DELIVERY` or `DELIVERED`. → `OrderRead` (`payment_status="PAID"`).

**The client never sets `status` or `payment_status` directly on create/update anywhere in this API.**

---

## 15. Promotions — `/api/v1/promotions/*`

### `GET /promotions/active`
Requires auth (any role). Currently-active, date-in-range promotions only.
- 200 → `PromotionRead[]`:
```json
{
  "id","created_at","updated_at","name","description",
  "discount_type":"PERCENTAGE"|"FIXED","discount_value":"string",
  "start_date":"datetime","end_date":"datetime","is_active":bool,
  "stack_priority":int,"combinable":bool,
  "product_ids":["uuid"],"category_ids":["uuid"],"plan_ids":["uuid"]
}
```
Discounts are already reflected in `Product.effective_price` and cart/order totals — the Flutter
app does **not** need to re-implement stacking logic; use this endpoint purely to show promo
banners/badges, referencing `product_ids`/`category_ids` to know which items a badge applies to.

### `GET /promotions` (admin only) / `POST /promotions` (admin only) / `PATCH /promotions/{id}` (admin only)
- Create body: `{ "name","description"?,"discount_type":DiscountType,"discount_value":number|string,"start_date":datetime,"end_date":datetime,"stack_priority"?:int=100,"combinable"?:bool=false,"product_ids"?:[uuid],"category_ids"?:[uuid],"plan_ids"?:[uuid] }`
  (`end_date` must be after `start_date`; a `PERCENTAGE` discount_value must be ≤100 — both validated server-side, 422 otherwise)

---

## 16. Dashboard — `/api/v1/dashboard/*`  (MEMBER only)

### `GET /dashboard/me`
```json
{
  "membership": { "has_membership":bool,"status":"MembershipStatus|null","plan_name":"string|null","expiry_date":"date|null","days_remaining":"int|null" },
  "todays_workout": WorkoutSessionRead | null,
  "upcoming_classes": [GymClassRead],
  "active_promotions": [PromotionRead],
  "progress": { "latest_weight_kg":"number|null","weight_change_kg":"number|null","total_workouts_completed":int,"personal_records_count":int }
}
```

### `GET /dashboard/card`
**Informational only — there is no check-in/QR/NFC functionality anywhere in this API.**
```json
{ "member_id","member_code","full_name","photo_url":"string|null","membership_status":"MembershipStatus|null","membership_expiry":"date|null" }
```

---

## 17. Gym info (public-ish reference data)

All under no common prefix (mounted directly at `/api/v1`):
- `GET /gym/settings` (public) / `PATCH /gym/settings` (admin) → `{ "name","description","phone","email","address","logo_url" }` (all nullable except `name`)
- `GET /gym/opening-hours` (public) / `PUT /gym/opening-hours` (admin, upserts one day) → `OpeningHoursRead[]` / single: `{ "day_of_week":0-6 (0=Monday),"open_time":"HH:MM:SS|null","close_time":"HH:MM:SS|null","is_closed":bool }`
- `GET /gym/rules` (public) / `POST` (admin) / `DELETE /gym/rules/{id}` (admin) → `{ "id","title","description","order_index":int }`
- `GET /faqs` (public, query `active_only`) / `POST`/`PATCH`/`DELETE` (admin) → `{ "id","question","answer","order_index":int,"is_active":bool }`
- `POST /contact` (**public, no auth**) → submits `{ "name","email","phone"?,"subject","message" }`, returns `ContactRequestRead`. `GET /contact` / `PATCH /contact/{id}/status` — admin only.
- `POST /feedback` (MEMBER only) — `{ "rating":1-5,"comment"?:string }` → `FeedbackRead`. `GET /feedback` — admin only, not paginated.

---

## 18. Admin — `/api/v1/admin/*`

- **`POST /admin/staff`** (admin only) — creates a TRAINER or ADMIN account (the *only* way to
  create one besides the offline `scripts/create_admin.py` bootstrap). Body: `{ "email","password","full_name","role":"TRAINER"|"ADMIN" }` (sending `"role":"MEMBER"` here is rejected with `400`, use `/auth/register` instead). → `{ "id","email","role" }`
- **`GET /admin/dashboard`** (admin only) → `AdminDashboardResponse`: `{ "total_members","active_memberships","expiring_memberships_7d","pending_payments","active_classes","bookings_today","pending_orders","revenue_month":"string","active_promotions","total_trainers" }` (all counts are `int` except `revenue_month`, a decimal-as-string).
- **`GET /admin/audit-logs`** (admin only, paginated) — query `page`,`page_size`(≤200),`entity_type`,`action` →
  **⚠ known gap**: this endpoint has no declared OpenAPI response schema (returns `{}` in the
  spec), so it won't appear correctly in any Dart client generated from `/openapi.json`. The actual
  runtime shape (confirmed from source and live testing) is:
```json
{
  "items": [ { "id","actor_id":"uuid|null","action":"string","entity_type":"string","entity_id":"string|null","before":"object|null","after":"object|null","created_at":"ISO datetime string" } ],
  "total":int,"page":int,"page_size":int,"pages":int
}
```
  This is an admin/back-office endpoint, low priority for the mobile app; flagged here in case a
  future admin-web-panel consumes it.

---

## 19. Health (no auth, no `/api/v1` prefix)

- `GET /health` → `{ "status": "ok" }`
- `GET /health/live` → `{ "status": "alive" }` (lightweight, no dependency checks)
- `GET /health/ready` → `200 { "status":"ready","checks":{"database":"ok","redis":"ok"} }` or
  **`503`** with `"status":"not_ready"` and whichever check(s) failed set to `"error"` — useful for
  a splash-screen "server unavailable" state, not something the app needs to call routinely.

---

## 20. Master enum reference

| Enum | Values |
|---|---|
| `UserRole` | `ADMIN`, `TRAINER`, `MEMBER` |
| `FitnessLevel` | `BEGINNER`, `INTERMEDIATE`, `ADVANCED` |
| `DifficultyLevel` | `BEGINNER`, `INTERMEDIATE`, `ADVANCED` |
| `MembershipStatus` | `PENDING`, `ACTIVE`, `EXPIRED`, `CANCELLED`, `SUSPENDED` |
| `PaymentStatus` | `PENDING`, `PAID`, `CANCELLED`, `REFUNDED` |
| `WorkoutSessionStatus` | `SCHEDULED`, `COMPLETED`, `SKIPPED` |
| `ClassBookingStatus` | `BOOKED`, `CANCELLED`, `ATTENDED` |
| `NotificationType` | `MEMBERSHIP`, `WORKOUT_ASSIGNED`, `CLASS_REMINDER`, `NEW_MESSAGE`, `PROMOTION`, `ORDER_UPDATE`, `SYSTEM` |
| `DevicePlatform` | `ANDROID`, `IOS`, `WEB` |
| `OrderStatus` | `PENDING`, `CONFIRMED`, `PREPARING`, `OUT_FOR_DELIVERY`, `DELIVERED`, `CANCELLED` |
| `DiscountType` | `PERCENTAGE`, `FIXED` |
| `ContactStatus` | `OPEN`, `IN_PROGRESS`, `RESOLVED` |
| `MealType` | `BREAKFAST`, `LUNCH`, `DINNER`, `SNACK` |

Recommendation for Dart: generate one `enum` per row with a `fromJson`/`toJson` that round-trips
the exact uppercase string (e.g. via `json_serializable`'s `@JsonEnum`) — don't rely on positional/
index-based enum mapping, since these are transmitted as strings, not integers.

---

## Known Flutter-compatibility findings (see final report for full context)

1. **No OpenAPI `securitySchemes`/`security` metadata is declared** — the API works correctly with
   a manual `Authorization: Bearer <token>` header (documented per-endpoint above via "requires
   auth"), but if you generate a Dart client from `/openapi.json` with a tool like
   `openapi-generator`, it will **not** know to attach the header automatically; you'll need to
   configure the generated client's default headers/interceptor by hand. This is a documentation
   gap, not a functional one.
2. **`GET /admin/audit-logs` has no declared response schema** (see §18) — hand-documented above
   from source; low priority (admin/back-office only).
3. **Push notifications don't actually deliver yet** (see §11) — `POST /notifications/devices`
   works and stores the token, but the FCM send path is currently a stub. Build against
   `GET /notifications` as the real source of truth; don't build UI that assumes a tray
   notification will ever arrive.
4. **Password reset now sends a real email** (via Brevo) once `EMAIL_PROVIDER=brevo` is configured
   in production — `debug_reset_token` is dev/test-only (`DEBUG=true`), always `null` otherwise.
5. All other endpoints have complete, accurate OpenAPI schemas matching this document exactly
   (this document was generated directly from a live `/openapi.json` capture plus source
   cross-check, not from memory).
