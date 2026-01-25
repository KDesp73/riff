# Riff

**Riff** is a fast, standalone Python tool for exploring YouTube music content, downloading albums and tracks, and managing them locally. It features:

* Artist and album exploration
* Track listing and download
* Persistent caching to speed up repeated queries
* TUI interface using Rich/Textual for a smooth terminal experience
* Single-file executable for easy installation

---

## Features

* Fetch all albums/releases of a YouTube artist
* List tracks from a specific album
* Download tracks efficiently via `yt-dlp`
* Persistent caching (`~/.cache/riff.cache`) with configurable TTL
* Standalone single-file executable built with PyInstaller

---

## Installation

### Prerequisites

* Python 3.10+ (for development)
* `git` (optional)
* `sudo` privileges for system-wide install

### Using the installer script

```bash
git clone <repo-url> riff
cd riff
chmod +x ./scripts/install
./scripts/install
```

This will:

1. Create a virtual environment
2. Install dependencies
3. Build a standalone executable
4. Copy it to `/usr/local/bin/riff`

After this, you can run:

```bash
riff
```

### Development mode

```bash
source ./scripts/sourceme
python src/main.py
```

---

## Development Structure

```
.
├── src
│   ├── cache.py       # Persistent cache class
│   ├── converter.py   # Utilities for conversions (optional)
│   ├── downloader.py  # yt-dlp download logic
│   ├── metadata.py    # Track and album metadata management
│   ├── main.py        # CLI entry point
│   └── tui.py         # Terminal interface using Rich/Textual
├── scripts
│   ├── sourceme       # Optional environment helper
│   └── install        # Installation script
├── requirements.txt
└── README.md
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dependencies in a virtual environment
4. Make your changes
5. Submit a pull request

---

## License

MIT License — see [LICENSE](LICENSE)
