# --!-- coding: utf8 --!--
"""Chat history stored server-side (SQLite) per user, grouped by project.

Manuskript may delete and rewrite a project folder when saving, so chats
live in the app data directory and are tagged with the project path.
"""

import os
import time
import uuid
import sqlite3
from pathlib import Path


def _norm_project(project: str | None) -> str:
    if not project:
        return ""
    s = str(project).strip().rstrip("/\\")
    if not s:
        return ""
    p = Path(s)
    if p.name.upper() == "MANUSKRIPT":
        p = p.parent
    return p.stem if p.suffix.lower() == ".msk" else p.name


class ChatStore:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.folder / "chats.db"))
        self._init_db()

    def _init_db(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                project TEXT NOT NULL,
                created REAL NOT NULL,
                updated REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                agent TEXT,
                created REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id);
            CREATE INDEX IF NOT EXISTS idx_chats_project ON chats(project);
            CREATE INDEX IF NOT EXISTS idx_chats_updated ON chats(updated DESC);
        """)
        self.db.commit()

    @staticmethod
    def new_id():
        return uuid.uuid4().hex[:12]

    @staticmethod
    def make_title(agent, first_prompt):
        words = " ".join((first_prompt or "").split())
        if len(words) > 40:
            words = words[:40].rstrip() + "..."
        return "%s: %s" % (agent, words or "New chat")

    def save(self, chat):
        """chat: dict with id, title, project, messages.
        messages: list of {role, content, agent}"""
        now = time.time()
        chat["updated"] = now
        chat.setdefault("created", now)
        proj = _norm_project(chat.get("project", ""))
        self.db.execute("""
            INSERT OR REPLACE INTO chats (id, title, project, created, updated)
            VALUES (?, ?, ?, ?, ?)
        """, (chat["id"], chat["title"], proj,
              chat["created"], chat["updated"]))
        # Delete old messages and insert fresh
        self.db.execute("DELETE FROM messages WHERE chat_id = ?", (chat["id"],))
        for msg in chat.get("messages", []):
            self.db.execute("""
                INSERT INTO messages (chat_id, role, content, agent, created)
                VALUES (?, ?, ?, ?, ?)
            """, (chat["id"], msg["role"], msg["content"],
                  msg.get("agent"), msg.get("created", now)))
        self.db.commit()

    def load(self, chat_id):
        row = self.db.execute(
            "SELECT id, title, project, created, updated FROM chats WHERE id = ?",
            (chat_id,)).fetchone()
        if not row:
            return None
        messages = self.db.execute(
            "SELECT role, content, agent, created FROM messages"
            " WHERE chat_id = ? ORDER BY rowid",
            (chat_id,)).fetchall()
        return {
            "id": row[0], "title": row[1], "project": row[2],
            "created": row[3], "updated": row[4],
            "messages": [
                {"role": r[0], "content": r[1], "agent": r[2], "created": r[3]}
                for r in messages
            ]
        }

    def delete(self, chat_id):
        self.db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        self.db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        self.db.commit()

    def rename(self, chat_id, new_title):
        """Rename a chat."""
        now = time.time()
        self.db.execute(
            "UPDATE chats SET title = ?, updated = ? WHERE id = ?",
            (new_title, now, chat_id))
        self.db.commit()

    def list_chats(self, project=None):
        """Newest first. If project is given, only that project's chats."""
        norm = _norm_project(project) if project else None
        rows = self.db.execute(
            "SELECT id, title, project, created, updated"
            " FROM chats ORDER BY updated DESC"
        ).fetchall()
        out = []
        for r in rows:
            r_proj = _norm_project(r[2])
            if norm and r_proj != norm:
                continue
            out.append({
                "id": r[0], "title": r[1], "project": r_proj,
                "created": r[3], "updated": r[4]
            })
        return out

    def add_message(self, chat_id, role, content, agent=None):
        """Add a single message to a chat, updating the chat's updated time."""
        now = time.time()
        self.db.execute("""
            INSERT INTO messages (chat_id, role, content, agent, created)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, role, content, agent, now))
        self.db.execute(
            "UPDATE chats SET updated = ? WHERE id = ?", (now, chat_id))
        self.db.commit()
        return now

    def close(self):
        self.db.close()
