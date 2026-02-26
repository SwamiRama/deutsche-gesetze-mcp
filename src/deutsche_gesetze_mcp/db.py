from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import structlog

from deutsche_gesetze_mcp.models import ParsedLaw

logger = structlog.get_logger()

SCHEMA = """
CREATE TABLE IF NOT EXISTS laws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jurabk TEXT NOT NULL UNIQUE,
    full_title TEXT NOT NULL,
    slug TEXT NOT NULL,
    enactment_date TEXT NOT NULL DEFAULT '',
    norm_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS norms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id INTEGER NOT NULL REFERENCES laws(id) ON DELETE CASCADE,
    jurabk TEXT NOT NULL,
    enbez TEXT NOT NULL DEFAULT '',
    titel TEXT NOT NULL DEFAULT '',
    text_content TEXT NOT NULL DEFAULT '',
    gliederung_kennzahl TEXT NOT NULL DEFAULT '',
    gliederung_bez TEXT NOT NULL DEFAULT '',
    gliederung_titel TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_norms_law_id ON norms(law_id);
CREATE INDEX IF NOT EXISTS idx_norms_jurabk ON norms(jurabk);
CREATE INDEX IF NOT EXISTS idx_norms_enbez ON norms(jurabk, enbez);
CREATE INDEX IF NOT EXISTS idx_norms_sort ON norms(law_id, sort_order);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS norms_fts USING fts5(
    jurabk, enbez, titel, text_content,
    content='norms', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
"""

FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS norms_ai AFTER INSERT ON norms BEGIN
    INSERT INTO norms_fts(rowid, jurabk, enbez, titel, text_content)
    VALUES (new.id, new.jurabk, new.enbez, new.titel, new.text_content);
END;

CREATE TRIGGER IF NOT EXISTS norms_ad AFTER DELETE ON norms BEGIN
    INSERT INTO norms_fts(norms_fts, rowid, jurabk, enbez, titel, text_content)
    VALUES ('delete', old.id, old.jurabk, old.enbez, old.titel, old.text_content);
END;

CREATE TRIGGER IF NOT EXISTS norms_au AFTER UPDATE ON norms BEGIN
    INSERT INTO norms_fts(norms_fts, rowid, jurabk, enbez, titel, text_content)
    VALUES ('delete', old.id, old.jurabk, old.enbez, old.titel, old.text_content);
    INSERT INTO norms_fts(rowid, jurabk, enbez, titel, text_content)
    VALUES (new.id, new.jurabk, new.enbez, new.titel, new.text_content);
