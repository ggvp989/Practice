"""Работа с SQLite: подключение и схема БД."""
import os
import sqlite3

DB_PATH = os.environ.get("PLANNER_DB", os.path.join(os.path.dirname(__file__), "planner.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    priority    INTEGER NOT NULL DEFAULT 2,          -- 1 низкий, 2 средний, 3 высокий
    status      TEXT NOT NULL DEFAULT 'todo',        -- todo | in_progress | done
    start_date  TEXT,                                -- YYYY-MM-DD
    due_date    TEXT,                                -- YYYY-MM-DD
    notes       TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS time_entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id      INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    started_at   TEXT NOT NULL,                      -- YYYY-MM-DD HH:MM:SS
    duration_sec INTEGER NOT NULL,
    is_manual    INTEGER NOT NULL DEFAULT 0
);
"""


def connect(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path=None):
    with connect(path) as conn:
        conn.executescript(SCHEMA)
