"""Автоматическое наполнение БД тестовыми данными: python seed.py"""
import random
from datetime import date, datetime, timedelta

import db

PROJECTS = {
    "Курсовая по программированию": ["Выбрать тему", "Написать ТЗ", "Реализовать модуль данных", "Оформить пояснительную записку"],
    "Лабораторные по физике": ["Лаба 1: измерения", "Лаба 2: оптика", "Подготовить отчёты"],
    "Английский язык": ["Выучить лексику юнита 5", "Эссе", "Подготовить презентацию"],
    "Учебная практика": ["Выбрать стек", "Модуль задач", "Таймер", "Отчёты и Гант", "Документация"],
}


def seed():
    db.init_db()
    today = date.today()
    with db.connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]:
            print("БД уже заполнена — пропускаю.")
            return
        random.seed(42)
        for name, titles in PROJECTS.items():
            pid = conn.execute("INSERT INTO projects (name, description) VALUES (?, ?)",
                               (name, f"Тестовый проект «{name}»")).lastrowid
            for title in titles:
                start = today + timedelta(days=random.randint(-20, 10))
                due = start + timedelta(days=random.randint(3, 21))
                status = random.choice(["todo", "in_progress", "done"])
                tid = conn.execute(
                    "INSERT INTO tasks (project_id, title, priority, status, start_date, due_date, notes) VALUES (?,?,?,?,?,?,?)",
                    (pid, title, random.randint(1, 3), status, start.isoformat(), due.isoformat(), "")).lastrowid
                for _ in range(random.randint(0, 4)):
                    day = today - timedelta(days=random.randint(0, 27))
                    started = datetime.combine(day, datetime.min.time()).replace(hour=random.randint(8, 21))
                    conn.execute("INSERT INTO time_entries (task_id, started_at, duration_sec, is_manual) VALUES (?,?,?,0)",
                                 (tid, started.strftime("%Y-%m-%d %H:%M:%S"), random.randint(15, 150) * 60))
    print("Тестовые данные добавлены.")


if __name__ == "__main__":
    seed()
