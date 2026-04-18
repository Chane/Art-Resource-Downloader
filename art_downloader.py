import logging
import sys
import argparse
from pathlib import Path

import requests

import config

LASTFM_API_BASE = "http://ws.audioscrobbler.com/2.0/"
IMAGE_SIZE_PREFERENCE = ("extralarge", "large", "medium", "small")


class ArtDownloader:
    def __init__(self, args=None):
        parser = argparse.ArgumentParser(
            description="Download album art and artist images from Last.fm"
        )
        parser.add_argument(
            "-d", "--debug",
            help="Log debug information",
            action="store_const", dest="loglevel", const=logging.DEBUG,
            default=logging.WARNING,
        )
        parser.add_argument(
            "-v", "--verbose",
            help="Log verbose information",
            action="store_const", dest="loglevel", const=logging.INFO,
        )
        parser.add_argument(
            "-u", "--user",
            help="Last.fm username to fetch art for (default: configured account)",
            default=None,
        )
        parser.add_argument(
            "-o", "--output",
            help="Directory to save downloaded images (default: ./output/)",
            default="./output/",
        )

        parsed = parser.parse_args(args)

        logging.basicConfig(stream=sys.stdout, level=parsed.loglevel,
                            format="%(levelname)s: %(message)s")
        self.logger = logging.getLogger(__name__)

        self.user = parsed.user or config.LASTFM_ACCOUNT
        self.output_dir = Path(parsed.output)
        self.api_key = config.LASTFM_API_KEY

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self):
        self.logger.info("Starting download for user: %s", self.user)
        self.logger.info("Output directory: %s", self.output_dir)

        albums_dir = self.output_dir / "albums"
        artists_dir = self.output_dir / "artists"
        albums_dir.mkdir(parents=True, exist_ok=True)
        artists_dir.mkdir(parents=True, exist_ok=True)

        self._download_album_art(albums_dir)
        self._download_artist_images(artists_dir)

        self.logger.info("Done.")

    # ------------------------------------------------------------------
    # Download orchestrators
    # ------------------------------------------------------------------

    def _download_album_art(self, dest_dir: Path):
        self.logger.info("Fetching top albums for %s…", self.user)
        albums = self._fetch_all_pages(
            method="user.gettopalbums",
            result_key="topalbums",
            items_key="album",
            user=self.user,
        )
        self.logger.info("Found %d albums.", len(albums))

        downloaded = skipped = missing = 0
        for album in albums:
            artist = album.get("artist", {}).get("name", "Unknown Artist")
            name = album.get("name", "Unknown Album")
            url = self._get_image_url(album.get("image", []))
            if not url:
                self.logger.debug("No image URL for album: %s – %s", artist, name)
                missing += 1
                continue

            safe_artist = _safe_filename(artist)
            safe_name = _safe_filename(name)
            ext = _url_extension(url)
            filepath = dest_dir / f"{safe_artist} - {safe_name}{ext}"

            result = self._download_image(url, filepath)
            if result is True:
                downloaded += 1
            elif result is False:
                skipped += 1

        self.logger.info(
            "Albums — downloaded: %d, skipped (exists): %d, no image: %d",
            downloaded, skipped, missing,
        )

    def _download_artist_images(self, dest_dir: Path):
        self.logger.info("Fetching top artists for %s…", self.user)
        artists = self._fetch_all_pages(
            method="user.gettopartists",
            result_key="topartists",
            items_key="artist",
            user=self.user,
        )
        self.logger.info("Found %d artists.", len(artists))

        downloaded = skipped = missing = 0
        for artist in artists:
            name = artist.get("name", "Unknown Artist")
            url = self._get_image_url(artist.get("image", []))
            if not url:
                self.logger.debug(
                    "No image URL for artist: %s (Last.fm removed artist images in 2019)", name
                )
                missing += 1
                continue

            safe_name = _safe_filename(name)
            ext = _url_extension(url)
            filepath = dest_dir / f"{safe_name}{ext}"

            result = self._download_image(url, filepath)
            if result is True:
                downloaded += 1
            elif result is False:
                skipped += 1

        self.logger.info(
            "Artists — downloaded: %d, skipped (exists): %d, no image: %d",
            downloaded, skipped, missing,
        )

    # ------------------------------------------------------------------
    # Last.fm API helpers
    # ------------------------------------------------------------------

    def _fetch_all_pages(self, method: str, result_key: str, items_key: str, **params) -> list:
        """Fetch every page for a paginated Last.fm endpoint and return a flat list."""
        all_items = []
        page = 1

        while True:
            response = requests.get(
                LASTFM_API_BASE,
                params={
                    "method": method,
                    "api_key": self.api_key,
                    "format": "json",
                    "limit": 200,
                    "page": page,
                    **params,
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise RuntimeError(
                    f"Last.fm API error {data['error']}: {data.get('message', '')}"
                )

            result = data.get(result_key, {})
            items = result.get(items_key, [])
            if isinstance(items, dict):
                # API returns a single object instead of a list when there's one result
                items = [items]

            all_items.extend(items)

            attr = result.get("@attr", {})
            total_pages = int(attr.get("totalPages", 1))
            self.logger.debug("Fetched page %d / %d (%s)", page, total_pages, method)

            if page >= total_pages:
                break
            page += 1

        return all_items

    def _get_image_url(self, images: list) -> str:
        """Return the best available image URL from a Last.fm image list."""
        by_size = {img.get("size"): img.get("#text", "") for img in images}
        for size in IMAGE_SIZE_PREFERENCE:
            url = by_size.get(size, "")
            if url:
                return url
        return ""

    def _download_image(self, url: str, filepath: Path) -> bool:
        """
        Download *url* to *filepath*.

        Returns True  if the file was downloaded.
        Returns False if the file already existed (skipped).
        Raises on HTTP / IO errors.
        """
        if filepath.exists():
            self.logger.debug("Skipping (exists): %s", filepath.name)
            return False

        self.logger.info("Downloading: %s", filepath.name)
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        with filepath.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=8192):
                fh.write(chunk)

        return True


# ------------------------------------------------------------------
# Module-level utilities
# ------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    """Strip characters that are invalid in filenames."""
    keep = set(r" .,!&'()-_[]")
    return "".join(c if (c.isalnum() or c in keep) else "_" for c in name).strip()


def _url_extension(url: str) -> str:
    """Extract file extension from a URL, defaulting to .jpg."""
    path = url.split("?")[0]
    suffix = Path(path).suffix
    return suffix if suffix else ".jpg"
