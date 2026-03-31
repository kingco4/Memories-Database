#!/usr/bin/env python3
"""
Memory Archive — Conversational AI for exploring personal memories.

Commands (at the chat prompt):
  /upload <path>   — ingest a file or directory of memories
  /add             — interactively add a memory
  /list            — list all memories in the archive
  /delete <id>     — remove a memory
  /sources         — show which memories were retrieved for last query
  /reset           — clear conversation history
  /help            — show this help
  /quit            — exit
"""
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from agent import MemoryAgent
from ingest import ingest_bulk, ingest_file, ingest_interactive
from store import delete_memory, list_memories

console = Console()


WELCOME = """\
# Memory Archive

A conversational AI for exploring your personal archive of memories.

Ask questions like:
- *"What did I feel the last time I went to the ocean?"*
- *"Show me memories that feel like nostalgia"*
- *"When did things start changing?"*

Type `/help` for commands, `/add` to add a memory, or start chatting.
"""


def show_help():
    console.print(Panel(
        """\
[bold]/upload <path>[/bold]  — ingest a file or directory
[bold]/add[/bold]            — interactively write a new memory
[bold]/list[/bold]           — list all stored memories
[bold]/delete <id>[/bold]    — remove a memory by ID
[bold]/sources[/bold]        — show sources retrieved for last question
[bold]/reset[/bold]          — clear conversation history
[bold]/help[/bold]           — show this message
[bold]/quit[/bold]           — exit""",
        title="[cyan]Commands[/cyan]",
        border_style="dim cyan",
    ))


def show_memory_list():
    memories = list_memories()
    if not memories:
        console.print("[dim]The archive is empty. Use /add or /upload to add memories.[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Title")
    table.add_column("Type", style="magenta")
    table.add_column("Date", style="green")
    table.add_column("Tags", style="dim")

    for m in memories:
        table.add_row(
            m.get("id", ""),
            m.get("title", ""),
            m.get("type", ""),
            m.get("date", ""),
            ", ".join(m.get("tags", [])),
        )
    console.print(table)


def main():
    console.print(Markdown(WELCOME))

    agent = MemoryAgent()
    last_query = ""

    while True:
        try:
            user_input = console.input("[bold green]you>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        # --- Commands ---
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ("/quit", "/exit", "/q"):
                console.print("[dim]Goodbye.[/dim]")
                break

            elif cmd == "/help":
                show_help()

            elif cmd == "/list":
                show_memory_list()

            elif cmd == "/add":
                ingest_interactive()

            elif cmd == "/upload":
                if not arg:
                    console.print("[yellow]Usage: /upload <path>[/yellow]")
                    continue
                path = Path(arg.strip())
                if path.is_dir():
                    n = ingest_bulk(path)
                    console.print(f"[green]Ingested {n} file(s).[/green]")
                else:
                    ingest_file(path)

            elif cmd == "/delete":
                if not arg:
                    console.print("[yellow]Usage: /delete <memory_id>[/yellow]")
                    continue
                if delete_memory(arg.strip()):
                    console.print(f"[green]Deleted memory:[/green] {arg}")
                else:
                    console.print(f"[red]Memory not found:[/red] {arg}")

            elif cmd == "/sources":
                if last_query:
                    agent.show_sources(last_query)
                else:
                    console.print("[dim]Ask a question first.[/dim]")

            elif cmd == "/reset":
                agent.reset()
                console.print("[dim]Conversation history cleared.[/dim]")

            else:
                console.print(f"[yellow]Unknown command:[/yellow] {cmd}. Type /help.")

        else:
            # --- Chat ---
            last_query = user_input
            try:
                agent.chat(user_input)
            except Exception as e:
                console.print(f"\n[red]Error:[/red] {e}")


if __name__ == "__main__":
    main()
