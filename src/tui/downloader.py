
from typing import Optional, Dict, List
from pathlib import Path
import threading
from datetime import datetime

from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    ListView,
    ListItem,
    Static,
    ProgressBar,
    RichLog,
)
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from downloader import get_album_tracks, get_artist_albums
from metadata import set_metadata
from lyrics import LyricsDownloader, get_lyrics, get_synced_lyrics
from converter import convert_audio
from utils import extract_track_title


# -----------------------------
# Logging
# -----------------------------
class AppLog(RichLog):
    """Custom log widget with timestamping."""

    def info(self, msg: str):
        self.write(f"[bold cyan]INFO[/bold cyan]  [{self._ts()}] {msg}")

    def warn(self, msg: str):
        self.write(f"[bold yellow]WARN[/bold yellow]  [{self._ts()}] {msg}")

    def error(self, msg: str):
        self.write(f"[bold red]ERROR[/bold red] [{self._ts()}] {msg}")

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")


# -----------------------------
# List items
# -----------------------------
class AlbumItem(ListItem):
    def __init__(self, title: str, url: str):
        super().__init__()
        self.title = title
        self.url = url
        self.selected = False
        self.label = Static()

    def compose(self):
        yield self.label

    def on_mount(self):
        self._update()

    def _update(self):
        self.label.update(("[✓] " if self.selected else "[ ] ") + self.title)

    def toggle(self):
        self.selected = not self.selected
        self._update()


class TrackItem(ListItem):
    def __init__(self, index: int, title: str, url: str):
        super().__init__()
        self.index = index
        self.title = title
        self.url = url
        self.selected = False
        self.label = Static()

    def compose(self):
        yield self.label

    def on_mount(self):
        self._update()

    def _update(self):
        prefix = "[✓] " if self.selected else "[ ] "
        self.label.update(f"{prefix}{self.index:02d}. {self.title}")

    def toggle(self):
        self.selected = not self.selected
        self._update()


# -----------------------------
# Status widget
# -----------------------------
class DownloadStatus(Vertical):
    """Container for progress bars and status text."""

    def compose(self):
        yield Static("Idle", id="status_text")
        yield Static("Download Progress")
        yield ProgressBar(total=100, id="dl_bar", show_eta=False)
        yield Static("Conversion Progress")
        yield ProgressBar(total=100, id="cv_bar", show_eta=False)

    def update_msg(self, text: str):
        self.query_one("#status_text", Static).update(text)

    def update_dl(self, pct: float):
        self.query_one("#dl_bar", ProgressBar).progress = pct

    def update_cv(self, pct: float):
        self.query_one("#cv_bar", ProgressBar).progress = pct


