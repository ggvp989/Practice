"""Веб-приложение для планирования учебных задач (Flask + SQLite)."""
from datetime import datetime, date, timedelta

from flask import Flask, jsonify, render_template, request, abort

import db
from schedule_parser import get_schedule

app = Flask(__name__)

STATUSES = ("todo", "in_progress", "done")
PROGRESS = {"todo": 0, "in_progress": 50, "done": 100}


def rows(query, args=()):
    with db.connect() as conn:
        return [dict(r) for r in conn.execute(query, args).fetchall()]


def execute(query, args=()):
    with db.connect() as conn:
        cur = conn.execute(query, args)
        return cur.lastrowid


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "Ожидался JSON-объект")
    return data


@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=e.description), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify(error="Не найдено"), 404


# ---------- страница ----------
@app.get("/")
def index():
    return render_template("index.html")


# ---------- проекты ----------
@app.get("/api/projects")
def list_projects():
    return jsonify(rows("SELECT * FROM projects ORDER BY id"))


@app.post("/api/projects")
def create_project():
    d = body()
    name = (d.get("name") or "").strip()
    if not name:
        abort(400, "Укажите название проекта")
    pid = execute("INSERT INTO projects (name, description) VALUES (?, ?)",
                  (name, d.get("description", "")))
    return jsonify(rows("SELECT * FROM projects WHERE id=?", (pid,))[0]), 201


@app.delete("/api/projects/<int:pid>")
def delete_project(pid):
    execute("DELETE FROM projects WHERE id=?", (pid,))
    return "", 204


# ---------- задачи ----------
def validate_task(d, partial=False):
    out = {}
    if "title" in d or not partial:
        title = (d.get("title") or "").strip()
        if not title:
            abort(400, "Укажите название задачи")
        out["title"] = title
    if "priority" in d or not partial:
        try:
            pr = int(d.get("priority", 2))
        except (TypeError, ValueError):
            abort(400, "Приоритет должен быть числом 1–3")
        if pr not in (1, 2, 3):
            abort(400, "Приоритет: 1, 2 или 3")
        out["priority"] = pr
    if "status" in d or not partial:
        st = d.get("status", "todo")
        if st not in STATUSES:
            abort(400, "Статус: todo, in_progress или done")
        out["status"] = st
    for key in ("start_date", "due_date"):
        if key in d or not partial:
            val = d.get(key) or None
            if val:
                try:
                    date.fromisoformat(val)
                except ValueError:
                    abort(400, f"{key}: формат ГГГГ-ММ-ДД")
            out[key] = val
    if "notes" in d or not partial:
        out["notes"] = d.get("notes", "")
    if out.get("start_date") and out.get("due_date") and out["start_date"] > out["due_date"]:
        abort(400, "Дата начала позже срока")
    return out


@app.get("/api/tasks")
def list_tasks():
    sql = """SELECT t.*, p.name AS project_name,
                    COALESCE((SELECT SUM(duration_sec) FROM time_entries e WHERE e.task_id = t.id), 0) AS spent_sec
             FROM tasks t JOIN projects p ON p.id = t.project_id"""
    args = ()
    if request.args.get("project_id"):
        sql += " WHERE t.project_id = ?"
        args = (request.args["project_id"],)
    sql += " ORDER BY t.priority DESC, t.due_date IS NULL, t.due_date"
    return jsonify(rows(sql, args))


@app.post("/api/tasks")
def create_task():
    d = body()
    if not rows("SELECT id FROM projects WHERE id=?", (d.get("project_id"),)):
        abort(400, "Проект не найден")
    f = validate_task(d)
    tid = execute(
        "INSERT INTO tasks (project_id, title, priority, status, start_date, due_date, notes) VALUES (?,?,?,?,?,?,?)",
        (d["project_id"], f["title"], f["priority"], f["status"], f["start_date"], f["due_date"], f["notes"]))
    return jsonify(rows("SELECT * FROM tasks WHERE id=?", (tid,))[0]), 201


@app.patch("/api/tasks/<int:tid>")
def update_task(tid):
    if not rows("SELECT id FROM tasks WHERE id=?", (tid,)):
        abort(404)
    f = validate_task(body(), partial=True)
    if f:
        sets = ", ".join(f"{k}=?" for k in f)
        execute(f"UPDATE tasks SET {sets} WHERE id=?", (*f.values(), tid))
    return jsonify(rows("SELECT * FROM tasks WHERE id=?", (tid,))[0])


@app.delete("/api/tasks/<int:tid>")
def delete_task(tid):
    execute("DELETE FROM tasks WHERE id=?", (tid,))
    return "", 204


