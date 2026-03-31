"""
Ingest memories from files or interactive input.

Supported file types:
  .txt / .md   — text, journal, poem
  .json        — pre-structured { title, content, type, date, tags }

Usage:
  from ingest import ingest_file, ingest_interactive
"""
import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt

from store import add_memory

console = Console()

VALID_TYPES = ["journal", "voice_note", "poem", "sketch", "letter", "dream", "note", "other"]


def ingest_file(path: str | Path) -> Optional[str]:
    """
    Ingest a single file into the memory archive.
    Returns the memory_id on success, None on failure.
    """
    path = Path(path)
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        return None

    suffix = path.suffix.lower()

    if suffix == ".json":
        return _ingest_json(path)
    elif suffix in (".txt", ".md"):
        return _ingest_text(path)
    else:
        console.print(f"[yellow]Unsupported file type:[/yellow] {suffix} — only .txt, .md, .json")
        return None


def _ingest_json(path: Path) -> Optional[str]:
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        console.print(f"[red]Failed to parse JSON:[/red] {e}")
        return None

    required = {"title", "content"}
    if not required.issubset(data.keys()):
        console.print(f"[red]JSON must have at least 'title' and 'content' fields.[/red]")
        return None

    memory_id = add_memory(
        content=data["content"],
        title=data["title"],
        memory_type=data.get("type", "note"),
        date=data.get("date"),
        tags=data.get("tags", []),
        source_path=path,
    )
    console.print(f"[green]✓[/green] Ingested: [bold]{data['title']}[/bold] → {memory_id}")
    return memory_id


def _ingest_text(path: Path) -> Optional[str]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        console.print(f"[yellow]Empty file:[/yellow] {path}")
        return None

    # Try to parse frontmatter (--- key: value --- at top)
    title, memory_type, date, tags = None, "note", None, []
    try:
        import frontmatter
        post = frontmatter.loads(content)
        content = post.content.strip()
        title = post.get("title")
        memory_type = post.get("type", "note")
        raw_date = post.get("date")
        date = raw_date.isoformat() if hasattr(raw_date, "isoformat") else raw_date
        tags = post.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
    except Exception:
        pass

    # Fallback: use filename as title
    if not title:
        title = path.stem.replace("_", " ").replace("-", " ").title()

    memory_id = add_memory(
        content=content,
        title=title,
        memory_type=memory_type,
        date=date,
        tags=tags,
        source_path=path,
    )
    console.print(f"[green]✓[/green] Ingested: [bold]{title}[/bold] → {memory_id}")
    return memory_id


def ingest_interactive() -> Optional[str]:
    """Interactively collect a memory from the user and store it."""
    console.print("\n[bold cyan]Add a new memory[/bold cyan]")

    title = Prompt.ask("Title")
    memory_type = Prompt.ask(
        "Type",
        choices=VALID_TYPES,
        default="journal",
    )
    date = Prompt.ask("Date (YYYY-MM-DD)", default="")
    tags_raw = Prompt.ask("Tags (comma-separated, optional)", default="")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    console.print("Content (type your memory, then press [bold]Ctrl+D[/bold] or enter [bold]END[/bold] on a new line):")
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
    except EOFError:
        pass
    content = "\n".join(lines).strip()

    if not content:
        console.print("[yellow]No content entered. Cancelled.[/yellow]")
        return None

    memory_id = add_memory(
        content=content,
        title=title,
        memory_type=memory_type,
        date=date or None,
        tags=tags,
    )
    console.print(f"[green]✓[/green] Memory saved: [bold]{title}[/bold] → {memory_id}")
    return memory_id


def ingest_bulk(directory: str | Path) -> int:
    """Ingest all .txt, .md, .json files in a directory. Returns count ingested."""
    directory = Path(directory)
    if not directory.is_dir():
        console.print(f"[red]Not a directory:[/red] {directory}")
        return 0

    count = 0
    for path in sorted(directory.rglob("*")):
        if path.suffix.lower() in (".txt", ".md", ".json") and path.is_file():
            if ingest_file(path):
                count += 1
    return count
