from __future__ import annotations

import os
import shutil
from typing import Any, Optional, Union, List, Dict
import chromadb

from config import CHROMA_PATH, COLLECTION_NAME, PDF_FOLDER, TOP_K

DEFAULT_FOLDER = "General"

# Singleton ChromaDB client & collection instances
_client: Any = None
_collection: Any = None
_doc_count_cached: int | None = None
_retrieval_cache: dict[tuple, dict] = {}
_folder_stats_cached: list[dict] | None = None
_folder_docs_cached: dict[str | None, list[dict]] = {}


def _get_client():
    """Returns a singleton ChromaDB PersistentClient with retry."""
    global _client
    if _client is not None:
        return _client

    last_err = None
    for attempt in range(3):
        try:
            _client = chromadb.PersistentClient(path=CHROMA_PATH)
            return _client
        except (AttributeError, ValueError) as e:
            last_err = e
            import time
            time.sleep(0.3)

    raise RuntimeError(f"ChromaDB failed to initialize after 3 attempts: {last_err}")


def get_collection():
    """Gets or returns cached main collection instance."""
    global _collection
    if _collection is not None:
        return _collection
    client = _get_client()
    _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def _invalidate_caches():
    """Invalidates memory caches when documents or collections are modified."""
    global _doc_count_cached, _retrieval_cache, _folder_stats_cached, _folder_docs_cached
    _doc_count_cached = None
    _retrieval_cache.clear()
    _folder_stats_cached = None
    _folder_docs_cached.clear()


def sanitize_folder_name(name: Any) -> str:
    """Sanitizes folder names for safe filesystem and metadata usage."""
    if name is None:
        return DEFAULT_FOLDER
    raw_str = str(name).strip()
    if not raw_str:
        return DEFAULT_FOLDER
    sanitized = "".join(
        c for c in raw_str if c.isalnum() or c in (" ", "_", "-", "+")
    ).strip()
    return sanitized if sanitized else DEFAULT_FOLDER


# ===========================
# Indexing Operations
# ===========================


def add_document(
    chunks: list[str],
    embeddings: list[list[float]],
    filename: str,
    folder: str = DEFAULT_FOLDER,
) -> int:
    """
    Adds document chunks + embeddings to ChromaDB with folder metadata.
    Replaces existing chunks for the same file + folder.
    Batches chunk insertions to prevent batch limit exceptions.
    Returns the number of chunks added.
    """
    if not chunks:
        return 0

    collection = get_collection()
    clean_folder = sanitize_folder_name(folder)
    safe_filename = os.path.basename(filename)

    # Delete existing chunks for this file + folder (re-index support)
    try:
        collection.delete(
            where={"$and": [{"source": safe_filename}, {"folder": clean_folder}]}
        )
    except Exception:
        pass

    chunk_ids = [
        f"{clean_folder}_{safe_filename}_chunk_{i}" for i in range(len(chunks))
    ]
    metadatas = [
        {"source": safe_filename, "folder": clean_folder, "chunk_index": i}
        for i in range(len(chunks))
    ]

    # Ingest in safe batches of 500 chunks
    batch_size = 500
    for start_idx in range(0, len(chunks), batch_size):
        end_idx = start_idx + batch_size
        collection.add(
            ids=chunk_ids[start_idx:end_idx],
            documents=chunks[start_idx:end_idx],
            embeddings=embeddings[start_idx:end_idx],
            metadatas=metadatas[start_idx:end_idx],
        )

    _invalidate_caches()
    return len(chunks)


# ===========================
# Query Operations
# ===========================


def query(
    query_embedding: list[float],
    top_k: int = TOP_K,
    folder: str | list[str] | None = None,
) -> dict:
    """
    Queries ChromaDB with folder-scoped filtering and in-memory result caching.
    Supports single folder ("OS"), multiple folders (["OS", "DBMS"]), or None/All.
    Returns dict with 'chunks', 'metadatas', 'distances'.
    """
    collection = get_collection()
    total_count = get_document_count()

    if total_count == 0:
        return {"chunks": [], "metadatas": [], "distances": []}

    # Normalize folder key for caching
    if isinstance(folder, list):
        folder_key = tuple(sorted(folder))
    elif isinstance(folder, str):
        folder_key = (folder,)
    else:
        folder_key = None

    # Fast hash representation of query embedding for cache lookup
    cache_key = (tuple(query_embedding[:8]), len(query_embedding), top_k, folder_key)
    if cache_key in _retrieval_cache:
        return _retrieval_cache[cache_key]

    # Resolve folder filter
    where_filter = _build_folder_filter(folder)

    n_results = min(top_k, total_count)
    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
    }
    if where_filter:
        query_params["where"] = where_filter

    results = collection.query(**query_params)

    chunks = results["documents"][0] if results.get("documents") else []
    metadatas = results["metadatas"][0] if results.get("metadatas") else []
    distances = results["distances"][0] if results.get("distances") else []

    out = {"chunks": chunks, "metadatas": metadatas, "distances": distances}
    
    # Cache up to 128 recent queries
    if len(_retrieval_cache) > 128:
        _retrieval_cache.pop(next(iter(_retrieval_cache)))
    _retrieval_cache[cache_key] = out

    return out