END;
"""

_SANITIZE_RE = re.compile(r"[^\w\sÄäÖöÜüß]", re.UNICODE)


def _sanitize_fts_query(query: str) -> str:
    cleaned = _SANITIZE_RE.sub(" ", query)
    terms = cleaned.split()
    if not terms:
        return ""
    return " ".join(f'"{t}"' for t in terms)


class Database:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            self._conn.execute("PRAGMA journal_mode=DELETE")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()
        logger.info("database_connected", path=str(self.db_path))

    def _init_schema(self) -> None:
        assert self._conn is not None
        self._conn.executescript(SCHEMA)
        self._conn.executescript(FTS_SCHEMA)
        self._conn.executescript(FTS_TRIGGERS)
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.connect()
        assert self._conn is not None
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def upsert_law(self, law: ParsedLaw) -> None:
        c = self.conn
        existing = c.execute("SELECT id FROM laws WHERE jurabk = ?", (law.jurabk,)).fetchone()

        if existing:
            law_id = existing["id"]
            c.execute(
                "UPDATE laws SET full_title=?, slug=?, enactment_date=?, norm_count=? WHERE id=?",
                (law.full_title, law.slug, law.enactment_date, len(law.norms), law_id),
            )
            c.execute("DELETE FROM norms WHERE law_id = ?", (law_id,))
        else:
            cursor = c.execute(
                "INSERT INTO laws (jurabk, full_title, slug, enactment_date, norm_count) VALUES (?, ?, ?, ?, ?)",
                (law.jurabk, law.full_title, law.slug, law.enactment_date, len(law.norms)),
            )
            law_id = cursor.lastrowid

        for norm in law.norms:
            c.execute(
                """INSERT INTO norms
                   (law_id, jurabk, enbez, titel, text_content,
                    gliederung_kennzahl, gliederung_bez, gliederung_titel, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    law_id,
                    law.jurabk,
                    norm.enbez,
                    norm.titel,
                    norm.text_content,
                    norm.gliederung_kennzahl,
                    norm.gliederung_bez,
                    norm.gliederung_titel,
                    norm.sort_order,
                ),
            )

        c.commit()

    def list_laws(self, filter_text: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        if filter_text:
            pattern = f"%{filter_text}%"
            rows = self.conn.execute(
                """SELECT jurabk, full_title, slug, norm_count FROM laws
                   WHERE jurabk LIKE ? OR full_title LIKE ?
                   ORDER BY jurabk LIMIT ? OFFSET ?""",
                (pattern, pattern, limit, offset),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT jurabk, full_title, slug, norm_count FROM laws ORDER BY jurabk LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_paragraph(self, jurabk: str, enbez: str) -> dict | None:
        row = self.conn.execute(
            """SELECT n.jurabk, n.enbez, n.titel, n.text_content,
                      n.gliederung_kennzahl, n.gliederung_bez, n.gliederung_titel
               FROM norms n
               WHERE n.jurabk = ? AND n.enbez = ?""",
            (jurabk, enbez),
        ).fetchone()
        return dict(row) if row else None

    def get_paragraphs_range(self, jurabk: str, start_enbez: str, end_enbez: str, max_results: int = 50) -> list[dict]:
        start_row = self.conn.execute(
            "SELECT sort_order FROM norms WHERE jurabk = ? AND enbez = ?",
            (jurabk, start_enbez),
        ).fetchone()
        end_row = self.conn.execute(
            "SELECT sort_order FROM norms WHERE jurabk = ? AND enbez = ?",
            (jurabk, end_enbez),
        ).fetchone()

        if not start_row or not end_row:
            return []

        rows = self.conn.execute(
            """SELECT jurabk, enbez, titel, text_content,
                      gliederung_kennzahl, gliederung_bez, gliederung_titel
               FROM norms
               WHERE jurabk = ? AND sort_order BETWEEN ? AND ?
               ORDER BY sort_order
               LIMIT ?""",
            (jurabk, start_row["sort_order"], end_row["sort_order"], max_results),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_law_structure(self, jurabk: str) -> list[dict]:
        rows = self.conn.execute(
            """SELECT enbez, titel, gliederung_kennzahl, gliederung_bez, gliederung_titel
               FROM norms
               WHERE jurabk = ?
               ORDER BY sort_order""",
            (jurabk,),
        ).fetchall()
        return [dict(r) for r in rows]

    def search(
        self,
        query: str,
        laws: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        sanitized = _sanitize_fts_query(query)
        if not sanitized:
            return []

        if laws:
            placeholders = ",".join("?" for _ in laws)
            sql = f"""
                SELECT n.jurabk, n.enbez, n.titel,
                       snippet(norms_fts, 3, '>>>', '<<<', '...', 64) AS snippet,
                       rank
                FROM norms_fts
                JOIN norms n ON norms_fts.rowid = n.id
                WHERE norms_fts MATCH ?
                  AND n.jurabk IN ({placeholders})
                ORDER BY rank
                LIMIT ? OFFSET ?
            """
            params: list = [sanitized, *laws, limit, offset]
        else:
            sql = """
                SELECT n.jurabk, n.enbez, n.titel,
                       snippet(norms_fts, 3, '>>>', '<<<', '...', 64) AS snippet,
                       rank
                FROM norms_fts
                JOIN norms n ON norms_fts.rowid = n.id
                WHERE norms_fts MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
            """
            params = [sanitized, limit, offset]

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_law_metadata(self, jurabk: str) -> dict | None:
        row = self.conn.execute(
            "SELECT jurabk, full_title, slug, enactment_date, norm_count FROM laws WHERE jurabk = ?",
            (jurabk,),
        ).fetchone()
        return dict(row) if row else None

    def get_stats(self) -> dict:
        law_count = self.conn.execute("SELECT COUNT(*) as c FROM laws").fetchone()
        norm_count = self.conn.execute("SELECT COUNT(*) as c FROM norms").fetchone()
        return {
            "law_count": law_count["c"] if law_count else 0,
            "norm_count": norm_count["c"] if norm_count else 0,
        }
