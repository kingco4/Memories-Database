"""
Conversational agent powered by Claude claude-opus-4-6 with RAG.
Maintains multi-turn conversation history.
"""
import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from rag import SYSTEM_PROMPT, build_rag_context

console = Console()


class MemoryAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.history: list[dict] = []

    def chat(self, user_message: str) -> str:
        """Send a message and stream the response. Returns full response text."""
        # Build RAG context for this query
        hits, rag_context = build_rag_context(user_message)

        # Inject RAG context into the user message
        augmented_message = f"{user_message}\n\n[ARCHIVE CONTEXT]\n{rag_context}"

        # Append to history
        self.history.append({"role": "user", "content": augmented_message})

        # Keep history bounded (last 20 turns) to avoid hitting context limits
        messages = self.history[-20:]

        response_text = ""
        console.print()

        with self.client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
            thinking={"type": "adaptive"},
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        console.print(event.delta.text, end="", highlight=False)
                        response_text += event.delta.text

        console.print()  # newline after streaming

        # Append assistant response to history (without the RAG context injection,
        # so follow-up turns don't carry stale context)
        self.history[-1] = {"role": "user", "content": user_message}
        self.history.append({"role": "assistant", "content": response_text})

        return response_text

    def show_sources(self, query: str):
        """Print the retrieved memory sources for a query."""
        hits, _ = build_rag_context(query)
        if not hits:
            console.print("[dim]No memories retrieved.[/dim]")
            return
        console.print(Panel(
            "\n".join(
                f"[bold]{h['title']}[/bold] ({h['date']}) · {h['type']} · score={h['score']:.2f}"
                for h in hits
            ),
            title="[cyan]Retrieved memories[/cyan]",
            border_style="dim",
        ))

    def reset(self):
        """Clear conversation history."""
        self.history.clear()
