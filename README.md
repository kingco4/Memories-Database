# Memory Archive

A conversational AI for exploring your personal archive of memories. Ask questions about your past in natural language — the system retrieves the most relevant entries and uses Claude to reflect on them with you.

## How it works

1. You ingest memories (journal entries, poems, voice note transcriptions, etc.) into a local vector database (ChromaDB).
2. When you ask a question, the RAG pipeline retrieves the most semantically similar memories.
3. Claude uses those retrieved entries to answer thoughtfully, surfacing patterns and connections across time.

## Setup

```bash
pip install -r requirements.txt
```

Requires an `ANTHROPIC_API_KEY` environment variable.

## Usage

```bash
python main.py
```

### Commands

| Command | Description |
|---|---|
| `/upload <path>` | Ingest a file or directory of memories |
| `/add` | Interactively write a new memory |
| `/list` | List all memories in the archive |
| `/delete <id>` | Remove a memory by ID |
| `/sources` | Show which memories were retrieved for the last query |
| `/reset` | Clear conversation history |
| `/help` | Show command help |
| `/quit` | Exit |

## Memory formats

**JSON** — pre-structured entries:
```json
{
  "title": "The last time I saw the ocean",
  "content": "...",
  "type": "journal",
  "date": "2021-08-14",
  "tags": ["ocean", "nostalgia"]
}
```

**Markdown / plain text** — with optional YAML frontmatter:
```markdown
---
title: Small Mercies
type: poem
date: 2020-05-03
tags: gratitude, spring
---

The light came through the blinds at an angle...
```

If no frontmatter is present, the filename is used as the title.

**Memory types:** `journal`, `voice_note`, `poem`, `sketch`, `letter`, `dream`, `note`, `other`

## Stack

- [Claude](https://anthropic.com) (claude-opus-4-6) — conversational AI with extended thinking
- [ChromaDB](https://www.trychroma.com/) — local vector store
- [sentence-transformers](https://www.sbert.net/) — embedding model
- [Rich](https://github.com/Textualize/rich) — terminal UI
