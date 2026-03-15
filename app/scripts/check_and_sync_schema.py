"""
Compare SQLModel tables/columns with Neon DB and sync both ways:
- Models -> DB: create missing tables, add missing columns.
- DB -> Models: report tables/columns in DB not in models; optionally add them to model files.

Run from project root with venv active and DATABASE_URL set:
  python -m app.scripts.check_and_sync_schema [--apply] [--update-models]
  --apply: run CREATE TABLE and ALTER TABLE for missing items in DB.
  --update-models: add columns/tables that exist in DB but not in models into app/models (use after review).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.types import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlmodel import SQLModel

# Import all table models so they are registered with SQLModel.metadata
from app.core.database import engine
from app.models.audit_log import AuditLog
from app.models.card import Card
from app.models.competition import Competition
from app.models.goal import Goal
from app.models.lineup import Lineup
from app.models.match import Match
from app.models.news import News
from app.models.notification import Notification
from app.models.player import Player
from app.models.refresh_token import RefreshToken
from app.models.standing import Standing
from app.models.substitution import Substitution
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import User

# Ensure all are registered (no-op but makes dependency clear)
_ = (
    User,
    Team,
    Tournament,
    Competition,
    Match,
    Standing,
    Player,
    News,
    AuditLog,
    RefreshToken,
    Notification,
    Lineup,
    Goal,
    Card,
    Substitution,
)

# Table name (in DB) -> (models file path relative to backend root, class to add column to)
TABLE_TO_MODEL: dict[str, tuple[str, str]] = {
    "users": ("app/models/user.py", "User"),
    "team": ("app/models/team.py", "TeamBase"),
    "tournament": ("app/models/tournament.py", "TournamentBase"),
    "competition": ("app/models/competition.py", "CompetitionBase"),
    "match": ("app/models/match.py", "MatchBase"),
    "standing": ("app/models/standing.py", "StandingBase"),
    "player": ("app/models/player.py", "PlayerBase"),
    "news": ("app/models/news.py", "NewsBase"),
    "audit_logs": ("app/models/audit_log.py", "AuditLogBase"),
    "refresh_tokens": ("app/models/refresh_token.py", "RefreshToken"),
    "notifications": ("app/models/notification.py", "NotificationBase"),
    "lineup": ("app/models/lineup.py", "LineupBase"),
    "goal": ("app/models/goal.py", "GoalBase"),
    "card": ("app/models/card.py", "CardBase"),
    "substitution": ("app/models/substitution.py", "SubstitutionBase"),
}


def _db_type_to_field(defn: dict) -> str:
    """Infer a SQLModel Field() line from SQLAlchemy column definition (from inspector)."""
    col_type = defn.get("type") or defn.get("type_")
    if col_type is None:
        return "Any = Field()  # unknown type"
    type_str = str(col_type).upper()
    name = defn["name"]
    nullable = defn.get("nullable", True)
    # Map common PostgreSQL / SQLAlchemy types
    if isinstance(col_type, (Integer, INTEGER, BigInteger)):
        return f"{name}: int | None = Field(default=None)" if nullable else f"{name}: int = Field()"
    if isinstance(col_type, Boolean) or "BOOL" in type_str:
        return f"{name}: bool | None = Field(default=None)" if nullable else f"{name}: bool = Field()"
    if isinstance(col_type, DateTime) or "TIMESTAMP" in type_str or "DATE" in type_str:
        return f"{name}: datetime | None = Field(default=None)" if nullable else f"{name}: datetime = Field()"
    if isinstance(col_type, (String, VARCHAR)):
        max_len = getattr(col_type, "length", None) or 255
        return f'{name}: str | None = Field(default=None, max_length={max_len})' if nullable else f'{name}: str = Field(max_length={max_len})'
    if isinstance(col_type, Text) or "TEXT" in type_str:
        return f"{name}: str | None = Field(default=None)" if nullable else f"{name}: str = Field()"
    if "UUID" in type_str:
        return f"{name}: uuid.UUID | None = Field(default=None)" if nullable else f"{name}: uuid.UUID = Field()"
    if "JSON" in type_str or "JSONB" in type_str:
        return f"{name}: dict | list | None = Field(default=None)" if nullable else f"{name}: dict | list = Field()"
    if "FLOAT" in type_str or "DOUBLE" in type_str or "REAL" in type_str:
        return f"{name}: float | None = Field(default=None)" if nullable else f"{name}: float = Field()"
    return f"{name}: Any = Field()  # {type_str}"


def _get_expected_tables():
    """Tables defined in SQLModel (all registered table=True models)."""
    return set(SQLModel.metadata.tables.keys())


def _get_expected_columns(table_name: str) -> dict[str, str]:
    """Column name -> compiled SQL type for a given table in metadata."""
    if table_name not in SQLModel.metadata.tables:
        return {}
    table = SQLModel.metadata.tables[table_name]
    dialect = engine.dialect
    return {
        c.name: c.type.compile(dialect=dialect)
        for c in table.c
    }


def run_compare_and_sync(apply: bool = False, update_models: bool = False) -> bool:
    """Compare schema and optionally apply changes. Returns True if no errors."""
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())

    expected_tables = _get_expected_tables()
    missing_tables = expected_tables - db_tables
    extra_tables = db_tables - expected_tables

    # ---- 1) Report / create missing tables ----
    if missing_tables:
        print("Tables in MODELS but not in DB (will be created):")
        for t in sorted(missing_tables):
            print(f"  - {t}")
        if apply and missing_tables:
            tables_to_create = [
                SQLModel.metadata.tables[name]
                for name in sorted(missing_tables)
                if name in SQLModel.metadata.tables
            ]
            if tables_to_create:
                SQLModel.metadata.create_all(engine, tables=tables_to_create)
                print("Created missing tables.")
    else:
        print("All model tables exist in DB.")

    # ---- 2) Report / add missing columns ----
    missing_cols_by_table: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for table_name in expected_tables:
        if table_name not in db_tables:
            continue
        expected_cols = _get_expected_columns(table_name)
        db_cols = {c["name"] for c in inspector.get_columns(table_name)}
        for col_name, col_type in expected_cols.items():
            if col_name not in db_cols:
                missing_cols_by_table[table_name].append((col_name, col_type))

    if missing_cols_by_table:
        print("\nColumns in MODELS but not in DB (will be added):")
        alter_statements = []
        for t in sorted(missing_cols_by_table.keys()):
            for col_name, col_type in missing_cols_by_table[t]:
                print(f"  - {t}.{col_name} ({col_type})")
                # PostgreSQL: quote identifiers (lowercase table names from metadata)
                alter_statements.append(
                    f'ALTER TABLE "{t}" ADD COLUMN "{col_name}" {col_type};'
                )
        if apply and alter_statements:
            with engine.begin() as conn:
                for stmt in alter_statements:
                    conn.execute(text(stmt))
            print("Applied ALTER TABLE for missing columns.")
        elif alter_statements:
            # Write SQL file for manual review/run
            out_path = "sync_schema_migration.sql"
            with open(out_path, "w") as f:
                f.write("-- Generated migration: add columns in models but missing in DB\n")
                for stmt in alter_statements:
                    f.write(stmt + "\n")
            print(f"Wrote {len(alter_statements)} ALTER(s) to {out_path} for manual run.")
    else:
        print("\nAll model columns exist in DB.")

    # ---- 3) Report tables in DB not in models ----
    if extra_tables:
        print("\nTables in DB but not in MODELS (consider adding to app/models or ignoring):")
        for t in sorted(extra_tables):
            print(f"  - {t}")

    # ---- 4) Report columns in DB not in models; optionally add to model files ----
    extra_cols_by_table: dict[str, list[dict]] = defaultdict(list)
    for table_name in expected_tables:
        if table_name not in db_tables:
            continue
        expected_cols = set(_get_expected_columns(table_name).keys())
        for c in inspector.get_columns(table_name):
            if c["name"] not in expected_cols:
                extra_cols_by_table[table_name].append(c)

    if extra_cols_by_table:
        print("\nColumns in DB but not in MODELS (consider adding to model classes):")
        for t in sorted(extra_cols_by_table.keys()):
            for c in sorted(extra_cols_by_table[t], key=lambda x: x["name"]):
                print(f"  - {t}.{c['name']}")
        if update_models and TABLE_TO_MODEL:
            _add_extra_columns_to_models(extra_cols_by_table)
    elif update_models:
        print("\nNo extra columns in DB to add to models.")

    return True


def _add_extra_columns_to_models(extra_cols_by_table: dict[str, list[dict]]) -> None:
    """Insert missing column definitions into the right model class in app/models."""
    backend_root = Path(__file__).resolve().parent.parent.parent
    for table_name in sorted(extra_cols_by_table.keys()):
        if table_name not in TABLE_TO_MODEL:
            print(f"  [skip] No model mapping for table {table_name}")
            continue
        rel_path, class_name = TABLE_TO_MODEL[table_name]
        filepath = backend_root / rel_path
        if not filepath.exists():
            print(f"  [skip] File not found: {filepath}")
            continue
        lines = filepath.read_text().splitlines()
        # Find class ClassName: and the last line of its body (next class or end of class at same indent)
        class_indent = None
        insert_line_idx = None
        for i, line in enumerate(lines):
            if re.match(rf"^class {re.escape(class_name)}\s*[:(]", line):
                class_indent = len(line) - len(line.lstrip())
                insert_line_idx = i + 1
                continue
            if class_indent is not None and insert_line_idx is not None:
                stripped = line.lstrip()
                if not stripped or stripped.startswith("#"):
                    continue
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= class_indent and line.strip():
                    break
                if current_indent > class_indent and (" = Field(" in line or ":" in line and "=" in line):
                    insert_line_idx = i + 1
        if insert_line_idx is None:
            print(f"  [skip] Class {class_name} not found in {filepath}")
            continue
        # Build new field lines (add datetime import if needed)
        new_fields: list[str] = []
        needs_datetime = False
        for c in sorted(extra_cols_by_table[table_name], key=lambda x: x["name"]):
            field_line = _db_type_to_field(c)
            if "datetime" in field_line:
                needs_datetime = True
            new_fields.append(f"    {field_line}")
        file_content = "\n".join(lines)
        if needs_datetime and "from datetime" not in file_content and "import datetime" not in file_content:
            for i, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import "):
                    idx = i + 1
                    while idx < len(lines) and (lines[idx].startswith("from ") or lines[idx].startswith("import ") or not lines[idx].strip()):
                        idx += 1
                    lines.insert(idx, "from datetime import datetime")
                    break
        for field in reversed(new_fields):
            lines.insert(insert_line_idx, field)
        filepath.write_text("\n".join(lines) + "\n")
        print(f"  Updated {filepath.name}: added {len(new_fields)} column(s) to {class_name}.")


def main():
    parser = argparse.ArgumentParser(description="Compare and sync DB schema with SQLModel")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes: create missing tables, add missing columns in DB",
    )
    parser.add_argument(
        "--update-models",
        action="store_true",
        help="Add columns that exist in DB but not in models into app/models",
    )
    args = parser.parse_args()
    try:
        ok = run_compare_and_sync(apply=args.apply, update_models=args.update_models)
        if not args.apply and (ok or True):
            print("\n(Dry run. Use --apply to create missing tables and add missing columns.)")
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
