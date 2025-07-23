# Mortgage Deed Management API

A FastAPI-based REST API for managing digital mortgage deeds.

## Prerequisites

- Python 3.8+
- PostgreSQL (via Supabase)
- Mailgun account for email notifications

## Setup

1. Clone the repository:

```bash
git clone https://github.com/machan1119/kolibri-investment-backend.git
cd kolibri-investment-backend
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy the environment template and update the variables:

```bash
cp .env.example .env
```

## Development

Start the development server:

```bash
uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`

API Documentation will be available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
src/
├── api/
│   ├── main.py          # FastAPI application instance
│   ├── config.py        # Configuration management
│   ├── routers/         # API route handlers
│   ├── models/          # Pydantic models
│   ├── schemas/         # Database schemas
│   ├── services/        # Business logic
│   ├── utils/           # Utility functions
│   └── middleware/      # Custom middleware
└── tests/               # Test files
```

## Testing

Run tests with pytest:

```bash
pytest
```

## API Documentation

The API includes the following main endpoints:

- `/api/v1/deeds`: Mortgage deed CRUD operations
- `/api/v1/cooperatives`: Housing cooperative operations
- `/api/v1/stats`: Statistics and analytics

For detailed API documentation, visit the Swagger UI or ReDoc pages when the server is running.
