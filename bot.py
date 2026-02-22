{\rtf1\ansi\ansicpg1251\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 Format \uc0\u8594  Make Plain Text\
import os\
import re\
import csv\
import sqlite3\
import tempfile\
from dataclasses import dataclass\
from datetime import datetime\
from zoneinfo import ZoneInfo\
\
from aiogram import Bot, Dispatcher, types\
from aiogram.filters import Command\
import asyncio\
\
TOKEN = os.getenv("BOT_TOKEN")\
if not TOKEN:\
    raise SystemExit("Set BOT_TOKEN env var (BOT_TOKEN)")\
\
TZ = ZoneInfo("Europe/Rome")\
DB = "expenses.db"\
\
CATEGORIES = [\
    "\uc0\u1072 \u1088 \u1077 \u1085 \u1076 \u1072 ",\
    "\uc0\u1082 \u1086 \u1084 \u1084 \u1091 \u1085 \u1072 \u1083 \u1082 \u1072 ",\
    "\uc0\u1080 \u1085 \u1090 \u1077 \u1088 \u1085 \u1077 \u1090 ",\
    "\uc0\u1087 \u1088 \u1086 \u1076 \u1091 \u1082 \u1090 \u1099 ",\
    "\uc0\u1088 \u1077 \u1089 \u1090 \u1086 \u1088 \u1072 \u1085 \u1099 ",\
    "\uc0\u1076 \u1086 \u1089 \u1090 \u1072 \u1074 \u1082 \u1072  \u1077 \u1076 \u1099 ",\
    "\uc0\u1073 \u1077 \u1085 \u1079 \u1080 \u1085 ",\
    "\uc0\u1090 \u1072 \u1082 \u1089 \u1080 ",\
    "\uc0\u1086 \u1073 \u1089 \u1083 \u1091 \u1078 \u1080 \u1074 \u1072 \u1085 \u1080 \u1077  \u1072 \u1074 \u1090 \u1086 ",\
    "\uc0\u1086 \u1076 \u1077 \u1078 \u1076 \u1072 ",\
    "\uc0\u1090 \u1077 \u1093 \u1085 \u1080 \u1082 \u1072 ",\
    "\uc0\u1084 \u1072 \u1088 \u1082 \u1077 \u1090 \u1087 \u1083 \u1077 \u1081 \u1089 \u1099 ",\
    "\uc0\u1083 \u1077 \u1082 \u1072 \u1088 \u1089 \u1090 \u1074 \u1072 ",\
    "\uc0\u1074 \u1088 \u1072 \u1095 \u1080 ",\
    "\uc0\u1076 \u1085 \u1080  \u1088 \u1086 \u1078 \u1076 \u1077 \u1085 \u1080 \u1103 ",\
    "\uc0\u1087 \u1088 \u1072 \u1079 \u1076 \u1085 \u1080 \u1082 \u1080 ",\
    "\uc0\u1089 \u1072 \u1076 ",\
    "\uc0\u1089 \u1077 \u1082 \u1094 \u1080 \u1080 ",\
    "\uc0\u1076 \u1088 \u1091 \u1075 \u1086 \u1077 ",\
]\
\
ALIASES = \{\
    "\uc0\u1084 \u1072 \u1088 \u1082 \u1077 \u1090 ": "\u1084 \u1072 \u1088 \u1082 \u1077 \u1090 \u1087 \u1083 \u1077 \u1081 \u1089 \u1099 ",\
    "\uc0\u1076 \u1086 \u1089 \u1090 \u1072 \u1074 \u1082 \u1072 ": "\u1076 \u1086 \u1089 \u1090 \u1072 \u1074 \u1082 \u1072  \u1077 \u1076 \u1099 ",\
    "\uc0\u1076 \u1088 ": "\u1076 \u1085 \u1080  \u1088 \u1086 \u1078 \u1076 \u1077 \u1085 \u1080 \u1103 ",\
    "\uc0\u1082 \u1086 \u1084 \u1084 \u1091 \u1085 \u1072 \u1083 \u1100 \u1085 \u1099 \u1077 ": "\u1082 \u1086 \u1084 \u1084 \u1091 \u1085 \u1072 \u1083 \u1082 \u1072 ",\
    "\uc0\u1080 \u1085 \u1077 \u1090 ": "\u1080 \u1085 \u1090 \u1077 \u1088 \u1085 \u1077 \u1090 ",\
\}\
\
HELP_TEXT = (\
    "\uc0\u9989  \u1044 \u1086 \u1073 \u1072 \u1074 \u1083 \u1077 \u1085 \u1080 \u1077  \u1088 \u1072 \u1089 \u1093 \u1086 \u1076 \u1072 :\\n"\
    "  `250 \uc0\u1087 \u1088 \u1086 \u1076 \u1091 \u1082 \u1090 \u1099 `\\n"\
    "  `19.9 \uc0\u1090 \u1072 \u1082 \u1089 \u1080 `\\n"\
    "  `45 \uc0\u1076 \u1086 \u1089 \u1090 \u1072 \u1074 \u1082 \u1072  \u1077 \u1076 \u1099  \u1089 \u1091 \u1096 \u1080 `\\n\\n"\
    "\uc0\u55357 \u56522  \u1054 \u1090 \u1095 \u1105 \u1090 \u1099 :\\n"\
    "  /month \'97 \uc0\u1090 \u1077 \u1082 \u1091 \u1097 \u1080 \u1081  \u1084 \u1077 \u1089 \u1103 \u1094 \\n"\
    "  /month 2026-01 \'97 \uc0\u1082 \u1086 \u1085 \u1082 \u1088 \u1077 \u1090 \u1085 \u1099 \u1081  \u1084 \u1077 \u1089 \u1103 \u1094 \\n\\n"\
    "\uc0\u8617 \u65039  \u1054 \u1090 \u1084 \u1077 \u1085 \u1072 :\\n"\
    "  /undo \'97 \uc0\u1091 \u1076 \u1072 \u1083 \u1080 \u1090 \u1100  \u1087 \u1086 \u1089 \u1083 \u1077 \u1076 \u1085 \u1102 \u1102  \u1079 \u1072 \u1087 \u1080 \u1089 \u1100 \\n\\n"\
    "\uc0\u55357 \u56548  \u1069 \u1082 \u1089 \u1087 \u1086 \u1088 \u1090 :\\n"\
    "  /export \'97 CSV \uc0\u1079 \u1072  \u1090 \u1077 \u1082 \u1091 \u1097 \u1080 \u1081  \u1084 \u1077 \u1089 \u1103 \u1094 \\n"\
    "  /export 2026-01 \'97 CSV \uc0\u1079 \u1072  \u1082 \u1086 \u1085 \u1082 \u1088 \u1077 \u1090 \u1085 \u1099 \u1081  \u1084 \u1077 \u1089 \u1103 \u1094 \\n\\n"\
    "\uc0\u1050 \u1072 \u1090 \u1077 \u1075 \u1086 \u1088 \u1080 \u1080 :\\n  - " + "\\n  - ".join(CATEGORIES)\
)\
\
def init_db():\
    with sqlite3.connect(DB) as con:\
        con.execute("""\
            CREATE TABLE IF NOT EXISTS expenses (\
                id INTEGER PRIMARY KEY AUTOINCREMENT,\
                user_id INTEGER NOT NULL,\
                amount REAL NOT NULL,\
                category TEXT NOT NULL,\
                note TEXT,\
                created_at TEXT NOT NULL\
            )\
        """)\
        con.execute("CREATE INDEX IF NOT EXISTS idx_user_date ON expenses(user_id, created_at)")\
        con.execute("CREATE INDEX IF NOT EXISTS idx_user_cat_date ON expenses(user_id, category, created_at)")\
\
def add_expense(user_id: int, amount: float, category: str, note: str | None):\
    now = datetime.now(TZ).isoformat()\
    with sqlite3.connect(DB) as con:\
        con.execute(\
            "INSERT INTO expenses (user_id, amount, category, note, created_at) VALUES (?, ?, ?, ?, ?)",\
            (user_id, amount, category, note, now)\
        )\
\
def delete_last_expense(user_id: int):\
    with sqlite3.connect(DB) as con:\
        row = con.execute("""\
            SELECT id, amount, category, note, created_at\
            FROM expenses\
            WHERE user_id=?\
            ORDER BY datetime(created_at) DESC, id DESC\
            LIMIT 1\
        """, (user_id,)).fetchone()\
        if not row:\
            return None\
        exp_id = row[0]\
        con.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (exp_id, user_id))\
        return row\
