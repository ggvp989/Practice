# Планировщик учебных задач

Веб-приложение: проекты и задачи, учёт времени (таймер + ручной ввод), отчёты, диаграмма Ганта, импорт расписания.
Стек: Python + Flask, SQLite, HTML/CSS/JS, Chart.js, Frappe Gantt.

## Запуск

```bash
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python seed.py                 # тестовые данные (необязательно)
python app.py                  # http://127.0.0.1:5000
```

Тесты: `python -m unittest discover -s tests -v`

## Структура

| Файл | Что делает |
| --- | --- |
| `app.py` | Flask-приложение и REST API |
| `db.py` | схема БД (`projects`, `tasks`, `time_entries`) |
| `seed.py` | автоматическое наполнение БД |
| `schedule_parser.py` | разбор страницы расписания (`requests` + `BeautifulSoup`) |
| `templates/index.html`, `static/` | интерфейс |
| `tests/test_api.py` | автотесты |

## Расписание

Без настроек парсер читает `sample_schedule.html`. Для реальной страницы вставьте ссылку в поле на вкладке «Расписание»
или задайте переменную `SCHEDULE_URL`. Если вёрстка отличается от примера, поправьте селекторы в `parse_schedule()`.

## Работа без интернета

Chart.js и Frappe Gantt подключены через CDN. Чтобы работать офлайн, скачайте файлы в `static/vendor/`
и замените ссылки в `templates/index.html`.
