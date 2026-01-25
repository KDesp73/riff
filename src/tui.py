from typing import Optional
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, Static, ProgressBar
from textual.binding import Binding
from pathlib import Path
import threading

from downloader import download_albums, get_artist_albums, get_album_tracks
from converter import convert_audio
from metadata import set_metadata


class AlbumItem(ListItem):
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url
        self.selected = False
        self.label = Label()
        super().__init__(self.label)
        self._update_label()

    def _update_label(self):
        prefix = "[✓] " if self.selected else "[ ] "
        self.label.update(prefix + self.title)

    def toggle(self):
        self.selected = not self.selected
        self._update_label()


class DownloadStatus(Static):
    """Widget to show live download/conversion progress with bars."""

    def compose(self) -> ComposeResult:
        self.status_label = Label("Idle")
        self.download_bar_label = Label("Download Progress:")
        self.download_bar = ProgressBar(total=100)
        self.conversion_bar_label = Label("Conversion Progress:")
        self.conversion_bar = ProgressBar(total=100)

        yield self.status_label
        yield self.download_bar_label
        yield self.download_bar
        yield self.conversion_bar_label
        yield self.conversion_bar

    def update_status(self, msg: str):
        self.status_label.update(msg)

    def update_download(self, percent: float):
        self.download_bar.update(progress=int(percent))

    def update_conversion(self, percent: float):
        self.conversion_bar.update(progress=int(percent))


class AlbumSelector(App):
    CSS = """
    ListView {
        height: 1fr;
    }

    DownloadStatus {
        height: 6;
        padding: 1 2;
        background: $panel;
    }
    """

    BINDINGS = [
        Binding("space", "toggle", "Select"),
        Binding("d", "download", "Download"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, handle: str, artist: str, output_dir: str = "output", target_format: str = "webm", cookies: Optional[str] = None):
        super().__init__()
        self.handle = handle
        self.artist = artist
        self.output_dir = Path(output_dir)
        self.target_format = target_format
        self.albums = get_artist_albums(handle)
        self.cookies = cookies

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self.list_view = ListView()
        yield self.list_view
        self.status = DownloadStatus()
        yield self.status
        yield Footer()

    def on_mount(self):
        for album in self.albums:
            self.list_view.append(AlbumItem(album["title"], album["url"]))

    def action_toggle(self):
        item = self.list_view.highlighted_child
        if isinstance(item, AlbumItem):
            item.toggle()

    def action_download(self):
        selected_items = [
            item for item in self.list_view.children
            if isinstance(item, AlbumItem) and item.selected
        ]

        if not selected_items:
            self.notify("No albums selected", severity="warning")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)

        def worker():
            try:
                all_files = []

                for album_item in selected_items:
                    album_dir = self.output_dir / album_item.title
                    album_dir.mkdir(exist_ok=True)

                    # Get track URLs
                    tracks = get_album_tracks(album_item.url)

                    # Progress hook
                    def progress_hook(d):
                        status = d.get("status")
                        filename = d.get("filename", "")
                        if status == "downloading":
                            percent = d.get("_percent_str", "").strip()
                            self.call_from_thread(self.status.update_status, f"⬇ {filename} {percent}")
                        elif status == "finished":
                            self.call_from_thread(self.status.update_status, f"✔ Finished {filename}")
                            all_files.append(Path(filename))

                    # Synchronously download the album
                    from yt_dlp import YoutubeDL
                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": str(album_dir / "%(playlist_index)02d - %(title)s.%(ext)s"),
                        "progress_hooks": [progress_hook],
                        "noplaylist": False,
                    }
                    if self.cookies:
                        if self.cookies.lower() in ["chrome", "firefox", "edge"]:
                            ydl_opts["cookies_from_browser"] = (self.cookies.lower(),)
                        else:
                            ydl_opts["cookiefile"] = self.cookies

                    with YoutubeDL(ydl_opts) as ydl:
                        ydl.download([album_item.url])  # <-- blocks until all tracks are fully downloaded

                # Conversion & metadata
                for file in all_files:
                    out_file = Path(file)
                    if self.target_format != file.suffix.lstrip("."):
                        self.call_from_thread(
                            self.status.update_status,
                            f"Converting {file.name} → {self.target_format}"
                        )
                        out_file = Path(convert_audio(str(file), self.target_format, str(file.parent)))
                        file.unlink()

                    # Metadata
                    filename = file.stem
                    track_number = filename.split("-")[0].strip()
                    title = [part.strip() for part in filename.split("-")][-1]

                    metadata = {
                        "artist": self.artist,
                        "album": album_name,
                        "title": title,
                        "tracknumber": track_number,
                    }
                    set_metadata(str(out_file), metadata)

                self.call_from_thread(self.status.update_status, "All albums processed ✔")

            except Exception as e:
                self.call_from_thread(self.status.update_status, f"Error: {e}")

        threading.Thread(target=worker, daemon=True).start()
