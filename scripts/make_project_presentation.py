from __future__ import annotations

import json
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "presentation_assets"
PPTX_PATH = ROOT / "smart_cam_project_presentation_10_15min.pptx"
NOTES_PATH = ROOT / "smart_cam_project_speaker_notes.md"

WIDE_W = Inches(13.333)
WIDE_H = Inches(7.5)

COLORS = {
    "ink": RGBColor(30, 39, 46),
    "muted": RGBColor(94, 105, 112),
    "paper": RGBColor(249, 248, 244),
    "white": RGBColor(255, 255, 255),
    "teal": RGBColor(20, 150, 142),
    "green": RGBColor(49, 154, 93),
    "coral": RGBColor(231, 101, 81),
    "amber": RGBColor(239, 173, 77),
    "blue": RGBColor(52, 118, 180),
    "purple": RGBColor(117, 97, 171),
    "line": RGBColor(218, 222, 219),
    "dark": RGBColor(38, 50, 56),
}

FONT = "Aptos"
TITLE_FONT = "Aptos Display"

WORD_COUNT = 1356
PHRASE_COUNT = 916
PHRASE_FIRST_ID = 1357
PHRASE_LAST_ID = 2272


@dataclass
class LogStats:
    files: int
    lines: int
    parse_errors: int
    events: Counter
    sessions: int
    stop_save_ok: int
    total_bytes: int
    mode_sessions: Counter
    mode_stop_saves: Counter
    duration_failed: int
    fps_values: list[float]
    per_day: dict[str, dict[str, int]]


def rgb_to_hex(c: RGBColor) -> str:
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def fmt_gb(n: int) -> str:
    return f"{n / (1024 ** 3):.1f} GB"


def read_log_stats() -> LogStats:
    files = sorted((ROOT / "dashboard" / "recording_logs").glob("recording_log_*.ndjson"))
    events: Counter = Counter()
    mode_sessions: Counter = Counter()
    mode_stop_saves: Counter = Counter()
    per_day: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    session_mode: dict[str, str] = {}
    fps_values: list[float] = []
    lines = 0
    parse_errors = 0
    duration_failed = 0
    stop_save_ok = 0
    total_bytes = 0

    for path in files:
        day = path.stem.replace("recording_log_", "")
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            lines += 1
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                parse_errors += 1
                continue

            event = item.get("event", "")
            mode = item.get("mode") or ""
            session = item.get("session") or ""
            events[event] += 1
            per_day[day][event] += 1

            if event == "START":
                mode_sessions[mode] += 1
                if session:
                    session_mode[session] = mode
                if item.get("expected") == 3:
                    per_day[day]["expected_3"] += 1

            if event == "SESSION_CHECK":
                if (item.get("duration_check") or {}).get("ok") is False:
                    duration_failed += 1
                    per_day[day]["duration_failed"] += 1
                if item.get("saved_ok") == 3 and item.get("failed") == 0:
                    per_day[day]["ok_saved"] += 1
                else:
                    per_day[day]["problem"] += 1

            if event == "STOP_SAVE" and item.get("status") == "ok":
                stop_save_ok += 1
                total_bytes += int(item.get("size_bytes") or 0)
                current_mode = mode or session_mode.get(session, "")
                mode_stop_saves[current_mode] += 1
                fps = item.get("actual_fps")
                if isinstance(fps, (int, float)) and fps > 0:
                    fps_values.append(float(fps))

    return LogStats(
        files=len(files),
        lines=lines,
        parse_errors=parse_errors,
        events=events,
        sessions=events["SESSION_CHECK"],
        stop_save_ok=stop_save_ok,
        total_bytes=total_bytes,
        mode_sessions=mode_sessions,
        mode_stop_saves=mode_stop_saves,
        duration_failed=duration_failed,
        fps_values=fps_values,
        per_day={k: dict(v) for k, v in per_day.items()},
    )


def set_text(shape, text: str, font_size=18, bold=False, color=None, align=None):
    shape.text = text
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(font_size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    if align is not None:
        p.alignment = align
    tf.margin_left = Inches(0.08)
    tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.05)
    tf.margin_bottom = Inches(0.05)


def add_bg(slide, color=COLORS["paper"]):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def add_title(slide, title: str, subtitle: str | None = None):
    box = slide.shapes.add_textbox(Inches(0.62), Inches(0.42), Inches(11.9), Inches(0.58))
    set_text(box, title, 29, True, COLORS["ink"])
    box.text_frame.paragraphs[0].runs[0].font.name = TITLE_FONT
    if subtitle:
        sub = slide.shapes.add_textbox(Inches(0.65), Inches(1.02), Inches(11.1), Inches(0.38))
        set_text(sub, subtitle, 13, False, COLORS["muted"])


def add_footer(slide, index: int, total: int, note: str = ""):
    box = slide.shapes.add_textbox(Inches(0.45), Inches(7.12), Inches(9.2), Inches(0.22))
    set_text(box, note or "Smart Cam / Three Cam project", 8, False, COLORS["muted"])
    num = slide.shapes.add_textbox(Inches(12.35), Inches(7.12), Inches(0.55), Inches(0.22))
    set_text(num, f"{index}/{total}", 8, False, COLORS["muted"], PP_ALIGN.RIGHT)