\
def parse_year_month(arg: str | None):\
    if not arg:\
        now = datetime.now(TZ)\
        y, m = now.year, now.month\
    else:\
        mobj = re.match(r"^\\s*(\\d\{4\})-(\\d\{2\})\\s*$", arg)\
        if not mobj:\
            return None\
        y, m = int(mobj.group(1)), int(mobj.group(2))\
        if m < 1 or m > 12:\
            return None\
\
    start = datetime(y, m, 1, 0, 0, 0, tzinfo=TZ)\
    if m == 12:\
        end = datetime(y + 1, 1, 1, 0, 0, 0, tzinfo=TZ)\
    else:\
        end = datetime(y, m + 1, 1, 0, 0, 0, tzinfo=TZ)\
\
    label = start.strftime("%B %Y")\
    return start.isoformat(), end.isoformat(), label\
\
def get_total_and_by_category(user_id: int, start_iso: str, end_iso: str):\
    with sqlite3.connect(DB) as con:\
        (total,) = con.execute("""\
            SELECT COALESCE(SUM(amount),0)\
            FROM expenses\
            WHERE user_id=? AND created_at>=? AND created_at<?\
        """, (user_id, start_iso, end_iso)).fetchone()\
\
        rows = con.execute("""\
            SELECT category, COALESCE(SUM(amount),0) AS s\
            FROM expenses\
            WHERE user_id=? AND created_at>=? AND created_at<?\
            GROUP BY category\
        """, (user_id, start_iso, end_iso)).fetchall()\
