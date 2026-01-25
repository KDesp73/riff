from typing import Callable, List, Dict
from textual.screen import Screen
from textual.widgets import Input, ListView, ListItem, Static
from textual.containers import Vertical
import threading
from rich.text import Text
from textual import events

from downloader import search_artist


class SearchResultItem(ListItem):
    """A selectable item for search results."""
    def __init__(self, handle: str, artist: str):
        super().__init__()
        self.handle = handle
        self.artist = artist
        self.label = Static(f"{artist} (@{handle})")
        self.selected = False

    def compose(self):
        yield self.label

    def toggle(self):
        self.selected = not self.selected
        self.label.update(f"[✓] {self.artist} (@{self.handle})" if self.selected else f"{self.artist} (@{self.handle})")


class SearchScreen(Screen):
    """Centered search page for artists."""
    CSS = """
    #search_page {
        height: 100%;
        width: 100%;
        content-align: center middle;
        padding: 1;
    }

    #app_title {
        padding-bottom: 1;
        color: magenta;
    }

    #subtitle {
        padding-bottom: 1;
        color: cyan;
    }

    #search_input {
        width: 60%;
        min-height: 3;
        margin-bottom: 1;
        border: tall magenta;
        padding: 0 1;
    }

    #results_list {
        width: 60%;
        height: 40%;
        border: tall magenta;
        overflow: auto;
        padding: 0 1;
    }
    """

    def __init__(self, on_select: Callable[[str, str], None]):
        super().__init__()
        self.on_select = on_select
        self.results: List[Dict[str, str]] = []

    def compose(self):
        with Vertical(id="search_page"):
            # Use Rich Text for title
            yield Static(Text("Riff Downloader", justify="center", style="bold magenta"), id="app_title")
            yield Static(Text("Search for an artist by handle or name:", justify="center", style="italic cyan"), id="subtitle")

            self.input = Input(placeholder="Enter artist handle...", id="search_input")
            yield self.input

            self.list_view = ListView(id="results_list")
            yield self.list_view

    async def on_mount(self):
        # Focus the input so typing works immediately
        self.set_focus(self.input)

    async def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()
        if not query:
            return

        # Clear previous results
        self.list_view.clear()
        self.results.clear()
        self.list_view.append(ListItem(Static("Searching...")))

        # Background search
        threading.Thread(target=self._search_artist, args=(query,), daemon=True).start()

    def _search_artist(self, query: str):
        self.results = search_artist(query)
        self.list_view.focus()
        self.call_later(self._update_results)

    def _update_results(self):
        self.list_view.clear()
        for r in self.results:
            self.list_view.append(SearchResultItem(r["handle"], r["artist"]))

    async def key_enter(self, event: events.Key):
        """Select the highlighted result."""
        if self.list_view.index is None:
            return
        item = self.list_view.children[self.list_view.index]
        if isinstance(item, SearchResultItem):
            self.on_select(item.handle, item.artist)
