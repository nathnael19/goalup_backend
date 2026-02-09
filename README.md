# Backend Setup Walkthrough

## Prerequisites

- Python 3.9+
- PostgreSQL

## Setup Instructions

1.  **Navigate to the backend directory:**

    ```bash
    cd backend
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\\Scripts\\activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    - Rename `.env` (if it exists as a template) or ensure it has the correct values.
    - Update `DATABASE_URL` in `.env` to point to your PostgreSQL database.

5.  **Initialize Database:**
    - The application will attempt to create tables on startup.
    - To use migrations with Alembic:
      ```bash
      alembic revision --autogenerate -m "Initial migration"
      alembic upgrade head
      ```

6.  **Run the Server:**

    ```bash
    uvicorn app.main:app --reload
    ```

7.  **Access Documentation:**
    - Open `http://127.0.0.1:8000/docs` to view the Swagger UI.