\
    by_cat = \{cat: float(s) for cat, s in rows\}\
    return float(total), by_cat\
\
def get_rows_for_export(user_id: int, start_iso: str, end_iso: str):\
    with sqlite3.connect(DB) as con:\
        rows = con.execute("""\
            SELECT created_at, amount, category, COALESCE(note,'')\
            FROM expenses\
            WHERE user_id=? AND created_at>=? AND created_at<?\
            ORDER BY datetime(created_at) ASC, id ASC\
        """, (user_id, start_iso, end_iso)).fetchall()\
    return rows\
\
@dataclass\
class ParsedExpense:\
    amount: float\
    category: str\
    note: str | None\
\
def normalize(s: str) -> str:\
    s = s.strip().lower()\
    s = s.replace("\uc0\u1105 ", "\u1077 ")\
    s = re.sub(r"\\s+", " ", s)\
    return s\
\
CATEGORIES_NORM = \{normalize(c): c for c in CATEGORIES\}\
ALIASES_NORM = \{normalize(k): normalize(v) for k, v in ALIASES.items()\}\
\
def resolve_category(rest: str):\
    rest_n = normalize(rest)\
\
    first = rest_n.split(" ", 1)[0]\
    if first in ALIASES_NORM:\
        mapped = ALIASES_NORM[first]\
        rest_n = mapped + ("" if len(rest_n) == len(first) else " " + rest_n[len(first)+1:])\
\
    for cat_norm in sorted(CATEGORIES_NORM.keys(), key=len, reverse=True):\
        if rest_n == cat_norm:\
            return CATEGORIES_NORM[cat_norm], None\
        if rest_n.startswith(cat_norm + " "):\
            note = rest_n[len(cat_norm)+1:].strip()\
            return CATEGORIES_NORM[cat_norm], note\
\
    return None, None\
\
def parse_message(text: str) -> ParsedExpense | None:\
    text = (text or "").strip()\
    m = re.match(r"^\\s*(\\d+(?:[.,]\\d+)?)\\s+(.+)$", text)\
    if not m:\
        return None\
\
    amount = float(m.group(1).replace(",", "."))\
    rest = m.group(2).strip()\
    category, note = resolve_category(rest)\
    if not category:\
        return None\
    return ParsedExpense(amount=amount, category=category, note=note)\
\
def format_money(x: float) -> str:\
    s = f"\{x:,.2f\}".replace(",", " ")\
    if s.endswith(".00"):\
        s = s[:-3]\
    return s\
