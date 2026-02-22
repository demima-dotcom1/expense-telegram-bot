import os
import re
import csv
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

# ======================
# CONFIG
# ======================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise SystemExit("Set BOT_TOKEN env var (BOT_TOKEN)")

TZ = ZoneInfo("Europe/Rome")
DB = "expenses.db"

CATEGORIES = [
    "аренда",
    "коммуналка",
    "интернет",
    "продукты",
    "рестораны",
    "доставка еды",
    "бензин",
    "такси",
    "обслуживание авто",
    "одежда",
    "техника",
    "маркетплейсы",
    "лекарства",
    "врачи",
    "дни рождения",
    "праздники",
    "сад",
    "секции",
    "другое",
]

ALIASES = {
    "маркет": "маркетплейсы",
    "доставка": "доставка еды",
    "др": "дни рождения",
    "коммунальные": "коммуналка",
    "инет": "интернет",
}

HELP_TEXT = (
    "✅ Добавление расхода:\n"
    "  `250 продукты`\n"
    "  `19.9 такси`\n"
    "  `45 доставка еды суши`\n\n"
    "📊 Отчёты:\n"
    "  /month — текущий месяц\n"
    "  /month 2026-01 — конкретный месяц\n\n"
    "↩️ Отмена:\n"
    "  /undo — удалить последнюю запись (в этом чате)\n\n"
    "📤 Экспорт:\n"
    "  /export — CSV за текущий месяц (в этом чате)\n"
    "  /export 2026-01 — CSV за конкретный месяц\n\n"
    "Категории:\n  - " + "\n  - ".join(CATEGORIES)
)

# ======================
# DB
# ======================
def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_chat_date ON expenses(chat_id, created_at)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_chat_cat_date ON expenses(chat_id, category, created_at)")

def add_expense(chat_id: int, user_id: int, amount: float, category: str, note: str | None):
    now = datetime.now(TZ).isoformat()
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO expenses (chat_id, user_id, amount, category, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, user_id, amount, category, note, now)
        )

def delete_last_expense(chat_id: int):
    with sqlite3.connect(DB) as con:
        row = con.execute("""
            SELECT id, amount, category, note, created_at, user_id
            FROM expenses
            WHERE chat_id=?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 1
        """, (chat_id,)).fetchone()
        if not row:
            return None
        exp_id = row[0]
        con.execute("DELETE FROM expenses WHERE id=? AND chat_id=?", (exp_id, chat_id))
        return row

def parse_year_month(arg: str | None):
    """
    None -> current month
    "YYYY-MM" -> that month
    """
    if not arg:
        now = datetime.now(TZ)
        y, m = now.year, now.month
    else:
        mobj = re.match(r"^\s*(\d{4})-(\d{2})\s*$", arg)
        if not mobj:
            return None
        y, m = int(mobj.group(1)), int(mobj.group(2))
        if not (1 <= m <= 12):
            return None

    start = datetime(y, m, 1, 0, 0, 0, tzinfo=TZ)
    if m == 12:
        end = datetime(y + 1, 1, 1, 0, 0, 0, tzinfo=TZ)
    else:
        end = datetime(y, m + 1, 1, 0, 0, 0, tzinfo=TZ)

    label = start.strftime("%B %Y")
    return start.isoformat(), end.isoformat(), label

def get_total_and_by_category(chat_id: int, start_iso: str, end_iso: str):
    with sqlite3.connect(DB) as con:
        (total,) = con.execute("""
            SELECT COALESCE(SUM(amount),0)
            FROM expenses
            WHERE chat_id=? AND created_at>=? AND created_at<?
        """, (chat_id, start_iso, end_iso)).fetchone()

        rows = con.execute("""
            SELECT category, COALESCE(SUM(amount),0) AS s
            FROM expenses
            WHERE chat_id=? AND created_at>=? AND created_at<?
            GROUP BY category
        """, (chat_id, start_iso, end_iso)).fetchall()

    by_cat = {cat: float(s) for cat, s in rows}
    return float(total), by_cat

def get_rows_for_export(chat_id: int, start_iso: str, end_iso: str):
    with sqlite3.connect(DB) as con:
        rows = con.execute("""
            SELECT created_at, amount, category, COALESCE(note,''), user_id
            FROM expenses
            WHERE chat_id=? AND created_at>=? AND created_at<?
            ORDER BY datetime(created_at) ASC, id ASC
        """, (chat_id, start_iso, end_iso)).fetchall()
    return rows

# ======================
# PARSING
# ======================
@dataclass
class ParsedExpense:
    amount: float
    category: str
    note: str | None

def is_group(chat: types.Chat) -> bool:
    return chat.type in ("group", "supergroup")

