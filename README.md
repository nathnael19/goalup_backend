# ASTU Football App - Backend

A robust backend for managing football tournaments, teams, players, matches, and standings. Built with FastAPI, SQLModel (SQLAlchemy + Pydantic), and PostgreSQL.

## Features

- **Tournament Management**: Create, view, update, and delete tournaments.
- **Team Management**: Manage teams within tournaments, including automatic standing initialization.
- **Player Management**:
  - Unique jersey numbers per team.
  - Case-insensitive position handling.
  - Full CRUD operations.
- **Match Management**:
  - Track match status (scheduled, live, finished).
  - Update scores and status.
- **Automated Standings**:
  - Grouped by tournament.
  - Enriched with team and tournament details.
  - Manual recalculation endpoint for data integrity.

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **ORM**: [SQLModel](https://sqlmodel.tiangolo.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/latest/)

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL

### Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd Football/backend
   ```

2. **Set up a virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the `backend/` directory:

   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/db_name
   SECRET_KEY=your_secret_key
   ```

5. **Run Migrations**:

   ```bash
   alembic upgrade head
   ```

6. **Start the Development Server**:
   ```bash
   fastapi dev
   ```
   Access the API documentation at `http://127.0.0.1:8000/docs`.

## Project Structure

```text
backend/
├── alembic/            # Database migrations
├── app/
│   ├── api/            # API v1 routes and endpoints
│   ├── core/           # Configuration and database setup
│   ├── models/         # SQLModel database schemas
│   └── main.py         # App entry point
├── .env                # Environment variables (not tracked)
├── alembic.ini         # Alembic configuration
└── requirements.txt    # Project dependencies
```

## API Documentation

The API follows standard RESTful principles. Key endpoints include:

- `/api/v1/tournaments/`
- `/api/v1/teams/`
- `/api/v1/players/`
- `/api/v1/matches/`
- `/api/v1/standings/`

Detailed documentation and interactive testing are available via Swagger UI (`/docs`).