\
async def main():\
    init_db()\
    bot = Bot(TOKEN)\
    dp = Dispatcher()\
\
    @dp.message(Command("start"))\
    async def start(m: types.Message):\
        await m.answer("\uc0\u1055 \u1088 \u1080 \u1074 \u1077 \u1090 ! \u1071  \u1073 \u1086 \u1090  \u1076 \u1083 \u1103  \u1091 \u1095 \u1105 \u1090 \u1072  \u1088 \u1072 \u1089 \u1093 \u1086 \u1076 \u1086 \u1074 .\\n\\n" + HELP_TEXT, parse_mode="Markdown")\
\
    @dp.message(Command("help"))\
    async def help_cmd(m: types.Message):\
        await m.answer(HELP_TEXT, parse_mode="Markdown")\
\
    @dp.message(Command("month"))\
    async def month_cmd(m: types.Message):\
        parts = (m.text or "").split(maxsplit=1)\
        arg = parts[1] if len(parts) > 1 else None\
\
        parsed_range = parse_year_month(arg)\
        if not parsed_range:\
            await m.answer("\uc0\u1060 \u1086 \u1088 \u1084 \u1072 \u1090 : /month \u1080 \u1083 \u1080  /month YYYY-MM (\u1087 \u1088 \u1080 \u1084 \u1077 \u1088 : /month 2026-01)")\
            return\
\
        start_iso, end_iso, label = parsed_range\
        user_id = m.from_user.id\
        total, by_cat = get_total_and_by_category(user_id, start_iso, end_iso)\
\
        lines = [\
            f"\uc0\u55357 \u56522  *\u1048 \u1090 \u1086 \u1075 \u1080  \u1079 \u1072  \{label\}*",\
            f"\uc0\u55357 \u56496  *\u1042 \u1089 \u1077 \u1075 \u1086 :* \{format_money(total)\}",\
            "",\
            "*\uc0\u1055 \u1086  \u1082 \u1072 \u1090 \u1077 \u1075 \u1086 \u1088 \u1080 \u1103 \u1084 :*"\
        ]\
\
        any_data = any(by_cat.get(c, 0) > 0 for c in CATEGORIES)\
        if not any_data:\
            lines.append("\uc0\u1055 \u1086 \u1082 \u1072  \u1085 \u1077 \u1090  \u1088 \u1072 \u1089 \u1093 \u1086 \u1076 \u1086 \u1074  \u1074  \u1101 \u1090 \u1086 \u1084  \u1084 \u1077 \u1089 \u1103 \u1094 \u1077 .")\
        else:\
            for c in CATEGORIES:\
                s = by_cat.get(c, 0.0)\
                if s > 0:\
                    lines.append(f"\'95 \{c\}: \{format_money(s)\}")\
\
        await m.answer("\\n".join(lines), parse_mode="Markdown")\
\
    @dp.message(Command("undo"))\
    async def undo_cmd(m: types.Message):\
        row = delete_last_expense(m.from_user.id)\
        if not row:\
            await m.answer("\uc0\u1053 \u1077 \u1095 \u1077 \u1075 \u1086  \u1091 \u1076 \u1072 \u1083 \u1103 \u1090 \u1100  \'97 \u1079 \u1072 \u1087 \u1080 \u1089 \u1077 \u1081  \u1085 \u1077 \u1090 .")\
            return\
\
        _, amount, category, note, created_at = row\
        note_part = f" \'97 \{note\}" if note else ""\
        try:\
            dt = datetime.fromisoformat(created_at).astimezone(TZ)\
            dt_s = dt.strftime("%Y-%m-%d %H:%M")\
        except Exception:\
            dt_s = created_at\
\
        await m.answer(\
            f"\uc0\u8617 \u65039  \u1059 \u1076 \u1072 \u1083 \u1080 \u1083  \u1087 \u1086 \u1089 \u1083 \u1077 \u1076 \u1085 \u1102 \u1102  \u1079 \u1072 \u1087 \u1080 \u1089 \u1100 :\\n"\
            f"\{dt_s\} \'97 \{format_money(float(amount))\} \'97 \{category\}\{note_part\}"\
        )\
