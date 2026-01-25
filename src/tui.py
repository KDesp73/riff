from typing import Optional, Dict, List
from pathlib import Path
import threading

from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    ListView,
    ListItem,
    Static,
    ProgressBar,
)
from textual.binding import Binding
from textual.containers import Horizontal, Vertical

from downloader import get_artist_albums, get_album_tracks
from converter import convert_audio
from metadata import set_metadata
from lyrics import get_lyrics


# -----------------------------
# Album item
# -----------------------------
class AlbumItem(ListItem):
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url
        self.selected = False
        self.label = Static()
        super().__init__(self.label)
        self._update()

    def _update(self):
        prefix = "[✓] " if self.selected else "[ ] "
        self.label.update(prefix + self.title)

    def toggle(self):
        self.selected = not self.selected
        self._update()


# -----------------------------
# Download / conversion status
# -----------------------------
class DownloadStatus(Static):
    def compose(self) -> ComposeResult:
        self.status = Static("Idle")
        self.dl_bar = ProgressBar(total=100)
        self.cv_bar = ProgressBar(total=100)

        yield self.status
        yield Static("Download")
        yield self.dl_bar
        yield Static("Conversion")
        yield self.cv_bar

    def msg(self, text: str):
        self.status.update(text)

    def dl(self, pct: float):
        self.dl_bar.update(progress=int(pct))

    def cv(self, pct: float):
        self.cv_bar.update(progress=int(pct))


# -----------------------------
# Track preview panel (RIGHT)
# -----------------------------
class TrackList(Static):
    def compose(self) -> ComposeResult:
        self.container = Vertical()
        yield self.container

    def show(self, tracks: List[Dict[str, str]]):
        if not self.is_mounted:
            return

        self.container.remove_children()

        if not tracks:
            self.container.mount(Static("—"))
            return

        for i, t in enumerate(tracks, 1):
            filename = f"{i:02d} - {t['title']}.webm"
            text = (
                f"{i:02d}. {t['title']}\n"
                f"    {filename}\n"
                f"    {t['url']}"
            )
            self.container.mount(Static(text))


# -----------------------------
# Main app
# -----------------------------
class AlbumSelector(App):
    CSS = """
    Horizontal { height: 1fr; }

    ListView { width: 40%; }

    TrackList {
        width: 60%;
        padding: 1 2;
        border: round $primary;
    }

    DownloadStatus {
        height: 7;
        padding: 1 2;
        background: $panel;
    }
    """

    BINDINGS = [
        Binding("space", "toggle", "Select"),
        Binding("d", "download", "Download"),
    ]

    def __init__(
        self,
        handle: str,
        artist: str,
        output_dir="output",
        target_format="webm",
        cookies: Optional[str] = None,
    ):
        super().__init__()
        self.handle = handle
        self.artist = artist
        self.output_dir = Path(output_dir)
        self.target_format = target_format
        self.cookies = cookies

        self.albums = get_artist_albums(handle)
        self.album_tracks: Dict[str, List[Dict[str, str]]] = {}

        self._last_index: Optional[int] = None

    # -------------------------
    # UI
    # -------------------------
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal():
            self.list_view = ListView()
            self.track_panel = TrackList()
            yield self.list_view
            yield self.track_panel

        self.status = DownloadStatus()
        yield self.status
        yield Footer()

    def on_mount(self):
        for a in self.albums:
            self.list_view.append(AlbumItem(a["title"], a["url"]))

        threading.Thread(target=self._preload_tracks, daemon=True).start()
        self.set_interval(0.1, self._poll_highlight)

    # -------------------------
    # Track preloading
    # -------------------------
    def _preload_tracks(self):
        for album in self.albums:
            try:
                self.album_tracks[album["url"]] = get_album_tracks(album["url"])
            except Exception as e:
                self.album_tracks[album["url"]] = []
                self.call_from_thread(
                    self.status.msg,
                    f"Failed to preload {album['title']}: {e}",
                )

    # -------------------------
    # Highlight tracking (arrow keys)
    # -------------------------
    def _poll_highlight(self):
        index = self.list_view.index
        if index == self._last_index:
            return

        self._last_index = index

        if index is None:
            self.track_panel.show([])
            return

        item = self.list_view.children[index]
        if isinstance(item, AlbumItem):
            tracks = self.album_tracks.get(item.url, [])
            self.track_panel.show(tracks)
        else:
            self.track_panel.show([])

    # -------------------------
    # Actions
    # -------------------------
    def action_toggle(self):
        index = self.list_view.index
        if index is None:
            return

        item = self.list_view.children[index]
        if isinstance(item, AlbumItem):
            item.toggle()

    def action_download(self):
        selected = [
            i for i in self.list_view.children
            if isinstance(i, AlbumItem) and i.selected
        ]

        if not selected:
            self.notify("No albums selected", severity="warning")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)

        def worker():
            from yt_dlp import YoutubeDL
            import time

            all_files: List[Path] = []

            for album in selected:
                album_dir = self.output_dir / album.title
                album_dir.mkdir(exist_ok=True)

                tracks = self.album_tracks.get(album.url, [])
                total = len(tracks)

                for idx, track in enumerate(tracks, 1):
                    url = track["url"]

                    def hook(d):
                        if d["status"] == "downloading":
                            pct = d.get("_percent_str", "").strip()
                            self.call_from_thread(
                                self.status.msg,
                                f"⬇ {pct} ({idx}/{total})",
                            )
                        elif d["status"] == "finished":
                            all_files.append(Path(d["filename"]))

                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": str(album_dir / f"{idx:02d} - %(title)s.%(ext)s"),
                        "progress_hooks": [hook],
                        "noplaylist": True,
                        "ignoreerrors": True,
                    }

                    if self.cookies:
                        if self.cookies.lower() in {"chrome", "firefox", "edge"}:
                            ydl_opts["cookies_from_browser"] = (self.cookies.lower(),)
                        else:
                            ydl_opts["cookiefile"] = self.cookies

                    with YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])

                    self.call_from_thread(
                        self.status.dl,
                        (idx / total) * 100,
                    )

            total = len(all_files)
            done = 0

            for file in all_files:
                out = file
                album = file.parent.name

                if self.target_format != file.suffix.lstrip("."):
                    out = Path(
                        convert_audio(str(file), self.target_format, str(file.parent))
                    )
                    file.unlink()

                stem = out.stem
                track_number = stem.split("-")[0].strip()
                title = stem.split("-", 1)[-1].strip()

                set_metadata(
                    str(out),
                    {
                        "artist": self.artist,
                        "album": album,
                        "title": title,
                        "tracknumber": track_number,
                    },
                )

                # Download lyrics
                lyrics = get_lyrics(title)
                if lyrics.get("status") == 200:
                    lyrics_file = out.with_suffix(".lrc")
                    lyrics_file.write_text(lyrics.get("lyrics"), encoding="utf-8")

                done += 1
                self.call_from_thread(self.status.cv, (done / total) * 100)

            self.call_from_thread(self.status.msg, "All albums processed ✔")

        threading.Thread(target=worker, daemon=True).start()