# -----------------------------
# Selector Screen
# -----------------------------
class DownloaderScreen(Screen):
    """Album Selector Screen for the main app."""

    CSS = """
    .CliPane { height: 3; background: $surface; padding: 1 2; border: tall $primary; }
    .TopPane { height: 50%; }
    .BottomPane { height: 40%; }

    ListView { width: 50%; border: solid $primary; }
    DownloadStatus { width: 40%; padding: 1; background: $surface; border: tall $primary; }
    AppLog { width: 60%; border: tall $primary; padding: 0 2; }
    """

    BINDINGS = [
        Binding("ctrl+h", "focus_albums", "Focus Albums"),
        Binding("ctrl+l", "focus_tracks", "Focus Tracks"),
        Binding("space", "toggle", "Select/Deselect"),
        Binding("d", "download", "Start Download"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        handle,
        artist,
        output_dir="output",
        target_format="mp3",
        cookies=None,
        download_lyrics=True,
    ):
        super().__init__()
        self.handle = handle
        self.artist = artist
        self.output_dir = Path(output_dir)
        self.target_format = target_format
        self.cookies = cookies

        self.album_tracks: Dict[str, List[Dict[str, str]]] = {}
        self.current_album: Optional[AlbumItem] = None
        self.download_lyrics = download_lyrics

    # -------------------------
    # UI
    # -------------------------
    def compose(self):
        yield Header()

        # CLI info
        with Vertical(classes="CliPane"):
            cli_text = f"{self.artist} @{self.handle}\nOutput: {self.output_dir}\nFormat: {self.target_format} | Download Lyrics: {self.download_lyrics}"
            yield Static(cli_text)

        with Horizontal(classes="TopPane"):
            yield ListView(id="album_list")
            yield ListView(id="track_list")

        with Horizontal(classes="BottomPane"):
            yield DownloadStatus(id="status_area")
            yield AppLog(id="log_view", highlight=True, markup=True)

        yield Footer()

    # -------------------------
    # Mount
    # -------------------------
    def on_mount(self):
        # Load albums
        self.albums = get_artist_albums(self.handle)
        album_list = self.query_one("#album_list", ListView)
        for a in self.albums:
            album_list.append(AlbumItem(a["title"], a["url"]))
        album_list.focus()

        threading.Thread(target=self._preload_tracks, daemon=True).start()

    def _preload_tracks(self):
        log = self.query_one("#log_view", AppLog)
        for album in self.albums:
            try:
                self.album_tracks[album["url"]] = get_album_tracks(album["url"])
            except Exception:
                self.album_tracks[album["url"]] = []
                # Use call_later instead of call_from_thread
                self.call_later(log.warn, f"Failed preloading: {album['title']}")

    # -------------------------
    # Events & Actions
    # -------------------------
    def on_list_view_highlighted(self, event):
        if event.list_view.id == "album_list":
            item = event.item
            if isinstance(item, AlbumItem):
                self.current_album = item
                track_list = self.query_one("#track_list", ListView)
                track_list.clear()
                tracks = self.album_tracks.get(item.url, [])
                for i, t in enumerate(tracks, 1):
                    track_list.append(TrackItem(i, t["title"], t["url"]))

    def action_toggle(self):
        if self.focused and hasattr(self.focused, "children"):
            if isinstance(self.focused, ListView) and self.focused.index is not None:
                item = self.focused.children[self.focused.index]
                if hasattr(item, "toggle"):
                    item.toggle()

    def action_focus_albums(self):
        self.query_one("#album_list").focus()

    def action_focus_tracks(self):
        self.query_one("#track_list").focus()

    def action_download(self):
        album_list = self.query_one("#album_list", ListView)
        track_list = self.query_one("#track_list", ListView)
        selected_albums = [a for a in album_list.children if getattr(a, "selected", False)]
        jobs = []

        if selected_albums:
            for album in selected_albums:
                tracks = self.album_tracks.get(album.url, [])
                for i, t in enumerate(tracks, 1):
                    jobs.append((album, i, t))
        else:
            selected_tracks = [t for t in track_list.children if getattr(t, "selected", False)]
            if not selected_tracks:
                self.notify("Select something first!", severity="error")
                return
            for t in selected_tracks:
                jobs.append((self.current_album, t.index, {"title": t.title, "url": t.url}))

        threading.Thread(target=self.worker, args=(jobs,), daemon=True).start()

    # -------------------------
    # Worker
    # -------------------------
    def worker(self, jobs: List[tuple]):
        from yt_dlp import YoutubeDL

        status_area = self.query_one("#status_area", DownloadStatus)
        log_view = self.query_one("#log_view", AppLog)
        downloaded_paths: List[Path] = []
        total = len(jobs)

        # --- Phase 1: Download ---
        for idx, (album, track_no, track) in enumerate(jobs, 1):
            album_dir = self.output_dir / album.title
            album_dir.mkdir(parents=True, exist_ok=True)

            def hook(d):
                if d["status"] == "downloading":
                    p_str = d.get("_percent_str", "0%").replace("%", "").strip()
                    self.call_later(
                        status_area.update_msg, f"Downloading: {track['title']} ({p_str}%)"
                    )

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": str(album_dir / f"{track_no:02d} - %(title)s.%(ext)s"),
                "progress_hooks": [hook],
                "quiet": True,
                "noplaylist": True,
                "ignoreerrors": False,
            }

            if self.cookies:
                if self.cookies.lower() in {"chrome", "firefox", "edge", "safari", "opera"}:
                    ydl_opts["cookies_from_browser"] = (self.cookies.lower(),)
                else:
                    ydl_opts["cookiefile"] = self.cookies

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(track["url"], download=True)
                    if info:
                        final_filename = Path(ydl.prepare_filename(info))
                        downloaded_paths.append(final_filename)
                        self.call_later(log_view.info, f"Downloaded: {final_filename.name}")
                self.call_later(status_area.update_dl, (idx / total) * 100)
            except Exception as e:
                self.call_later(log_view.error, f"DL Failed [{track_no}]: {e}")

        # --- Phase 2: Convert, Metadata & Lyrics ---
        self.call_later(status_area.update_msg, "Processing metadata & conversion...")
        proc_total = len(downloaded_paths)

        for idx, file_path in enumerate(downloaded_paths, 1):
            try:
                current_file = file_path
                album_name = file_path.parent.name

                # 1. Conversion
                actual_ext = file_path.suffix.lstrip(".")
                if self.target_format.lower() != actual_ext.lower():
                    self.call_later(status_area.update_msg, f"Converting: {file_path.name}")
                    new_path_str = convert_audio(str(file_path), self.target_format, str(file_path.parent))
                    file_path.unlink()
                    current_file = Path(new_path_str)
                    self.call_later(log_view.info, f"Converted: {current_file.name}")

                # 2. Metadata
                track_no_str, title_str = extract_track_title(str(current_file), self.artist)
                tags = {
                    "artist": self.artist,
                    "album": album_name,
                    "title": title_str.strip(),
                    "tracknumber": track_no_str.strip(),
                }
                set_metadata(str(current_file), tags)
                self.call_later(log_view.info, f"Tags set: {current_file.name}")

                # 3. Lyrics
                if self.download_lyrics:
                    self.call_later(status_area.update_msg, f"Fetching lyrics: {title_str}")
                    lyrics_downloader = LyricsDownloader(tags["artist"], tags["title"], current_file)
                    lyrics_download_data = lyrics_downloader.download_lyrics()
                    if lyrics_download_data.get("status") == 200:
                        self.call_later(log_view.info, lyrics_download_data.get("message"))
                    

            except Exception as e:
                self.call_later(log_view.error, f"Process error on {file_path.name}: {e}")

            self.call_later(status_area.update_cv, (idx / proc_total) * 100)

        self.call_later(status_area.update_msg, "All tasks complete! ✔")
        self.call_later(log_view.info, f"Processed {proc_total} tracks successfully.")
