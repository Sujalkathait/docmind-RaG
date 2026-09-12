from __future__ import annotations

"""
DocMind Second Brain — Database CRUD Operations
High-performance data access layer for documents, chunks, wiki graph, memories, and outputs.
"""

import uuid
import time
from typing import List, Dict, Optional, Any
from backend.database.connection import db_session
from backend.database.models import (
    DocumentModel,
    DocumentChunkModel,
    KnowledgeNodeModel,
    KnowledgeRelationshipModel,
    KnowledgeSourceModel,
    MemoryModel,
    OutputArtifactModel,
)


# ====================================================
# 1. Document CRUD
# ====================================================

def create_document(
    doc_id: str,
    filename: str,
    original_path: str,
    file_hash: str,
    folder: str = "General",
    file_size: int = 0,
    mime_type: str = "application/pdf",
    user_id: str = "default_user",
) -> DocumentModel:
    """Registers a new uploaded document in SQLite."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO documents (id, user_id, filename, original_path, file_hash, folder, file_size, mime_type, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        ON CONFLICT(id) DO UPDATE SET
            filename = excluded.filename,
            original_path = excluded.original_path,
            file_hash = excluded.file_hash,
            folder = excluded.folder,
            file_size = excluded.file_size,
            status = 'ACTIVE';
        """, (doc_id, user_id, filename, original_path, file_hash, folder, file_size, mime_type))

    return get_document_by_id(doc_id)  # type: ignore


def get_document_by_id(doc_id: str) -> Optional[DocumentModel]:
    """Retrieves document record by document ID."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT d.*, COUNT(c.id) as chunk_count
        FROM documents d
        LEFT JOIN document_chunks c ON d.id = c.document_id
        WHERE d.id = ?
        GROUP BY d.id;
        """, (doc_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return DocumentModel(
            id=row["id"],
            user_id=row["user_id"],
            filename=row["filename"],
            original_path=row["original_path"],
            file_hash=row["file_hash"],
            folder=row["folder"],
            file_size=row["file_size"],
            mime_type=row["mime_type"],
            status=row["status"],
            chunk_count=row["chunk_count"],
            created_at=str(row["created_at"]),
        )


def get_document_by_hash(file_hash: str) -> Optional[DocumentModel]:
    """Finds document by SHA-256 hash."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE file_hash = ? AND status = 'ACTIVE' LIMIT 1;", (file_hash,))
        row = cursor.fetchone()
        if row:
            return get_document_by_id(row["id"])
    return None


def list_documents(user_id: str = "default_user", folder: Optional[str] = None) -> List[DocumentModel]:
    """Lists all active documents, optionally filtered by folder."""
    with db_session() as conn:
        cursor = conn.cursor()
        if folder and folder.lower() not in ("all", "*", ""):
            cursor.execute("""
            SELECT d.*, COUNT(c.id) as chunk_count
            FROM documents d
            LEFT JOIN document_chunks c ON d.id = c.document_id
            WHERE d.user_id = ? AND d.folder = ? AND d.status != 'DELETED'
            GROUP BY d.id
            ORDER BY d.created_at DESC;
            """, (user_id, folder))
        else:
            cursor.execute("""
            SELECT d.*, COUNT(c.id) as chunk_count
            FROM documents d
            LEFT JOIN document_chunks c ON d.id = c.document_id
            WHERE d.user_id = ? AND d.status != 'DELETED'
            GROUP BY d.id
            ORDER BY d.created_at DESC;
            """, (user_id,))

        rows = cursor.fetchall()
        return [
            DocumentModel(
                id=r["id"],
                user_id=r["user_id"],
                filename=r["filename"],
                original_path=r["original_path"],
                file_hash=r["file_hash"],
                folder=r["folder"],
                file_size=r["file_size"],
                mime_type=r["mime_type"],
                status=r["status"],
                chunk_count=r["chunk_count"],
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]


def delete_document(doc_id: str) -> bool:
    """Cascade deletes a document and associated chunks/knowledge sources from SQLite."""
    with db_session() as conn:
        cursor = conn.cursor()
        # Delete related sources and chunks
        cursor.execute("DELETE FROM knowledge_sources WHERE document_id = ?;", (doc_id,))
        cursor.execute("DELETE FROM document_chunks WHERE document_id = ?;", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = ?;", (doc_id,))
        return cursor.rowcount > 0


def list_folders(user_id: str = "default_user") -> List[str]:
    """Retrieves all distinct folders across indexed documents and disk directories."""
    import os
    folders = {"General"}
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT folder FROM documents WHERE folder IS NOT NULL AND status != 'DELETED';")
        for row in cursor.fetchall():
            if row["folder"]:
                folders.add(row["folder"])

    try:
        from config import PDF_FOLDER
    except ImportError:
        PDF_FOLDER = os.path.join("raw", "pdfs")

    if os.path.exists(PDF_FOLDER):
        for entry in os.listdir(PDF_FOLDER):
            if os.path.isdir(os.path.join(PDF_FOLDER, entry)):
                folders.add(entry)

    return sorted(list(folders))


# ====================================================
# 2. Document Chunks CRUD
# ====================================================

def add_document_chunks(
    document_id: str,
    chunks: List[str],
    page_numbers: Optional[List[int]] = None,
    section_titles: Optional[List[str]] = None,
) -> int:
    """Inserts batch of text chunks into SQLite."""
    if not chunks:
        return 0

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM document_chunks WHERE document_id = ?;", (document_id,))
        
        insert_data = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chk_{i:04d}"
            pg = page_numbers[i] if page_numbers and i < len(page_numbers) else 1
            sec = section_titles[i] if section_titles and i < len(section_titles) else None
            tok_est = len(chunk) // 4
            insert_data.append((chunk_id, document_id, i, pg, sec, chunk, tok_est))

        cursor.executemany("""
        INSERT INTO document_chunks (id, document_id, chunk_index, page_number, section_title, text_content, token_count)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, insert_data)

    return len(chunks)


