# Art Resource Downloader

> **Work in progress**

A Python CLI tool ("PosterGeterinator") for downloading art resources such as album artwork and posters via the [Last.fm API](https://www.last.fm/api).

## Usage

```bash
python main.py           # run normally
python main.py -v        # verbose output
python main.py -d        # debug output
```

## Configuration

API credentials are stored in `config.py`:

| Variable | Description |
|---|---|
| `LASTFM_APPLICATON_NAME` | Last.fm application name |
| `LASTFM_API_KEY` | Last.fm API key |
| `LASTFM_SHARED_SECRET` | Last.fm shared secret |
| `LASTFM_ACCOUNT` | Last.fm account to query |

> **Warning:** Do not commit real credentials to source control. Consider using environment variables or a `.env` file and adding `config.py` to `.gitignore`.

## Requirements

- Python 3
- `requests`

## Project Structure

```
main.py      # Entry point
myclass.py   # Core application class
config.py    # API credentials and configuration
```