def add_pill(slide, x, y, text, color=COLORS["teal"], w=1.9):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, Inches(w), Inches(0.34))
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.color.rgb = color
    set_text(shp, text, 10, True, COLORS["white"], PP_ALIGN.CENTER)
    shp.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE


def add_metric_card(slide, x, y, w, h, value, label, color=COLORS["teal"]):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    card.fill.solid()
    card.fill.fore_color.rgb = COLORS["white"]
    card.line.color.rgb = COLORS["line"]
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, Inches(0.08), h)
    accent.fill.solid()
    accent.fill.fore_color.rgb = color
    accent.line.color.rgb = color
    val = slide.shapes.add_textbox(x + Inches(0.22), y + Inches(0.14), w - Inches(0.35), Inches(0.38))
    set_text(val, value, 21, True, color)
    lab = slide.shapes.add_textbox(x + Inches(0.22), y + Inches(0.55), w - Inches(0.35), Inches(0.46))
    set_text(lab, label, 10, False, COLORS["muted"])


def add_bullets(slide, x, y, w, h, items, font_size=15, color=COLORS["ink"], bullet=True):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"• {item}" if bullet else item
        p.font.name = FONT
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.space_after = Pt(5)
    return box


def add_table(slide, x, y, col_widths, row_h, rows, header=True, font_size=10):
    for r, row in enumerate(rows):
        xx = x
        for c, txt in enumerate(row):
            cell = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, xx, y + row_h * r, col_widths[c], row_h)
            cell.fill.solid()
            if header and r == 0:
                cell.fill.fore_color.rgb = COLORS["dark"]
                txt_color = COLORS["white"]
                bold = True
            else:
                cell.fill.fore_color.rgb = COLORS["white"] if r % 2 else RGBColor(243, 246, 244)
                txt_color = COLORS["ink"]
                bold = False
            cell.line.color.rgb = COLORS["line"]
            set_text(cell, str(txt), font_size, bold, txt_color, PP_ALIGN.CENTER if c > 0 else PP_ALIGN.LEFT)
            cell.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
            xx += col_widths[c]


def add_callout(slide, x, y, w, h, title, body, color=COLORS["amber"]):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    box.fill.solid()
    box.fill.fore_color.rgb = COLORS["white"]
    box.line.color.rgb = color
    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, Inches(0.08))
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = color
    stripe.line.color.rgb = color
    t = slide.shapes.add_textbox(x + Inches(0.18), y + Inches(0.17), w - Inches(0.35), Inches(0.32))
    set_text(t, title, 13, True, COLORS["ink"])
    add_bullets(slide, x + Inches(0.18), y + Inches(0.56), w - Inches(0.35), h - Inches(0.65), body, 10, COLORS["muted"], False)


def make_section_slide(prs, blank, number: str, title: str, subtitle: str, color):
    slide = prs.slides.add_slide(blank)
    add_bg(slide, COLORS["dark"])
    add_pill(slide, Inches(0.75), Inches(0.72), number, color, 1.35)
    box = slide.shapes.add_textbox(Inches(0.8), Inches(2.25), Inches(11.7), Inches(0.8))
    set_text(box, title, 36, True, COLORS["white"])
    box.text_frame.paragraphs[0].runs[0].font.name = TITLE_FONT
    sub = slide.shapes.add_textbox(Inches(0.82), Inches(3.15), Inches(10.7), Inches(0.55))
    set_text(sub, subtitle, 18, False, RGBColor(220, 228, 229))
    return slide


def make_workflow_diagram(slide, x, y):
    steps = [
        ("Импорт списка", COLORS["blue"]),
        ("Dashboard", COLORS["teal"]),
        ("3 телефона", COLORS["purple"]),
        ("MP4 + JSON", COLORS["green"]),
        ("NDJSON-аудит", COLORS["amber"]),
    ]
    w = Inches(2.06)
    h = Inches(0.7)
    gap = Inches(0.31)
    for i, (label, color) in enumerate(steps):
        xx = x + i * (w + gap)
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, xx, y, w, h)
        box.fill.solid()
        box.fill.fore_color.rgb = color
        box.line.color.rgb = color
        set_text(box, label, 12, True, COLORS["white"], PP_ALIGN.CENTER)
        box.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        if i < len(steps) - 1:
            arr = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, xx + w - Inches(0.02), y + Inches(0.24), gap + Inches(0.04), Inches(0.22))
            arr.fill.solid()
            arr.fill.fore_color.rgb = COLORS["muted"]
            arr.line.color.rgb = COLORS["muted"]