\
    @dp.message(Command("export"))\
    async def export_cmd(m: types.Message):\
        parts = (m.text or "").split(maxsplit=1)\
        arg = parts[1] if len(parts) > 1 else None\
\
        parsed_range = parse_year_month(arg)\
        if not parsed_range:\
            await m.answer("\uc0\u1060 \u1086 \u1088 \u1084 \u1072 \u1090 : /export \u1080 \u1083 \u1080  /export YYYY-MM (\u1087 \u1088 \u1080 \u1084 \u1077 \u1088 : /export 2026-01)")\
            return\
\
        start_iso, end_iso, label = parsed_range\
        user_id = m.from_user.id\
        rows = get_rows_for_export(user_id, start_iso, end_iso)\
\
        if not rows:\
            await m.answer(f"\uc0\u1053 \u1077 \u1090  \u1088 \u1072 \u1089 \u1093 \u1086 \u1076 \u1086 \u1074  \u1079 \u1072  \{label\}, \u1085 \u1077 \u1095 \u1077 \u1075 \u1086  \u1101 \u1082 \u1089 \u1087 \u1086 \u1088 \u1090 \u1080 \u1088 \u1086 \u1074 \u1072 \u1090 \u1100 .")\
            return\
\
        safe_label = label.replace(" ", "_")\
        filename = f"expenses_\{safe_label\}.csv"\
\
        with tempfile.NamedTemporaryFile("w", delete=False, newline="", encoding="utf-8", suffix=".csv") as f:\
            writer = csv.writer(f)\
            writer.writerow(["datetime", "amount", "category", "note"])\
            for created_at, amount, category, note in rows:\
                try:\
                    dt = datetime.fromisoformat(created_at).astimezone(TZ)\
                    created_at_out = dt.strftime("%Y-%m-%d %H:%M")\
                except Exception:\
                    created_at_out = created_at\
                writer.writerow([created_at_out, float(amount), category, note])\
            temp_path = f.name\
\
        await m.answer(f"\uc0\u55357 \u56548  \u1069 \u1082 \u1089 \u1087 \u1086 \u1088 \u1090  \u1079 \u1072  \{label\}:")\
        await m.answer_document(\
            types.FSInputFile(temp_path, filename=filename),\
            caption="CSV \uc0\u1092 \u1072 \u1081 \u1083  \u1089  \u1088 \u1072 \u1089 \u1093 \u1086 \u1076 \u1072 \u1084 \u1080 "\
        )\
\
    @dp.message()\
    async def any_text(m: types.Message):\
        parsed = parse_message(m.text or "")\
        if not parsed:\
            await m.answer(\
                "\uc0\u1053 \u1077  \u1087 \u1086 \u1085 \u1103 \u1083  \u1092 \u1086 \u1088 \u1084 \u1072 \u1090  \u55357 \u56837 \\n\\n"\
                "\uc0\u1055 \u1080 \u1096 \u1080  \u1090 \u1072 \u1082 : `250 \u1087 \u1088 \u1086 \u1076 \u1091 \u1082 \u1090 \u1099 ` \u1080 \u1083 \u1080  `45 \u1076 \u1086 \u1089 \u1090 \u1072 \u1074 \u1082 \u1072  \u1077 \u1076 \u1099  \u1089 \u1091 \u1096 \u1080 `\\n"\
                "\uc0\u1050 \u1086 \u1084 \u1072 \u1085 \u1076 \u1099 : /month, /month YYYY-MM, /undo, /export\\n"\
                "\uc0\u1055 \u1086 \u1076 \u1089 \u1082 \u1072 \u1079 \u1082 \u1072 : /help",\
                parse_mode="Markdown"\
            )\
            return\
\
        add_expense(m.from_user.id, parsed.amount, parsed.category, parsed.note)\
        note_part = f" \'97 _\{parsed.note\}_" if parsed.note else ""\
        await m.answer(\
            f"\uc0\u9989  \u1047 \u1072 \u1087 \u1080 \u1089 \u1072 \u1083 : *\{format_money(parsed.amount)\}* \'97 \{parsed.category\}\{note_part\}",\
            parse_mode="Markdown"\
        )\
\
    await dp.start_polling(bot)\
\
if __name__ == "__main__":\
    asyncio.run(main())}