def normalize(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    return s

CATEGORIES_NORM = {normalize(c): c for c in CATEGORIES}  # normalized -> original
ALIASES_NORM = {normalize(k): normalize(v) for k, v in ALIASES.items()}

def resolve_category(rest: str):
    """
    Finds category at beginning of string:
      "доставка еды суши" -> ("доставка еды", "суши")
      "такси" -> ("такси", None)
    """
    rest_n = normalize(rest)

    # alias by first word
    first = rest_n.split(" ", 1)[0]
    if first in ALIASES_NORM:
        mapped = ALIASES_NORM[first]
        rest_n = mapped + ("" if len(rest_n) == len(first) else " " + rest_n[len(first)+1:])

    # match longest first
    for cat_norm in sorted(CATEGORIES_NORM.keys(), key=len, reverse=True):
        if rest_n == cat_norm:
            return CATEGORIES_NORM[cat_norm], None
        if rest_n.startswith(cat_norm + " "):
            note = rest_n[len(cat_norm) + 1:].strip()
            return CATEGORIES_NORM[cat_norm], note

    return None, None

def parse_expense_text(text: str) -> ParsedExpense | None:
    """
    Expected:
      250 продукты
      45 доставка еды суши
    """
    text = (text or "").strip()
    m = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s+(.+)$", text)
    if not m:
        return None

    amount = float(m.group(1).replace(",", "."))
    rest = m.group(2).strip()

    category, note = resolve_category(rest)
    if not category:
        return None

    return ParsedExpense(amount=amount, category=category, note=note)

def format_money(x: float) -> str:
    s = f"{x:,.2f}".replace(",", " ")
    if s.endswith(".00"):
        s = s[:-3]
    return s

# ======================
# BOT
# ======================
async def main():
    init_db()
    bot = Bot(TOKEN)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start(m: types.Message):
        await m.answer(
            "Привет! Я бот для учёта расходов.\n"
            "Если вы в группе — убедитесь, что privacy у бота выключен: @BotFather → /setprivacy → Disable.\n\n"
            + HELP_TEXT,
            parse_mode="Markdown"
        )

    @dp.message(Command("help"))
    async def help_cmd(m: types.Message):
        await m.answer(HELP_TEXT, parse_mode="Markdown")

    @dp.message(Command("month"))
    async def month_cmd(m: types.Message):
        parts = (m.text or "").split(maxsplit=1)
        arg = parts[1] if len(parts) > 1 else None

        parsed_range = parse_year_month(arg)
        if not parsed_range:
            await m.answer("Формат: /month или /month YYYY-MM (пример: /month 2026-01)")
            return

        start_iso, end_iso, label = parsed_range
        total, by_cat = get_total_and_by_category(m.chat.id, start_iso, end_iso)

        lines = [
            f"📊 *Итоги за {label}*",
            f"💰 *Всего:* {format_money(total)}",
            "",
            "*По категориям:*"
        ]

        any_data = any(by_cat.get(c, 0) > 0 for c in CATEGORIES)
        if not any_data:
            lines.append("Пока нет расходов в этом месяце.")
        else:
            for c in CATEGORIES:
                s = by_cat.get(c, 0.0)
                if s > 0:
                    lines.append(f"• {c}: {format_money(s)}")

        await m.answer("\n".join(lines), parse_mode="Markdown")

    @dp.message(Command("undo"))
    async def undo_cmd(m: types.Message):
        row = delete_last_expense(m.chat.id)
        if not row:
            await m.answer("Нечего удалять — записей нет в этом чате.")
            return

        _, amount, category, note, created_at, uid = row
        note_part = f" — {note}" if note else ""
        try:
            dt = datetime.fromisoformat(created_at).astimezone(TZ)
            dt_s = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            dt_s = created_at

        # В группе не палим имена, просто user_id (можно убрать вообще)
        who = f" (user_id {uid})" if is_group(m.chat) else ""
        await m.answer(f"↩️ Удалил последнюю запись{who}:\n{dt_s} — {format_money(float(amount))} — {category}{note_part}")

    @dp.message(Command("export"))
    async def export_cmd(m: types.Message):
        parts = (m.text or "").split(maxsplit=1)
        arg = parts[1] if len(parts) > 1 else None

        parsed_range = parse_year_month(arg)
        if not parsed_range:
            await m.answer("Формат: /export или /export YYYY-MM (пример: /export 2026-01)")
            return

        start_iso, end_iso, label = parsed_range
        rows = get_rows_for_export(m.chat.id, start_iso, end_iso)

        if not rows:
            await m.answer(f"Нет расходов за {label}, нечего экспортировать.")
            return

        safe_label = label.replace(" ", "_")
        filename = f"expenses_{safe_label}.csv"

        with tempfile.NamedTemporaryFile("w", delete=False, newline="", encoding="utf-8", suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerow(["datetime", "amount", "category", "note", "user_id"])
            for created_at, amount, category, note, uid in rows:
                try:
                    dt = datetime.fromisoformat(created_at).astimezone(TZ)
                    created_at_out = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    created_at_out = created_at
                writer.writerow([created_at_out, float(amount), category, note, uid])
            temp_path = f.name

        await m.answer(f"📤 Экспорт за {label}:")
        await m.answer_document(types.FSInputFile(temp_path, filename=filename), caption="CSV файл с расходами")

    @dp.message()
    async def any_text(m: types.Message):
        # Игнорируем сообщения от самого бота
        if m.from_user and m.from_user.is_bot:
            return

        parsed = parse_expense_text(m.text or "")
        if not parsed:
            # В группе молчим, чтобы не мешать
            if is_group(m.chat):
                return

            await m.answer(
                "Не понял формат 😅\n\n"
                "Пиши так: `250 продукты` или `45 доставка еды суши`\n"
                "Команды: /month, /month YYYY-MM, /undo, /export\n"
                "Подсказка: /help",
                parse_mode="Markdown"
            )
            return

        add_expense(m.chat.id, m.from_user.id, parsed.amount, parsed.category, parsed.note)

        if is_group(m.chat):
            # Короткий ответ в группе
            await m.reply(f"✅ {format_money(parsed.amount)} — {parsed.category}")
            return

        note_part = f" — _{parsed.note}_" if parsed.note else ""
        await m.answer(
            f"✅ Записал: *{format_money(parsed.amount)}* — {parsed.category}{note_part}",
            parse_mode="Markdown"
        )

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