def _build_folder_filter(folder: str | list[str] | None, collection: Any = None) -> dict | None:
    """Builds an optimized ChromaDB where-filter from folder specification using $in."""
    if folder is None:
        return None

    if isinstance(folder, str):
        if folder.strip().lower() in ("all", "*", ""):
            return None
        folders = [f.strip() for f in folder.split(",") if f.strip()]
    else:
        folders = [str(f).strip() for f in folder if str(f).strip()]

    # Remove "all"/"*" entries
    folders = [f for f in folders if f.lower() not in ("all", "*")]

    if not folders:
        return None
    elif len(folders) == 1:
        return {"folder": folders[0]}
    else:
        return {"folder": {"$in": folders}}


# ===========================
# Folder Management
# ===========================


def get_all_folders() -> list[dict]:
    """Returns all folders with cached document and chunk counts for high UI speed."""
    global _folder_stats_cached
    if _folder_stats_cached is not None:
        return _folder_stats_cached

    os.makedirs(PDF_FOLDER, exist_ok=True)
    folder_set = {DEFAULT_FOLDER}

    # Scan directories on disk
    for item in os.listdir(PDF_FOLDER):
        if os.path.isdir(os.path.join(PDF_FOLDER, item)):
            folder_set.add(item)

    collection = get_collection()
    folder_stats = {
        f: {"name": f, "document_count": 0, "chunk_count": 0} for f in folder_set
    }

    try:
        if get_document_count() > 0:
            results = collection.get(include=["metadatas"])
            metadatas = results.get("metadatas", []) or []

            doc_tracker: dict[str, set] = {}
            for meta in metadatas:
                if not meta:
                    continue
                f_name = meta.get("folder", DEFAULT_FOLDER)
                src = meta.get("source", "Unknown")

                if f_name not in folder_stats:
                    folder_stats[f_name] = {
                        "name": f_name,
                        "document_count": 0,
                        "chunk_count": 0,
                    }

                folder_stats[f_name]["chunk_count"] += 1

                if f_name not in doc_tracker:
                    doc_tracker[f_name] = set()
                doc_tracker[f_name].add(src)

            for f_name, docs in doc_tracker.items():
                if f_name in folder_stats:
                    folder_stats[f_name]["document_count"] = len(docs)
    except Exception as e:
        print(f"Error reading ChromaDB folder stats: {e}")

    _folder_stats_cached = sorted(
        list(folder_stats.values()),
        key=lambda x: (x["name"] != DEFAULT_FOLDER, x["name"].lower()),
    )
    return _folder_stats_cached


