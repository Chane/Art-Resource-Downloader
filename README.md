# Art Resource Downloader

A Python CLI tool ("PosterGeterinator") that downloads album art and artist images for a [Last.fm](https://www.last.fm/) user via the Last.fm API.

For each of the user's top albums it fetches the highest-resolution cover art available (`extralarge` → `large` fallback) and saves it to a local directory. Already-present files are skipped, making re-runs safe.

> **Note:** Last.fm removed artist images from their public API around 2019. The artist download step still runs but will report most images as unavailable.

## Requirements

- Python 3.8+
- `requests`
- `pytest` (for tests)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Credentials are read from `config.py`. Copy `config_local.py` (git-ignored) to supply real values:

| Variable | Description |
|---|---|
| `LASTFM_API_KEY` | Last.fm API key |
| `LASTFM_SHARED_SECRET` | Last.fm shared secret |
| `LASTFM_ACCOUNT` | Default Last.fm username |

`config.py` ships with placeholder values and imports `config_local.py` at runtime if it exists.

## Usage

```bash
python main.py [options]
```

| Flag | Description | Default |
|---|---|---|
| `-u`, `--user USER` | Last.fm username to fetch art for | `LASTFM_ACCOUNT` in config |
| `-o`, `--output DIR` | Directory to save images | `./output/` |
| `-v`, `--verbose` | Log informational messages | — |
| `-d`, `--debug` | Log debug messages | — |

**Examples:**

```bash
# Download art for the configured account into ./output/
python main.py -v

# Download art for a specific user into a custom directory
python main.py --user rj --output ~/Music/art -v
```

## Output Structure

```
output/
├── albums/
│   ├── Cher - Believe.jpg
│   └── Dream Theater - Images and Words.jpg
└── artists/
    └── ...   (usually empty — see note above)
```

Files are named `{Artist} - {Album}{ext}` for albums and `{Artist}{ext}` for artists.

## Running Tests

```bash
python -m pytest tests/ -v
```

Tests use `unittest.mock` — no network calls or real credentials required.

## Project Structure

```
main.py                  # Entry point
myclass.py               # ArtDownloader class
config.py                # Dummy credentials + local override import
config_local.py          # Real credentials (git-ignored)
requirements.txt         # Python dependencies
tests/
└── test_art_downloader.py
```

