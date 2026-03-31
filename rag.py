"""
RAG pipeline: retrieve relevant memories and build context for Claude.
"""
from store import search_memories

SYSTEM_PROMPT = """\
You are a thoughtful archivist and companion helping someone explore their personal memory archive.

The archive contains journal entries, voice note transcriptions, sketches with captions, poems, and other personal records. Your role is to:

- Help the user rediscover and reflect on their memories with warmth and depth
- Answer questions by drawing directly from the retrieved archive entries
- Notice emotional patterns, recurring themes, and meaningful connections across time
- Speak in a gentle, literary tone — like a wise friend who has read every page of someone's diary
- When quoting or referencing a memory, mention its title and date
- If the retrieved memories don't fully answer the question, say so honestly and suggest what the user might search for

Never invent memories. Only draw from what's in the archive.
"""


def build_rag_context(query: str, n_results: int = 5) -> tuple[list[dict], str]:
    """
    Retrieve relevant memories and format them as context.
    Returns (hits, formatted_context_string).
    """
    hits = search_memories(query, n_results=n_results)

    if not hits:
        return [], "No memories found in the archive yet. Ask the user to upload some memories first."

    lines = ["Here are the most relevant entries from the memory archive:\n"]
    for i, h in enumerate(hits, 1):
        tags_str = f"  Tags: {', '.join(h['tags'])}" if h["tags"] else ""
        lines.append(f"--- MEMORY {i} ---")
        lines.append(f"Title: {h['title']}")
        lines.append(f"Type: {h['type']}  |  Date: {h['date']}{tags_str}")
        lines.append(f"\n{h['full_content'] or h['excerpt']}\n")

    return hits, "\n".join(lines)