def get_folder_documents(folder_name: str | None = None) -> list[dict]:
    """
    Returns a detailed cached list of all documents (indexed and unindexed)
    for a specific folder or all folders.
    """
    global _folder_docs_cached
    clean_target = (
        sanitize_folder_name(folder_name)
        if folder_name and str(folder_name).lower() != "all"
        else None
    )

    if clean_target in _folder_docs_cached:
        return _folder_docs_cached[clean_target]

    collection = get_collection()
    docs_map: dict[tuple[str, str], dict] = {}

    # 1. Gather indexed documents from ChromaDB
    try:
        if get_document_count() > 0:
            if clean_target:
                results = collection.get(
                    where={"folder": clean_target}, include=["metadatas"]
                )
            else:
                results = collection.get(include=["metadatas"])

            metadatas = results.get("metadatas", []) or []
            for meta in metadatas:
                if not meta:
                    continue
                f = meta.get("folder", DEFAULT_FOLDER)
                src = meta.get("source", "Unknown")
                key = (f, src)
                if key not in docs_map:
                    docs_map[key] = {
                        "filename": src,
                        "folder": f,
                        "chunk_count": 0,
                        "file_size": "--",
                    }
                docs_map[key]["chunk_count"] += 1
    except Exception as e:
        print(f"Error fetching ChromaDB documents: {e}")

    # 2. Enrich with filesystem files
    os.makedirs(PDF_FOLDER, exist_ok=True)
    all_folders = [f["name"] for f in get_all_folders()]
    if clean_target and clean_target not in all_folders:
        all_folders.append(clean_target)

    for f_name in all_folders:
        if clean_target and f_name != clean_target:
            continue
        folder_dir = os.path.join(PDF_FOLDER, f_name)
        search_dirs = [folder_dir]
        if f_name == DEFAULT_FOLDER:
            search_dirs.append(PDF_FOLDER)

        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            for item in os.listdir(s_dir):
                if item.lower().endswith(".pdf") and os.path.isfile(
                    os.path.join(s_dir, item)
                ):
                    key = (f_name, item)
                    file_path = os.path.join(s_dir, item)
                    try:
                        size_bytes = os.path.getsize(file_path)
                        if size_bytes < 1024:
                            size_str = f"{size_bytes} B"
                        elif size_bytes < 1024 * 1024:
                            size_str = f"{size_bytes / 1024:.1f} KB"
                        else:
                            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                    except Exception:
                        size_str = "--"

                    if key not in docs_map:
                        docs_map[key] = {
                            "filename": item,
                            "folder": f_name,
                            "chunk_count": 0,
                            "file_size": size_str,
                        }
                    else:
                        docs_map[key]["file_size"] = size_str

    doc_list = list(docs_map.values())
    doc_list.sort(key=lambda d: (d["folder"].lower(), d["filename"].lower()))
    _folder_docs_cached[clean_target] = doc_list
    return doc_list



def create_folder(folder_name: str) -> dict:
    """Creates a new folder directory under pdfs/."""
    clean_name = sanitize_folder_name(folder_name)
    os.makedirs(os.path.join(PDF_FOLDER, clean_name), exist_ok=True)
    _invalidate_caches()
    return {"success": True, "folder": clean_name}


def delete_folder(folder_name: str) -> dict:
    """Deletes folder chunks from ChromaDB and removes directory from disk."""
    clean_name = sanitize_folder_name(folder_name)
    collection = get_collection()

    try:
        collection.delete(where={"folder": clean_name})
    except Exception as e:
        print(f"Warning deleting folder '{clean_name}' from ChromaDB: {e}")

    folder_path = os.path.join(PDF_FOLDER, clean_name)
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            print(f"Warning removing directory '{folder_path}': {e}")

    _invalidate_caches()
    return {"success": True, "folder": clean_name}


def delete_document(filename: str, folder: str = None) -> dict:
    """Deletes a document's chunks from ChromaDB and the file from disk."""
    safe_filename = os.path.basename(filename)
    clean_folder = sanitize_folder_name(folder) if folder else None
    collection = get_collection()

    try:
        if clean_folder:
            collection.delete(
                where={"$and": [{"source": safe_filename}, {"folder": clean_folder}]}
            )
        else:
            collection.delete(where={"source": safe_filename})
    except Exception as e:
        print(f"Warning deleting '{safe_filename}' from ChromaDB: {e}")

    # Delete physical file
    target_dir = os.path.join(PDF_FOLDER, clean_folder) if clean_folder else PDF_FOLDER
    file_path = os.path.join(target_dir, safe_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    _invalidate_caches()
    return {"success": True, "filename": safe_filename}


def clear_all() -> dict:
    """Clears all documents from ChromaDB and the pdfs/ directory."""
    global _client, _collection
    client = _get_client()

    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    _collection = None
    _client = None
    client = _get_client()
    _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    _invalidate_caches()

    if os.path.exists(PDF_FOLDER):
        for root, dirs, files in os.walk(PDF_FOLDER, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except Exception:
                    pass

    os.makedirs(os.path.join(PDF_FOLDER, DEFAULT_FOLDER), exist_ok=True)
    return {"success": True, "message": "All documents and folders cleared."}


def get_document_count() -> int:
    """Returns the cached or queried total number of chunks in the collection."""
    global _doc_count_cached
    if _doc_count_cached is not None:
        return _doc_count_cached
    try:
        _doc_count_cached = get_collection().count()
        return _doc_count_cached
    except Exception:
        return 0
