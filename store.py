"""
Local memory store: raw files + ChromaDB vector index.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

MEMORIES_DIR = Path("memories")
CHROMA_DIR = Path(".chroma")
COLLECTION_NAME = "memories"
EMBED_MODEL = "all-MiniLM-L6-v2"

_embedder: Optional[SentenceTransformer] = None
_client: Optional[chromadb.Client] = None
_collection = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def _get_collection():
    global _client, _collection
    if _collection is None:
        CHROMA_DIR.mkdir(exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_memory(
    content: str,
    title: str,
    memory_type: str,
    date: Optional[str] = None,
    tags: Optional[list[str]] = None,
    source_path: Optional[Path] = None,
) -> str:
    """Store a memory: save raw file + embed into vector DB. Returns memory ID."""
    MEMORIES_DIR.mkdir(exist_ok=True)

    date = date or datetime.now().strftime("%Y-%m-%d")
    tags = tags or []
    memory_id = f"{date}_{title[:40].lower().replace(' ', '_').replace('/', '_')}"

    # Save raw file
    meta = {
        "id": memory_id,
        "title": title,
        "type": memory_type,
        "date": date,
        "tags": tags,
    }
    dest = MEMORIES_DIR / f"{memory_id}.json"
    dest.write_text(json.dumps({**meta, "content": content}, indent=2, ensure_ascii=False))

    # If original file was uploaded, keep a copy
    if source_path and source_path.exists() and source_path != dest:
        shutil.copy2(source_path, MEMORIES_DIR / source_path.name)

    # Chunk if long (simple sliding-window, 400 tokens ~300 words)
    chunks = _chunk_text(content, chunk_size=300, overlap=50)

    collection = _get_collection()
    embedder = _get_embedder()

    ids, embeddings, documents, metadatas = [], [], [], []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{memory_id}__chunk{i}"
        emb = embedder.encode(chunk).tolist()
        ids.append(chunk_id)
        embeddings.append(emb)
        documents.append(chunk)
        metadatas.append({
            "memory_id": memory_id,
            "title": title,
            "type": memory_type,
            "date": date,
            "tags": json.dumps(tags),
            "chunk_index": i,
            "total_chunks": len(chunks),
        })

    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    return memory_id


def search_memories(query: str, n_results: int = 6) -> list[dict]:
    """Semantic search. Returns list of result dicts with text + metadata."""
    collection = _get_collection()
    embedder = _get_embedder()

    if collection.count() == 0:
        return []

    query_emb = embedder.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    seen_memory_ids = set()
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # De-duplicate: only include the best chunk per memory
        mid = meta["memory_id"]
        if mid in seen_memory_ids:
            continue
        seen_memory_ids.add(mid)

        # Load full memory content for context
        full_content = _load_full_memory(mid)
        hits.append({
            "memory_id": mid,
            "title": meta["title"],
            "type": meta["type"],
            "date": meta["date"],
            "tags": json.loads(meta.get("tags", "[]")),
            "excerpt": doc,
            "full_content": full_content,
            "score": 1 - dist,  # cosine similarity
        })
    return hits


def list_memories() -> list[dict]:
    """Return all stored memories (metadata only)."""
    if not MEMORIES_DIR.exists():
        return []
    memories = []
    for f in sorted(MEMORIES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            memories.append({k: v for k, v in data.items() if k != "content"})
        except Exception:
            pass
    return memories


def delete_memory(memory_id: str) -> bool:
    """Remove a memory from disk and vector DB."""
    collection = _get_collection()

    # Remove all chunks from ChromaDB
    results = collection.get(where={"memory_id": memory_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])

    # Remove raw file
    path = MEMORIES_DIR / f"{memory_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def _load_full_memory(memory_id: str) -> str:
    path = MEMORIES_DIR / f"{memory_id}.json"
    if path.exists():
        data = json.loads(path.read_text())
        return data.get("content", "")
    return ""


def _chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks
