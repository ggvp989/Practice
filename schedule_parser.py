"""Упрощённая интеграция с расписанием: разбор одной HTML-страницы.

Парсер универсальный: берёт все строки таблиц и вытаскивает текст ячеек.
Под свою страницу расписания поправьте parse_schedule() (см. TODO).
"""
import os
import re

import requests
from bs4 import BeautifulSoup

SCHEDULE_URL = os.environ.get("SCHEDULE_URL", "")  # ссылка на страницу расписания
LOCAL_SAMPLE = os.path.join(os.path.dirname(__file__), "sample_schedule.html")


def load_html(url=None):
    """Скачивает страницу. Если URL не задан — берёт локальный пример."""
    url = url or SCHEDULE_URL
    if not url:
        with open(LOCAL_SAMPLE, encoding="utf-8") as f:
            return f.read()
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def parse_schedule(html):
    """Возвращает список занятий: [{day, time, subject, room}].

    TODO: если на вашей странице другая вёрстка, поменяйте селекторы ниже
    (например soup.select("div.lesson")) и порядок колонок.
    """
    soup = BeautifulSoup(html, "html.parser")
    lessons = []
    day = ""
    for row in soup.select("table tr"):
        cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in row.find_all(["td", "th"])]
        if not cells or row.find("th"):
            # строка-заголовок: иногда содержит название дня недели
            if cells and len(cells) == 1:
                day = cells[0]
            continue
        if len(cells) == 1:
            day = cells[0]
            continue
        if len(cells) >= 3:
            lessons.append({
                "day": day,
                "time": cells[0],
                "subject": cells[1],
                "room": cells[2],
            })
    return lessons


def get_schedule(url=None):
    return parse_schedule(load_html(url))
