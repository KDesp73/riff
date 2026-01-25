from textual.app import App
from .downloader import DownloaderScreen
from .search import SearchScreen
from .settings import SettingsScreen

class RiffApp(App):
    def __init__(self, handle=None, artist=None, **kwargs):
        super().__init__(**kwargs)
        self.handle = handle
        self.artist = artist

    def on_mount(self):
        # Decide first screen
        if self.handle is None:
            # Show search screen first
            self.push_screen(SearchScreen(on_select=self.on_search_select))
        else:
            # Directly go to downloader
            self.push_screen(
                DownloaderScreen(handle=self.handle, artist=self.artist)
            )

    def on_search_select(self, handle: str, artist: str):
        """Callback from SearchScreen when user selects an artist."""
        self.handle = handle
        self.artist = artist
        # Switch to downloader screen with selected artist
        self.push_screen(DownloaderScreen(handle=handle, artist=artist))
