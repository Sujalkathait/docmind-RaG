from __future__ import annotations

"""
DocMind Second Brain — SQLite Database Connection & Schema Management
Thread-safe connection provider configured with WAL mode and foreign key integrity.
"""

import os
import sqlite3
import json
from typing import Generator
from contextlib import contextmanager

DB_PATH = os.getenv("DOCMIND_DB_PATH", os.path.join("data", "docmind.db"))


def _ensure_db_dir() -> None:
    """Ensures parent directory for SQLite database exists."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """
    Creates and returns a SQLite connection configured for concurrent WAL access.
    """
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def db_session() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for transactional database operations."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initializes all database tables and indexes if they do not already exist."""
    _ensure_db_dir()
    with db_session() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Documents Master Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_path TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            folder TEXT NOT NULL DEFAULT 'General',
            file_size INTEGER NOT NULL DEFAULT 0,
            mime_type TEXT NOT NULL DEFAULT 'application/pdf',
            status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'SUPERSEDED', 'ARCHIVED', 'DELETED')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder);")

        # 3. Document Versions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_versions (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            version_number INTEGER NOT NULL DEFAULT 1,
            file_hash TEXT NOT NULL,
            change_summary TEXT,
            status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'SUPERSEDED', 'ARCHIVED')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """)

        # 4. Document Chunks Metadata Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            page_number INTEGER NOT NULL DEFAULT 1,
            section_title TEXT,
            text_content TEXT NOT NULL,
            token_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_page ON document_chunks(document_id, page_number);")

        # 5. Wiki Knowledge Nodes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL CHECK (category IN ('CONCEPT', 'TOPIC', 'ENTITY', 'DEFINITION')),
            summary TEXT NOT NULL,
            canonical_definition TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUPERSEDED', 'ARCHIVED')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_name ON knowledge_nodes(name);")

        # 6. Wiki Knowledge Relationships Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_relationships (
            id TEXT PRIMARY KEY,
            source_node_id TEXT NOT NULL,
            target_node_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (target_node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
            UNIQUE(source_node_id, target_node_id, relation_type)
        );
        """)

        # 7. Knowledge Source Attribution (Grounding)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_sources (
            id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            page_number INTEGER NOT NULL DEFAULT 1,
            snippet TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """)

        # 8. Persistent Selective Memory Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            category TEXT NOT NULL,
            memory_key TEXT NOT NULL,
            memory_value TEXT NOT NULL,
            importance_score REAL NOT NULL DEFAULT 0.5,
            project_id TEXT DEFAULT 'DEFAULT',
            last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, category, memory_key)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_user_cat ON memories(user_id, category);")

        # 9. Generated Outputs Artifacts Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS outputs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            output_type TEXT NOT NULL CHECK (output_type IN ('SUMMARY', 'STUDY_NOTES', 'REPORT', 'QUIZ', 'FLASHCARDS')),
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            content_preview TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS output_sources (
            id TEXT PRIMARY KEY,
            output_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            page_number INTEGER,
            FOREIGN KEY (output_id) REFERENCES outputs(id) ON DELETE CASCADE,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """)

        # Seed Default User
        cursor.execute("""
        INSERT OR IGNORE INTO users (id, email, display_name)
        VALUES ('default_user', 'learner@docmind.local', 'CS Learner');
        """)

        # Seed Baseline Memories if none exist
        cursor.execute("SELECT COUNT(*) as cnt FROM memories WHERE user_id = 'default_user';")
        row = cursor.fetchone()
        if row and row["cnt"] == 0:
            seed_file = os.path.join("mem", "preferences", "default.json")
            if os.path.exists(seed_file):
                try:
                    with open(seed_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for item in data.get("preferences", []):
                        m_id = f"mem_seed_{item['category']}_{item['key']}"
                        cursor.execute("""
                        INSERT OR IGNORE INTO memories (id, user_id, category, memory_key, memory_value, importance_score)
                        VALUES (?, 'default_user', ?, ?, ?, ?);
                        """, (m_id, item["category"], item["key"], item["value"], item.get("importance", 0.7)))
                except Exception:
                    pass

    print("[DocMind] SQLite Database initialized successfully.")


# Auto-initialize when module is imported
init_db()