def make_daily_chart(path: Path):
    data = [
        ("08.24", 1344, 5),
        ("08.25", 1275, 0),
        ("08.26", 1605, 18),
        ("08.27", 1513, 46),
        ("08.28", 160, 3),
        ("09.04", 333, 12),
        ("09.09", 432, 2),
        ("09.10", 613, 3),
        ("09.15", 716, 5),
        ("09.17", 1334, 5),
        ("09.24", 1553, 10),
    ]
    labels = [d[0] for d in data]
    sessions = [d[1] for d in data]
    problems = [d[2] for d in data]
    ok = [s - p for s, p in zip(sessions, problems)]
    plt.figure(figsize=(9.5, 3.55), dpi=160)
    plt.bar(labels, ok, color=rgb_to_hex(COLORS["teal"]), label="OK")
    plt.bar(labels, problems, bottom=ok, color=rgb_to_hex(COLORS["coral"]), label="проблемные")
    plt.ylabel("сессии")
    plt.grid(axis="y", alpha=0.22)
    plt.legend(loc="upper left", frameon=False)
    plt.title("Сессии по дням: 24.08-24.09")
    plt.tight_layout()
    plt.savefig(path, facecolor="white")
    plt.close()


def make_fps_chart(path: Path):
    days = ["06.15", "08.03", "08.05", "08.07", "08.13", "08.24", "08.26", "09.04", "09.05"]
    p05 = [28.66, 29.91, 26.80, 22.44, 21.81, 29.92, 29.92, 29.92, 29.92]
    med = [29.92, 29.92, 29.75, 29.67, 28.48, 29.92, 29.92, 29.92, 29.92]
    colors = [rgb_to_hex(COLORS["coral"])] * 5 + [rgb_to_hex(COLORS["green"])] * 4
    plt.figure(figsize=(8.8, 3.35), dpi=160)
    plt.scatter(days, p05, s=85, c=colors, label="5-й процентиль")
    plt.plot(days, med, color=rgb_to_hex(COLORS["blue"]), marker="o", label="медиана")
    plt.axhline(29.92, color="#444444", linewidth=1, linestyle="--", alpha=0.6)
    plt.ylim(20, 31)
    plt.ylabel("FPS")
    plt.grid(axis="y", alpha=0.22)
    plt.xticks(rotation=30, ha="right")
    plt.legend(loc="lower right", frameon=False)
    plt.title("720p стабилизировал нижний хвост FPS")
    plt.tight_layout()
    plt.savefig(path, facecolor="white")
    plt.close()


def make_block_chart(path: Path):
    labels = ["Слова", "Фразы", "Итого"]
    values = [WORD_COUNT, PHRASE_COUNT, WORD_COUNT + PHRASE_COUNT]
    colors = [rgb_to_hex(COLORS["blue"]), rgb_to_hex(COLORS["green"]), rgb_to_hex(COLORS["teal"])]
    plt.figure(figsize=(7.4, 3.15), dpi=160)
    bars = plt.bar(labels, values, color=colors)
    plt.ylabel("единицы корпуса")
    plt.grid(axis="y", alpha=0.22)
    for b, v in zip(bars, values):
        plt.text(b.get_x() + b.get_width() / 2, v + 40, fmt_int(v), ha="center", fontsize=10)
    plt.ylim(0, 2450)
    plt.title("Структура корпуса: 1356 слов + 916 фраз")
    plt.tight_layout()
    plt.savefig(path, facecolor="white")
    plt.close()