# ---------- учёт времени ----------
@app.post("/api/time")
def add_time():
    """Запись времени: из таймера (duration_sec) или вручную (minutes + date)."""
    d = body()
    if not rows("SELECT id FROM tasks WHERE id=?", (d.get("task_id"),)):
        abort(400, "Задача не найдена")
    manual = "minutes" in d
    try:
        sec = int(float(d["minutes"]) * 60) if manual else int(d.get("duration_sec", 0))
    except (TypeError, ValueError):
        abort(400, "Некорректная длительность")
    if sec <= 0:
        abort(400, "Длительность должна быть больше нуля")
    if manual:
        day = d.get("date") or date.today().isoformat()
        try:
            date.fromisoformat(day)
        except ValueError:
            abort(400, "date: формат ГГГГ-ММ-ДД")
        started = f"{day} 12:00:00"
    else:
        started = d.get("started_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    eid = execute("INSERT INTO time_entries (task_id, started_at, duration_sec, is_manual) VALUES (?,?,?,?)",
                  (d["task_id"], started, sec, int(manual)))
    return jsonify(rows("SELECT * FROM time_entries WHERE id=?", (eid,))[0]), 201


@app.get("/api/time")
def list_time():
    sql = """SELECT e.*, t.title AS task_title FROM time_entries e
             JOIN tasks t ON t.id = e.task_id"""
    args = ()
    if request.args.get("task_id"):
        sql += " WHERE e.task_id = ?"
        args = (request.args["task_id"],)
    return jsonify(rows(sql + " ORDER BY e.started_at DESC LIMIT 200", args))


@app.delete("/api/time/<int:eid>")
def delete_time(eid):
    execute("DELETE FROM time_entries WHERE id=?", (eid,))
    return "", 204


# ---------- отчёты ----------
@app.get("/api/reports/time")
def report_time():
    """Статистика по дням или неделям: ?group=day|week&project_id=."""
    group = request.args.get("group", "day")
    if group not in ("day", "week"):
        abort(400, "group: day или week")
    key = "date(e.started_at)" if group == "day" else "strftime('%Y-W%W', e.started_at)"
    sql = f"""SELECT {key} AS period, SUM(e.duration_sec) AS seconds
              FROM time_entries e JOIN tasks t ON t.id = e.task_id"""
    args = ()
    if request.args.get("project_id"):
        sql += " WHERE t.project_id = ?"
        args = (request.args["project_id"],)
    sql += " GROUP BY period ORDER BY period"
    return jsonify(rows(sql, args))


@app.get("/api/reports/projects")
def report_projects():
    return jsonify(rows("""
        SELECT p.id, p.name,
               COUNT(DISTINCT t.id) AS tasks,
               COUNT(DISTINCT CASE WHEN t.status='done' THEN t.id END) AS done,
               COALESCE(SUM(e.duration_sec), 0) AS seconds
        FROM projects p
        LEFT JOIN tasks t ON t.project_id = p.id
        LEFT JOIN time_entries e ON e.task_id = t.id
        GROUP BY p.id ORDER BY seconds DESC"""))


# ---------- диаграмма Ганта ----------
@app.get("/api/gantt")
def gantt():
    """Задачи в формате Frappe Gantt (только те, у которых есть сроки)."""
    out = []
    for t in rows("""SELECT t.*, p.name AS project_name FROM tasks t
                     JOIN projects p ON p.id = t.project_id
                     WHERE t.due_date IS NOT NULL ORDER BY t.start_date, t.due_date"""):
        start = t["start_date"] or t["due_date"]
        out.append({
            "id": f"t{t['id']}",
            "name": f"{t['project_name']}: {t['title']}",
            "start": start,
            "end": t["due_date"],
            "progress": PROGRESS[t["status"]],
            "custom_class": f"prio-{t['priority']}",
        })
    return jsonify(out)


# ---------- расписание ----------
@app.get("/api/schedule")
def schedule():
    try:
        return jsonify(get_schedule(request.args.get("url")))
    except Exception as exc:  # сеть, кодировка, вёрстка
        return jsonify(error=f"Не удалось получить расписание: {exc}"), 502


@app.post("/api/schedule/import")
def schedule_import():
    """Создаёт в проекте «Расписание» по задаче на каждое занятие."""
    try:
        lessons = get_schedule(body().get("url"))
    except Exception as exc:
        return jsonify(error=f"Не удалось получить расписание: {exc}"), 502
    found = rows("SELECT id FROM projects WHERE name='Расписание'")
    pid = found[0]["id"] if found else execute(
        "INSERT INTO projects (name, description) VALUES ('Расписание', 'Импорт занятий')")
    for item in lessons:
        execute("INSERT INTO tasks (project_id, title, priority, status, notes) VALUES (?,?,?,?,?)",
                (pid, f"{item['subject']}", 1, "todo", f"{item['day']}, {item['time']}, {item['room']}"))
    return jsonify(imported=len(lessons)), 201


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)
