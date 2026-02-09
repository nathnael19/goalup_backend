# Backend Setup Walkthrough

## Prerequisites

- Python 3.9+
- PostgreSQL

## Setup Instructions

1.  **Navigate to the backend directory:**

    ```bash
    cd backend
    ```

2.  **Activate virtual environment:**

    ```bash
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    - Ensure `.env` exists and contains:
      ```
      DATABASE_URL=postgresql://user:password@localhost/dbname
      SECRET_KEY=change_this_secret_key
      ```
    - **Note:** `SECRET_KEY` is required for the application to start.

5.  **Initialize Database:**
    - The application will attempt to create tables on startup.
    - To use migrations with Alembic:
      ```bash
      alembic revision --autogenerate -m "Initial migration"
      alembic upgrade head
      ```

6.  **Run the Server:**

    ```bash
    fastapi dev
    # OR
    uvicorn app.main:app --reload
    ```

7.  **Access Documentation:**
    - Open `http://127.0.0.1:8000/docs` to view the Swagger UI.

## Troubleshooting

- If you see `ValidationError` for `Settings`, ensure `SECRET_KEY` is present in `.env` and `config.py` (Fixed in this setup).