def build_presentation(stats: LogStats):
    OUT_DIR.mkdir(exist_ok=True)
    daily_chart = OUT_DIR / "daily_sessions.png"
    fps_chart = OUT_DIR / "fps_resolution.png"
    block_chart = OUT_DIR / "corpus_blocks.png"
    make_daily_chart(daily_chart)
    make_fps_chart(fps_chart)
    make_block_chart(block_chart)

    prs = Presentation()
    prs.slide_width = WIDE_W
    prs.slide_height = WIDE_H
    blank = prs.slide_layouts[6]
    slides = []
    notes: list[tuple[str, str]] = []

    def new_slide(title, subtitle=None, footer_note=""):
        s = prs.slides.add_slide(blank)
        add_bg(s)
        add_title(s, title, subtitle)
        slides.append((s, footer_note))
        return s

    def add_section(number, title, subtitle, color):
        s = make_section_slide(prs, blank, number, title, subtitle, color)
        slides.append((s, "Структура презентации: слова -> фразы -> общий итог"))
        return s

    s = new_slide("Smart Cam / Three Cam", "Полный рассказ о разработанном приложении: слова, фразы и общий контроль качества")
    add_pill(s, Inches(0.68), Inches(1.52), "10-15 минут", COLORS["teal"], 1.55)
    add_pill(s, Inches(2.36), Inches(1.52), "Июль - сентябрь 2026", COLORS["blue"], 2.05)
    add_metric_card(s, Inches(0.72), Inches(2.23), Inches(2.55), Inches(1.15), "1 356", "слов в словаре", COLORS["blue"])
    add_metric_card(s, Inches(3.55), Inches(2.23), Inches(2.55), Inches(1.15), "916", "фраз: ID 1357-2272", COLORS["green"])
    add_metric_card(s, Inches(6.38), Inches(2.23), Inches(2.55), Inches(1.15), "3 камеры", "одна запись с трех ракурсов", COLORS["purple"])
    add_metric_card(s, Inches(9.21), Inches(2.23), Inches(2.55), Inches(1.15), "51 591", "клип проверен по FPS", COLORS["amber"])
    add_bullets(
        s,
        Inches(0.85),
        Inches(4.0),
        Inches(11.3),
        Inches(1.35),
        [
            "Цель: собрать корпус жестов так, чтобы каждое видео было связано с правильным словом или фразой.",
            "Главная идея приложения: не просто записать MP4, а сразу контролировать метаданные, 3 ракурса, ошибки и качество.",
        ],
        18,
        COLORS["ink"],
        False,
    )
    notes.append(("1. Обложка", "Сказать, что презентация теперь разделена на три части: сбор слов, сбор фраз и общий слой приложения. Главная мысль: приложение создавалось не как камера, а как система надежного сбора датасета."))

    s = new_slide("Логика презентации", "Три блока, чтобы не смешивать разные задачи")
    s.shapes.add_picture(str(block_chart), Inches(0.78), Inches(1.52), width=Inches(5.8), height=Inches(2.55))
    add_callout(
        s,
        Inches(7.0),
        Inches(1.55),
        Inches(4.9),
        Inches(1.18),
        "Блок 1: слова",
        ["1356 слов, PDF-импорт, word_id, дубль, пересъемка, 3 камеры"],
        COLORS["blue"],
    )
    add_callout(
        s,
        Inches(7.0),
        Inches(3.02),
        Inches(4.9),
        Inches(1.18),
        "Блок 2: фразы",
        ["916 фраз, phrase_id 1357-2272, длинный текст, slug, duration_check"],
        COLORS["green"],
    )
    add_callout(
        s,
        Inches(7.0),
        Inches(4.49),
        Inches(4.9),
        Inches(1.18),
        "Блок 3: общая система",
        ["архитектура, логи, FPS, ошибки, отличие от Blackmagic, итог"],
        COLORS["teal"],
    )
    notes.append(("2. Логика презентации", "Пояснить аудитории маршрут: сначала что делали для слов, затем как расширили приложение под фразы, потом общий вывод по архитектуре и качеству."))

    s = new_slide("Приложение от начала до конца", "Что происходит с одной записью")
    make_workflow_diagram(s, Inches(0.75), Inches(1.68))
    rows = [
        ["Этап", "Что делает приложение"],
        ["1. Импорт", "читает список слов/фраз, сохраняет ID, текст, count, segment и expected duration"],
        ["2. Подготовка", "проверяет 3 телефона, заряд, память, device_id, режим записи и текущего сайнера"],
        ["3. Запись", "одним действием запускает 3 телефона и ведет статус каждого ракурса"],
        ["4. Сохранение", "каждый телефон сохраняет MP4 и metadata JSON рядом с видео"],
        ["5. Проверка", "Dashboard пишет NDJSON и проверяет 3/3 файлов, длительность, FPS, ошибки"],
    ]
    add_table(s, Inches(0.85), Inches(3.05), [Inches(2.15), Inches(9.45)], Inches(0.52), rows, True, 10)
    notes.append(("3. Приложение от начала до конца", "Это сквозной слайд. Объяснить один цикл: импортировали список, выбрали сайнера, проверили телефоны, записали, сохранили, сразу проверили."))

    add_section("Блок 1", "Сбор слов: 1356 единиц", "Первый этап: сделать надежную систему для словаря, дублей и трех ракурсов", COLORS["blue"])
    notes.append(("4. Блок 1", "Переход к первой части: на словах мы строили базовую механику приложения и закрывали самые опасные ошибки."))

    s = new_slide("Задача сбора слов", "Нужно было не просто снять 1356 слов, а не потерять связь между видео и разметкой")
    add_metric_card(s, Inches(0.78), Inches(1.55), Inches(2.65), Inches(1.15), "1 356", "слов и служебных единиц", COLORS["blue"])
    add_metric_card(s, Inches(3.75), Inches(1.55), Inches(2.65), Inches(1.15), "3", "ракурса на каждую запись", COLORS["purple"])
    add_metric_card(s, Inches(6.72), Inches(1.55), Inches(2.65), Inches(1.15), "word_id", "главный адрес записи", COLORS["teal"])
    add_metric_card(s, Inches(9.69), Inches(1.55), Inches(2.65), Inches(1.15), "take", "вариант и дубль", COLORS["amber"])
    add_bullets(
        s,
        Inches(0.9),
        Inches(3.3),
        Inches(11.4),
        Inches(2.15),
        [
            "Оператор должен видеть текущее слово крупно и идти по списку без ручного переименования файлов.",
            "После успешной записи приложение само переходит дальше, но не двигает прогресс при ошибке.",
            "Каждый MP4 должен иметь понятное имя и метаданные: signer, word_id, word, take, device, record, duration.",
            "Главный риск этапа: файл есть, но он связан не с тем словом, дублем или ракурсом.",
        ],
        16,
    )
    notes.append(("5. Задача слов", "Сказать, что на этапе слов приложение решало базовую проблему корпуса: видео должно автоматически соответствовать слову, сайнеру, дублю и камере."))

    s = new_slide("Что было реализовано для слов", "Функции, которые превратили съемку в управляемый процесс")
    rows = [
        ["Функция", "Зачем она нужна"],
        ["PDF / список слов", "импортировать словарь и сохранить порядок"],
        ["word_id + 4 цифры", "стабильная сортировка и сквозной адрес слова"],
        ["count / take", "снимать несколько жестов одного слова без путаницы"],
        ["manual back / retake", "доснимать старое слово и не ломать основной прогресс"],
        ["BAD / SUPERSEDED", "оставлять историю пересъемок и понимать, какой дубль годен"],
        ["NDJSON + sidecar JSON", "сохранять метаданные и разбирать их скриптами"],
        ["3-camera status", "видеть, какой телефон пишет и кто подтвердил сохранение"],
    ]
    add_table(s, Inches(0.72), Inches(1.48), [Inches(3.2), Inches(8.2)], Inches(0.55), rows, True, 10)
    notes.append(("6. Реализация слов", "Коротко пройти по функциям. Главное: каждая функция появилась из практической боли на съемке, а не просто для красоты интерфейса."))

    s = new_slide("Ошибки этапа слов и фиксы", "Самые опасные ошибки были тихими: приложение могло выглядеть успешным, а данные уже были испорчены")
    rows = [
        ["Ошибка", "Как проявлялась", "Что сделали / потребовали"],
        ["stop/start потерян", "склейка двух записей или файл отсутствует", "ack, retry, desired state, запас после stop"],
        ["0 байт", "файл пустой, но раньше мог быть ok", "нулевой файл = error"],
        ["STOP_SAVE shift", "подтверждение относилось к прошлой записи", "сверка STOP_SAVE со своей сессией"],
        ["device identity", "телефон назывался чужим номером", "device_id и CAMERA_LAYOUT"],
        ["orientation / reticle", "при START кадр поворачивался, пропадал прицел", "не менять preview rotation при записи"],
    ]
    add_table(s, Inches(0.55), Inches(1.45), [Inches(2.65), Inches(4.15), Inches(4.95)], Inches(0.58), rows, True, 9)
    add_bullets(
        s,
        Inches(0.85),
        Inches(5.45),
        Inches(11.2),
        Inches(0.72),
        ["Принцип фиксов: оператор должен узнать о проблеме на площадке, пока слово можно переснять сразу."],
        17,
        COLORS["coral"],
        False,
    )
    notes.append(("7. Ошибки слов", "Рассказать на примере: склейка или неверный device хуже явной ошибки, потому что они проходят молча. Поэтому мы перешли к проверкам и явным статусам."))

    s = new_slide("Результат по словам", "Базовый режим записи стал проверяемым")
    add_metric_card(s, Inches(0.8), Inches(1.55), Inches(2.6), Inches(1.08), "1209", "записей 07.08, 10 сайнеров", COLORS["blue"])
    add_metric_card(s, Inches(3.75), Inches(1.55), Inches(2.6), Inches(1.08), "0.48%", "дефектных файлов 10-12.08", COLORS["amber"])
    add_metric_card(s, Inches(6.7), Inches(1.55), Inches(2.6), Inches(1.08), "5872", "начатых записей 24-28.08", COLORS["teal"])
    add_metric_card(s, Inches(9.65), Inches(1.55), Inches(2.6), Inches(1.08), "2", "реальные проблемы сохранения", COLORS["coral"])
    add_bullets(
        s,
        Inches(0.9),
        Inches(3.35),
        Inches(11.1),
        Inches(1.9),
        [
            "После слов стало понятно, какие проверки обязательны: журнал против диска, 3/3 сохранений, длительность между камерами, состав списка.",
            "Слова закрыли базовую механику: импорт, движение по списку, имена файлов, метаданные, пересъемки и проверка сохранения.",
            "Именно этот фундамент позволил безопасно перейти к фразам.",
        ],
        16,
    )
    notes.append(("8. Результат по словам", "Здесь связать первый блок со вторым: мы не просто сняли слова, мы построили инфраструктуру, на которой потом стало возможно снимать фразы."))

    add_section("Блок 2", "Сбор фраз: 916 единиц", "Второй этап: длинный текст, сквозная нумерация и контроль длительности", COLORS["green"])
    notes.append(("9. Блок 2", "Переход: фразы сложнее слов, потому что они длиннее, чаще требуют пересъемки и имеют больше шансов оборваться."))

    s = new_slide("Задача сбора фраз", "Фразы нельзя просто записать как длинное слово")
    add_metric_card(s, Inches(0.78), Inches(1.55), Inches(2.65), Inches(1.12), "916", "фраз в расширении", COLORS["green"])
    add_metric_card(s, Inches(3.75), Inches(1.55), Inches(2.65), Inches(1.12), "1357-2272", "диапазон phrase_id", COLORS["teal"])
    add_metric_card(s, Inches(6.72), Inches(1.55), Inches(2.65), Inches(1.12), "slug", "короткое имя файла", COLORS["amber"])
    add_metric_card(s, Inches(9.69), Inches(1.55), Inches(2.65), Inches(1.12), "1500 ms", "порог разброса длительности", COLORS["purple"])
    add_bullets(
        s,
        Inches(0.9),
        Inches(3.3),
        Inches(11.25),
        Inches(2.0),
        [
            "Словарь заканчивается на 1356, поэтому фразы продолжают ту же нумерацию: 1357-2272.",
            "Нельзя нумеровать фразы с единицы: номера попадут поверх уже существующих слов.",
            "Полный текст фразы хранится в metadata, а имя файла остается коротким и стабильным.",
            "Для длинных фраз нужны segment_index / segment_count и ожидаемая длительность.",
        ],
        16,
    )
    notes.append(("10. Задача фраз", "Главная мысль: фразы потребовали не нового приложения, а аккуратного расширения модели данных. ID должны продолжать словарь, а длинный текст не должен ломать имена файлов."))

    s = new_slide("Что добавили для фраз", "Расширили приложение, не ломая режим word")
    rows = [
        ["Поле / функция", "Назначение"],
        ["mode = phrase", "отделить фразы от старого режима word"],
        ["phrase_id из списка", "сохранить сквозную нумерацию корпуса"],
        ["phrase_text", "хранить полный текст в metadata и логе"],
        ["file_slug", "делать короткие имена: phrase_1380_a_1_device_2..."],
        ["expected_duration_ms", "сравнивать запись с ожидаемой длиной"],
        ["segment_index / segment_count", "готовность к разбиению длинных фраз"],
        ["duration_check", "после stop проверять разброс длительности 3 камер"],
    ]
    add_table(s, Inches(0.72), Inches(1.48), [Inches(3.25), Inches(8.15)], Inches(0.55), rows, True, 10)
    notes.append(("11. Реализация фраз", "Пояснить, что эти поля нужны не для бюрократии, а чтобы потом автоматически понять: какая фраза, какой дубль, какая попытка, какой сегмент и всё ли записалось."))

    s = new_slide("Проверка фраз на практике", "Сентябрь показал, что контроль стал работать прямо на площадке")
    add_metric_card(s, Inches(0.8), Inches(1.55), Inches(2.6), Inches(1.08), "1142", "записи за 09-11.09", COLORS["green"])
    add_metric_card(s, Inches(3.75), Inches(1.55), Inches(2.6), Inches(1.08), "0", "потеряно", COLORS["teal"])
    add_metric_card(s, Inches(6.7), Inches(1.55), Inches(2.6), Inches(1.08), "303", "уникальных phrase_id 09.09", COLORS["blue"])
    add_metric_card(s, Inches(9.65), Inches(1.55), Inches(2.6), Inches(1.08), "14", "стартов заблокированы вместо ложного ok", COLORS["amber"])
    add_callout(
        s,
        Inches(0.9),
        Inches(3.35),
        Inches(5.45),
        Inches(1.65),
        "Показательный случай",
        ["Фраза 1380: две камеры записали 10.3 с, третья 7.3 с", "duration_check поймал обрыв", "оператор переснял через 10 минут"],
        COLORS["green"],
    )
    add_callout(
        s,
        Inches(6.8),
        Inches(3.35),
        Inches(5.45),
        Inches(1.65),
        "Почему это важно",
        ["раньше такие дефекты находили через две недели", "теперь ошибка видна до ухода сайнера", "пересъемка становится частью процесса"],
        COLORS["teal"],
    )
    notes.append(("12. Практика фраз", "Это сильный слайд: показать, что система не только записывает фразы, но и ловит неправильную длительность сразу."))

    s = new_slide("Что еще нужно по фразам", "Остались пункты, которые уменьшают ручную работу")
    rows = [
        ["Проблема", "Почему важно", "Что сделать"],
        ["attempt не растет", "пересъемки выглядят одинаково", "реально писать a_1 / a_2"],
        ["expected_duration_ms = null", "проверка длительности без опоры", "брать время из списка фраз"],
        ["длинные фразы обрезаются", "лог теряет читаемость", "полный текст в metadata без лимита 56 символов"],
        ["счетчик сбрасывается", "одни номера у разных людей", "сброс один раз в начале дня"],
        ["экспозиция гуляет", "модель учит условия, а не жест", "фиксировать ISO/баланс/фокус или логировать"],
    ]
    add_table(s, Inches(0.55), Inches(1.48), [Inches(2.7), Inches(4.15), Inches(4.85)], Inches(0.58), rows, True, 9)
    notes.append(("13. Осталось по фразам", "Подать это как технический долг. Основной процесс работает, но эти пункты нужны, чтобы убрать ручные допущения и сделать фразы полностью автоматизированными."))

    add_section("Блок 3", "Общая система и итог", "Что получилось как приложение, чем оно отличается от обычной камеры и как контролируется качество", COLORS["teal"])
    notes.append(("14. Блок 3", "Переход к общему итогу: теперь смотрим на приложение как на систему, которая обслуживает оба режима: слова и фразы."))

    s = new_slide("Общая архитектура приложения", "Один workflow для слов и фраз")
    rows = [
        ["Компонент", "Ответственность"],
        ["Dashboard", "импорт списков, очередь, сайнеры, прогресс, старт/стоп, проверки"],
        ["Mobile app", "камера, запись MP4, sidecar JSON, статус телефона"],
        ["Протокол", "HTTP сейчас, WS/scheduler подготовлен для более точного старта"],
        ["Логи", "NDJSON: START, START_ACK, STOP, STOP_SAVE, SESSION_CHECK, CAMERA_LAYOUT"],
        ["Аналитика", "сверка 3/3 файлов, длительности, FPS, ошибок, проблемных дней"],
    ]
    add_table(s, Inches(0.75), Inches(1.52), [Inches(3.0), Inches(8.55)], Inches(0.62), rows, True, 11)
    add_bullets(
        s,
        Inches(0.95),
        Inches(5.55),
        Inches(11.0),
        Inches(0.55),
        ["Итог архитектуры: word и phrase используют общий надежный цикл записи, но имеют разные metadata-поля."],
        16,
        COLORS["teal"],
        False,
    )
    notes.append(("15. Архитектура", "Объяснить, что приложение стало платформой: режимы разные, но скелет один. Это важно для поддержки и будущих расширений."))

    s = new_slide("Почему не просто Blackmagic", "Blackmagic пишет видео; Smart Cam управляет корпусом данных")
    rows = [
        ["Критерий", "Blackmagic / обычная камера", "Smart Cam / Three Cam"],
        ["Список заданий", "оператор ведет отдельно", "word_id / phrase_id внутри workflow"],
        ["3 ракурса", "синхронизация вручную", "3 телефона как одна сессия"],
        ["Метаданные", "отдельная таблица или ручная работа", "metadata JSON рядом с MP4 + NDJSON"],
        ["Ошибки", "часто видны после просмотра", "START_FAILED, SESSION_CHECK, duration_check"],
        ["Пересъемка", "ручное решение", "BAD / SUPERSEDED / RETAKE / attempt"],
    ]
    add_table(s, Inches(0.62), Inches(1.55), [Inches(2.35), Inches(4.5), Inches(4.9)], Inches(0.6), rows, True, 10)
    add_bullets(
        s,
        Inches(0.95),
        Inches(5.65),
        Inches(11.0),
        Inches(0.6),
        ["Вывод: Blackmagic решает качество картинки, а наш проект решает качество, воспроизводимость и проверяемость ML-датасета."],
        16,
        COLORS["ink"],
        False,
    )
    notes.append(("16. Blackmagic", "Не говорить, что Blackmagic плохой. Сказать, что он решает другую задачу. Нам нужен не просто красивый видеопоток, а автоматическая связь видео с разметкой и проверками."))

    s = new_slide("Общий контроль качества", "Теперь можно считать состояние корпуса, а не спорить на глаз")
    s.shapes.add_picture(str(daily_chart), Inches(0.65), Inches(1.45), width=Inches(7.65), height=Inches(3.05))
    add_metric_card(s, Inches(8.75), Inches(1.48), Inches(2.7), Inches(0.95), "17 387", "SESSION_CHECK в локальных логах", COLORS["teal"])
    add_metric_card(s, Inches(8.75), Inches(2.58), Inches(2.7), Inches(0.95), "52 149", "STOP_SAVE ok", COLORS["green"])
    add_metric_card(s, Inches(8.75), Inches(3.68), Inches(2.7), Inches(0.95), "345.6 GB", "объем по локальным логам", COLORS["blue"])
    add_metric_card(s, Inches(8.75), Inches(4.78), Inches(2.7), Inches(0.95), "0", "битых JSON-строк", COLORS["amber"])
    add_bullets(
        s,
        Inches(0.9),
        Inches(5.75),
        Inches(11.0),
        Inches(0.55),
        [f"Локально прочитано: {stats.files} NDJSON-файла, {fmt_int(stats.lines)} строк; START_FAILED: {stats.events['START_FAILED']}, EMERGENCY_STOP: {stats.events['EMERGENCY_STOP']}."],
        12,
        COLORS["muted"],
        False,
    )
    notes.append(("17. Контроль качества", "Здесь показать, что общая система стала измеримой. Мы видим дни, проблемы, количество файлов, статусы, объем и можем возвращаться к конкретной сессии."))

    s = new_slide("FPS и разрешение", "Переход на 720p решил часть проблемы качества записи")
    s.shapes.add_picture(str(fps_chart), Inches(0.65), Inches(1.45), width=Inches(8.1), height=Inches(3.1))
    add_metric_card(s, Inches(9.18), Inches(1.45), Inches(2.65), Inches(0.95), "29.92", "основная частота корпуса", COLORS["blue"])
    add_metric_card(s, Inches(9.18), Inches(2.55), Inches(2.65), Inches(0.95), "28.5%", "клипов медленнее нее", COLORS["coral"])
    add_metric_card(s, Inches(9.18), Inches(3.65), Inches(2.65), Inches(0.95), "12.39", "худший FPS", COLORS["amber"])
    rows = [
        ["Разрешение", "Клипы", "Вывод"],
        ["1080x1920", "33 724", "телефоны теряли кадры"],
        ["720x1280", "17 867", "нижний хвост FPS исчез"],
    ]
    add_table(s, Inches(0.95), Inches(5.25), [Inches(2.5), Inches(2.0), Inches(6.0)], Inches(0.52), rows, True, 11)
    notes.append(("18. FPS", "Объяснить, почему FPS важен: модель ест окно в кадрах, а не в секундах. Если FPS падает до 15, жест внутри окна становится в два раза длиннее."))

    s = new_slide("Итог и следующий шаг", "Что проект дал и что нужно довести")
    add_metric_card(s, Inches(0.72), Inches(1.55), Inches(2.55), Inches(1.08), "слова", "1356 единиц: базовый workflow", COLORS["blue"])
    add_metric_card(s, Inches(3.55), Inches(1.55), Inches(2.55), Inches(1.08), "фразы", "916 единиц: расширение metadata", COLORS["green"])
    add_metric_card(s, Inches(6.38), Inches(1.55), Inches(2.55), Inches(1.08), "аудит", "логи + проверки + FPS", COLORS["teal"])
    add_metric_card(s, Inches(9.21), Inches(1.55), Inches(2.55), Inches(1.08), "оператор", "ошибка видна на площадке", COLORS["amber"])
    add_bullets(
        s,
        Inches(0.95),
        Inches(3.15),
        Inches(11.1),
        Inches(2.25),
        [
            "Мы разработали приложение как конвейер сбора датасета: импорт -> запись -> сохранение -> проверка -> пересъемка.",
            "Для слов приложение решило связь видео с word_id, дублями, сайнером и тремя камерами.",
            "Для фраз добавлены phrase_id, короткие file_slug, полный текст, сегменты и проверка длительности.",
            "Общий следующий шаг: закрыть attempt, expected_duration_ms, счетчик дня, экспозицию и протокол агента.",
        ],
        16,
    )
    notes.append(("19. Итог", "Закрыть спокойно и уверенно: теперь есть понятная система для слов и фраз, а не хаотичная съемка. Следующие пункты ясные и технически ограниченные."))

    s = new_slide("Источники внутри проекта", "Откуда взяты цифры и выводы")
    rows = [
        ["Файл", "Что взято"],
        ["TZ_2026_08_09.md", "требования к сбору слов и логам"],
        ["BUG_REPORT_shooting_app.md", "ошибки stop/start, device identity, orientation"],
        ["LOGS_AUDIT_2026-09-02.md", "аудит логов 24-28 августа"],
        ["FOR_DEVS_2026_09_08.md", "переход от слов к фразам, 1356 + 916"],
        ["FOR_DEVS_2026_09_12.md", "результаты 9-11 сентября и FPS-аудит"],
        ["recording_logs_analysis_20260824_20260924.md", "сводка по сессиям и файлам"],
        ["dashboard/recording_logs/*.ndjson", "локальная проверка событий, статусов, FPS"],
    ]
    add_table(s, Inches(0.75), Inches(1.48), [Inches(5.0), Inches(6.35)], Inches(0.55), rows, True, 10)
    notes.append(("20. Источники", "Этот слайд можно не показывать в устной защите, но оставить в конце как доказательство, что цифры взяты из файлов проекта."))

    total = len(slides)
    for i, (slide, footer_note) in enumerate(slides, 1):
        add_footer(slide, i, total, footer_note)

    prs.save(PPTX_PATH)

    lines = ["# Текст выступления к презентации", ""]
    lines.append("Ориентир по времени: 20 слайдов. Для 10 минут проходить слайды-блоки 4, 9, 14 и источники очень быстро; для 15 минут раскрывать примеры ошибок подробнее.")
    lines.append("")
    for title, body in notes:
        lines.append(f"## {title}")
        lines.append(body)
        lines.append("")
    NOTES_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    stats = read_log_stats()
    build_presentation(stats)
    with zipfile.ZipFile(PPTX_PATH) as zf:
        slide_count = len([n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
    print(f"PPTX: {PPTX_PATH}")
    print(f"Speaker notes: {NOTES_PATH}")
    print(f"Slides: {slide_count}")
    print(f"Local logs: {stats.files} files, {fmt_int(stats.lines)} rows, {stats.parse_errors} JSON errors")
    print(f"Events: START={stats.events['START']}, SESSION_CHECK={stats.sessions}, STOP_SAVE ok={stats.stop_save_ok}")
    print(f"Bytes in STOP_SAVE ok: {fmt_gb(stats.total_bytes)}")
    if stats.fps_values:
        print(f"Logged actual_fps: min={min(stats.fps_values):.3f}, avg={sum(stats.fps_values)/len(stats.fps_values):.3f}, max={max(stats.fps_values):.3f}")


if __name__ == "__main__":
    main()