def get_chunks_for_document(document_id: str) -> List[DocumentChunkModel]:
    """Retrieves all indexed chunks for a given document."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM document_chunks
        WHERE document_id = ?
        ORDER BY chunk_index ASC;
        """, (document_id,))
        rows = cursor.fetchall()
        return [
            DocumentChunkModel(
                id=r["id"],
                document_id=r["document_id"],
                chunk_index=r["chunk_index"],
                page_number=r["page_number"],
                section_title=r["section_title"],
                text_content=r["text_content"],
                token_count=r["token_count"],
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]


# ====================================================
# 3. Wiki Knowledge Nodes & Graph CRUD
# ====================================================

def upsert_knowledge_node(
    name: str,
    category: str = "CONCEPT",
    summary: str = "",
    canonical_definition: Optional[str] = None,
) -> KnowledgeNodeModel:
    """Creates or updates a structured concept node in the Wiki."""
    node_id = f"kn_{name.lower().replace(' ', '_').replace('-', '_')[:48]}"
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO knowledge_nodes (id, name, category, summary, canonical_definition, status, updated_at)
        VALUES (?, ?, ?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP)
        ON CONFLICT(name) DO UPDATE SET
            category = excluded.category,
            summary = CASE WHEN length(excluded.summary) > length(knowledge_nodes.summary) THEN excluded.summary ELSE knowledge_nodes.summary END,
            canonical_definition = COALESCE(excluded.canonical_definition, knowledge_nodes.canonical_definition),
            status = 'ACTIVE',
            updated_at = CURRENT_TIMESTAMP;
        """, (node_id, name.strip(), category, summary.strip(), canonical_definition))

    return get_knowledge_node(node_id)  # type: ignore


def get_knowledge_node(node_id_or_name: str) -> Optional[KnowledgeNodeModel]:
    """Fetches knowledge node by ID or by exact name."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM knowledge_nodes
        WHERE id = ? OR LOWER(name) = LOWER(?)
        LIMIT 1;
        """, (node_id_or_name, node_id_or_name))
        row = cursor.fetchone()
        if not row:
            return None
        return KnowledgeNodeModel(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            summary=row["summary"],
            canonical_definition=row["canonical_definition"],
            status=row["status"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )


def list_knowledge_nodes(category: Optional[str] = None, query: Optional[str] = None) -> List[KnowledgeNodeModel]:
    """Queries knowledge nodes with optional category or text search."""
    with db_session() as conn:
        cursor = conn.cursor()
        sql = "SELECT * FROM knowledge_nodes WHERE status = 'ACTIVE'"
        params: list = []

        if category and category != "ALL":
            sql += " AND category = ?"
            params.append(category)

        if query:
            sql += " AND (name LIKE ? OR summary LIKE ? OR canonical_definition LIKE ?)"
            like_str = f"%{query}%"
            params.extend([like_str, like_str, like_str])

        sql += " ORDER BY name ASC;"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [
            KnowledgeNodeModel(
                id=r["id"],
                name=r["name"],
                category=r["category"],
                summary=r["summary"],
                canonical_definition=r["canonical_definition"],
                status=r["status"],
                created_at=str(r["created_at"]),
                updated_at=str(r["updated_at"]),
            )
            for r in rows
        ]


def add_knowledge_relationship(
    source_node_id: str,
    target_node_id: str,
    relation_type: str = "RELATES_TO",
    confidence: float = 1.0,
    description: Optional[str] = None,
) -> bool:
    """Adds a directed or bi-directional relationship between two knowledge nodes."""
    if source_node_id == target_node_id:
        return False
    rel_id = f"rel_{source_node_id}_{target_node_id}_{relation_type[:6]}"
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO knowledge_relationships (id, source_node_id, target_node_id, relation_type, confidence, description)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_node_id, target_node_id, relation_type) DO UPDATE SET
            confidence = excluded.confidence,
            description = COALESCE(excluded.description, knowledge_relationships.description);
        """, (rel_id, source_node_id, target_node_id, relation_type, confidence, description))
        return True


