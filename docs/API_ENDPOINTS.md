# API Endpoints

This document describes the current API exposed by the project.

Base URL:

- Local development: http://localhost:8000/api

## Health

### GET /api/

- Description: Health check endpoint.
- Request body: None.
- Success response: `200 OK`
- Response body:

```json
{
  "message": "Estamos vivos y coleando"
}
```

---

## Authentication

### POST /api/auth/signup

- Description: Registers a new user.
- Request body:

```json
{
  "id": "12345678",
  "email": "user@example.com",
  "password": "secret123",
  "firstname": "Juan",
  "lastname": "Pérez",
  "birthdate": "1990-01-01T00:00:00",
  "gender": "male",
  "address": "Av. Principal 123",
  "phone": "987654321",
  "role": "patient"
}
```

- Success response: `200 OK`
- Response body: User object.

### POST /api/auth/login

- Description: Authenticates a user with email and password.
- Request body:

```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

- Success response: `200 OK`
- Response body: User object.
- Possible errors: `401 Unauthorized` when credentials are invalid.

---

## Chat

### GET /api/chat/sessions/{user_id}

- Description: Retrieves all chat sessions for a user.
- Request body: None.
- Success response: `200 OK`
- Response body: Array of chat session summaries.

### POST /api/chat/sessions

- Description: Creates a new chat session.
- Request body:

```json
{
  "user_id": "12345678",
  "title": "Consulta médica"
}
```

- Success response: `200 OK`
- Response body:

```json
{
  "id": "session-id",
  "user_id": "12345678",
  "title": "Consulta médica",
  "created_at": "2026-06-25T10:00:00",
  "message_count": 0
}
```

### GET /api/chat/sessions/detail/{session_id}

- Description: Retrieves details of a specific chat session.
- Request body: None.
- Success response: `200 OK`
- Response body: Chat session object with message count.
- Possible errors: `404 Not Found` if the session does not exist.

### DELETE /api/chat/sessions/{session_id}

- Description: Deletes a chat session.
- Request body: None.
- Success response: `200 OK`
- Response body:

```json
{
  "deleted": true
}
```

- Possible errors: `404 Not Found` if the session does not exist.

### GET /api/chat/messages/{session_id}

- Description: Retrieves all messages for a chat session.
- Request body: None.
- Success response: `200 OK`
- Response body: Array of messages.

### POST /api/chat/messages

- Description: Sends a user message and returns the AI response.
- Request body:

```json
{
  "session_id": "session-id",
  "user_id": "12345678",
  "content": "¿Qué medicamentos debo tomar?"
}
```

- Success response: `200 OK`
- Response body:

```json
{
  "id": "message-id",
  "session_id": "session-id",
  "role": "ai",
  "content": "Respuesta generada por el modelo",
  "created_at": "2026-06-25T10:00:30"
}
```

- Possible errors: `404 Not Found` if the session is missing, `403 Forbidden` if the user is not authorized for that session.

---

## Users

### GET /api/users/

- Description: Lists all users.
- Request body: None.
- Success response: `200 OK`
- Response body: Array of users.

### GET /api/users/{user_id}

- Description: Retrieves a specific user by ID.
- Request body: None.
- Success response: `200 OK`
- Response body: User object or `null` if not found.

### GET /api/users/email/{email}

- Description: Retrieves a user by email.
- Request body: None.
- Success response: `200 OK`
- Response body: User object or `null` if not found.

### GET /api/users/role/{role}

- Description: Retrieves users by role.
- Request body: None.
- Success response: `200 OK`
- Response body: Array of users.

### PUT /api/users/{user_id}

- Description: Updates a user using a JSON object with the fields to change.
- Request body:

```json
{
  "firstname": "Carlos",
  "address": "Nueva dirección"
}
```

- Success response: `200 OK`
- Response body: Updated user object.

### DELETE /api/users/{user_id}

- Description: Deletes a user.
- Request body: None.
- Success response: `200 OK`
- Response body:

```json
{
  "deleted": true
}
```

---

## Vision / Document Processing

### POST /api/vision/ocr

- Description: Performs OCR on an uploaded image file.
- Request body: `multipart/form-data`
  - `file`: binary image file
  - `mode`: string, either `default` or `custom`
- Success response: `200 OK`
- Response body: OCR output returned by the OCR module (array of detected text regions/results).

### POST /api/vision/detect-type

- Description: Classifies a text sample as a document type.
- Request body:

```json
{
  "text": "Texto del documento a analizar"
}
```

- Success response: `200 OK`
- Response body:

```json
"dni"
```

or

```json
"reporte_medico"
```

### POST /api/vision/format-text

- Description: Formats OCR text into a structured object based on the selected document type.
- Request body:

```json
{
  "ocr_text": "Texto extraído del OCR",
  "document_type": "dni"
}
```

- Success response: `200 OK`
- Response body: Structured object depending on the document type.
  - For `dni`: fields such as `names`, `paternal_lastname`, `maternal_lastname`, `date_of_birth`, `gender`.
  - For `medical_report`: fields such as `report_date`, `condition`, `results`, `medications`.
- Possible errors: `400 Bad Request` for invalid document type, `500 Internal Server Error` if the LLM API key is missing.

### POST /api/vision/save

- Description: Saves a processed document and optionally its structured data into the database.
- Request body:

```json
{
  "user_id": "12345678",
  "document_type": "dni",
  "file_path": "/tmp/document.jpg",
  "ocr_text": "Texto OCR",
  "dni_data": {
    "names": "Juan",
    "paternal_lastname": "Pérez",
    "maternal_lastname": "García",
    "date_of_birth": "1990-01-01",
    "gender": "male"
  }
}
```

- Success response: `200 OK`
- Response body:

```json
{
  "document": {
    "id": "document-id",
    "user_id": "12345678",
    "type": "dni",
    "file_path": "/tmp/document.jpg",
    "ocr_text": "Texto OCR",
    "uploaded_at": "2026-06-25T10:00:00"
  },
  "dni": {
    "id": "dni-id",
    "document_id": "document-id",
    "names": "Juan",
    "paternal_lastname": "Pérez",
    "maternal_lastname": "García",
    "date_of_birth": "1990-01-01",
    "gender": "male"
  }
}
```

- Possible errors: `400 Bad Request` for invalid document type or missing structured data.

---

## Notes

- The API is registered in the main FastAPI app with the prefix `/api`.
- Some endpoints use raw database access and currently do not enforce authentication.
- The vision endpoints depend on the `GROQ_API_KEY` environment variable for structured text extraction.