def get_node_relationships(node_id: str) -> List[KnowledgeRelationshipModel]:
    """Retrieves all incoming and outgoing connections for a given knowledge node."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT r.*, s.name as source_name, t.name as target_name
        FROM knowledge_relationships r
        JOIN knowledge_nodes s ON r.source_node_id = s.id
        JOIN knowledge_nodes t ON r.target_node_id = t.id
        WHERE r.source_node_id = ? OR r.target_node_id = ?;
        """, (node_id, node_id))
        rows = cursor.fetchall()
        return [
            KnowledgeRelationshipModel(
                id=r["id"],
                source_node_id=r["source_node_id"],
                target_node_id=r["target_node_id"],
                relation_type=r["relation_type"],
                confidence=r["confidence"],
                description=r["description"],
                source_name=r["source_name"],
                target_name=r["target_name"],
            )
            for r in rows
        ]


def link_knowledge_source(
    node_id: str,
    document_id: str,
    page_number: int = 1,
    snippet: str = "",
) -> bool:
    """Anchors a knowledge node to exact page evidence in a document."""
    src_id = f"src_{node_id[:16]}_{document_id[:16]}_p{page_number}"
    with db_session() as conn:
        cursor = conn.cursor()
        # Ensure document exists to satisfy foreign key constraint
        cursor.execute("SELECT id FROM documents WHERE id = ?;", (document_id,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT OR IGNORE INTO documents (id, user_id, filename, original_path, file_hash, folder, status)
            VALUES (?, 'default_user', 'AutoReferenceDoc', '', ?, 'General', 'ACTIVE');
            """, (document_id, document_id))

        cursor.execute("""
        INSERT OR REPLACE INTO knowledge_sources (id, node_id, document_id, page_number, snippet)
        VALUES (?, ?, ?, ?, ?);
        """, (src_id, node_id, document_id, page_number, snippet[:400]))
        return True



def get_sources_for_node(node_id: str) -> List[KnowledgeSourceModel]:
    """Returns all document evidence anchoring a given concept."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT ks.*, d.filename as document_name
        FROM knowledge_sources ks
        JOIN documents d ON ks.document_id = d.id
        WHERE ks.node_id = ?;
        """, (node_id,))
        rows = cursor.fetchall()
        return [
            KnowledgeSourceModel(
                id=r["id"],
                node_id=r["node_id"],
                document_id=r["document_id"],
                document_name=r["document_name"],
                page_number=r["page_number"],
                snippet=r["snippet"],
            )
            for r in rows
        ]


# ====================================================
# 4. Persistent Memory CRUD
# ====================================================

def upsert_memory(
    user_id: str,
    category: str,
    key: str,
    value: str,
    importance_score: float = 0.5,
    project_id: str = "DEFAULT",
) -> MemoryModel:
    """Saves or updates a selective memory record."""
    mem_id = f"mem_{user_id}_{category[:4]}_{key.lower().replace(' ', '_')[:32]}"
    with db_session() as conn:
        cursor = conn.cursor()
        # Ensure user exists to satisfy foreign key constraint
        cursor.execute("""
        INSERT OR IGNORE INTO users (id, email, display_name)
        VALUES (?, ? || '@docmind.local', ?);
        """, (user_id, user_id, user_id))

        cursor.execute("""
        INSERT INTO memories (id, user_id, category, memory_key, memory_value, importance_score, project_id, last_accessed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, category, memory_key) DO UPDATE SET
            memory_value = excluded.memory_value,
            importance_score = excluded.importance_score,
            project_id = excluded.project_id,
            last_accessed_at = CURRENT_TIMESTAMP;
        """, (mem_id, user_id, category, key.strip(), value.strip(), importance_score, project_id))

    return get_memory(mem_id)  # type: ignore


def get_memory(memory_id: str) -> Optional[MemoryModel]:
    """Retrieves a single memory by ID."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE id = ?;", (memory_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return MemoryModel(
            id=row["id"],
            user_id=row["user_id"],
            category=row["category"],
            memory_key=row["memory_key"],
            memory_value=row["memory_value"],
            importance_score=row["importance_score"],
            project_id=row["project_id"],
            last_accessed_at=str(row["last_accessed_at"]),
            created_at=str(row["created_at"]),
        )


def list_memories(user_id: str = "default_user", category: Optional[str] = None) -> List[MemoryModel]:
    """Lists persistent memories for user, optionally filtered by category."""
    with db_session() as conn:
        cursor = conn.cursor()
        if category and category != "ALL":
            cursor.execute("""
            SELECT * FROM memories
            WHERE user_id = ? AND category = ?
            ORDER BY importance_score DESC, last_accessed_at DESC;
            """, (user_id, category))
        else:
            cursor.execute("""
            SELECT * FROM memories
            WHERE user_id = ?
            ORDER BY importance_score DESC, last_accessed_at DESC;
            """, (user_id,))

        rows = cursor.fetchall()
        return [
            MemoryModel(
                id=r["id"],
                user_id=r["user_id"],
                category=r["category"],
                memory_key=r["memory_key"],
                memory_value=r["memory_value"],
                importance_score=r["importance_score"],
                project_id=r["project_id"],
                last_accessed_at=str(r["last_accessed_at"]),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]


def touch_memory_accessed(memory_id: str) -> None:
    """Updates the last_accessed_at timestamp for recency calculation."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE memories SET last_accessed_at = CURRENT_TIMESTAMP WHERE id = ?;", (memory_id,))


def delete_memory(memory_id: str) -> bool:
    """Deletes a memory record."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?;", (memory_id,))
        return cursor.rowcount > 0


def clear_all_memories(user_id: str = "default_user") -> int:
    """Wipes all persistent memories for user."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE user_id = ?;", (user_id,))
        return cursor.rowcount


# ====================================================
# 5. Output Deliverables CRUD
# ====================================================

def create_output_artifact(
    user_id: str,
    output_type: str,
    title: str,
    file_path: str,
    content_preview: Optional[str] = None,
    source_doc_ids: Optional[List[str]] = None,
) -> OutputArtifactModel:
    """Records a generated study artifact (note/report/quiz) in SQLite."""
    out_id = f"out_{uuid.uuid4().hex[:12]}"
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO outputs (id, user_id, output_type, title, file_path, content_preview)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (out_id, user_id, output_type, title, file_path, (content_preview or "")[:500]))

        if source_doc_ids:
            for d_id in source_doc_ids:
                s_id = f"os_{out_id}_{d_id[:8]}"
                cursor.execute("""
                INSERT OR IGNORE INTO output_sources (id, output_id, document_id)
                VALUES (?, ?, ?);
                """, (s_id, out_id, d_id))

    return OutputArtifactModel(
        id=out_id,
        user_id=user_id,
        output_type=output_type,
        title=title,
        file_path=file_path,
        content_preview=content_preview,
        created_at=str(time.time()),
    )


def list_outputs(user_id: str = "default_user", output_type: Optional[str] = None) -> List[OutputArtifactModel]:
    """Lists saved artifacts."""
    with db_session() as conn:
        cursor = conn.cursor()
        if output_type and output_type != "ALL":
            cursor.execute("""
            SELECT * FROM outputs
            WHERE user_id = ? AND output_type = ?
            ORDER BY created_at DESC;
            """, (user_id, output_type))
        else:
            cursor.execute("""
            SELECT * FROM outputs
            WHERE user_id = ?
            ORDER BY created_at DESC;
            """, (user_id,))

        rows = cursor.fetchall()
        return [
            OutputArtifactModel(
                id=r["id"],
                user_id=r["user_id"],
                output_type=r["output_type"],
                title=r["title"],
                file_path=r["file_path"],
                content_preview=r["content_preview"],
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]
