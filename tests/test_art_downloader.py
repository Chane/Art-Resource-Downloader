import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from myclass import ArtDownloader, _safe_filename, _url_extension


# ---------------------------------------------------------------------------
# Helpers for building mock responses
# ---------------------------------------------------------------------------

def _make_image_list(*sizes):
    """Build a Last.fm style image list from (size, url) tuples."""
    return [{"size": s, "#text": u} for s, u in sizes]


def _make_response(data: dict, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


# ---------------------------------------------------------------------------
# ArtDownloader instantiation helper (bypasses argparse sys.argv)
# ---------------------------------------------------------------------------

def make_downloader(output_dir, user="testuser", api_key="testkey"):
    with patch("config.LASTFM_ACCOUNT", user), patch("config.LASTFM_API_KEY", api_key):
        dl = ArtDownloader(args=["--output", str(output_dir), "--user", user])
    dl.api_key = api_key
    dl.user = user
    return dl


# ---------------------------------------------------------------------------
# _get_image_url
# ---------------------------------------------------------------------------

class TestGetImageUrl:
    def setup_method(self):
        self.dl = make_downloader(Path("/tmp"))

    def test_returns_extralarge_url(self):
        images = _make_image_list(
            ("small", "http://example.com/s.jpg"),
            ("medium", "http://example.com/m.jpg"),
            ("large", "http://example.com/l.jpg"),
            ("extralarge", "http://example.com/xl.jpg"),
        )
        assert self.dl._get_image_url(images) == "http://example.com/xl.jpg"

    def test_falls_back_to_large_when_extralarge_missing(self):
        images = _make_image_list(
            ("small", "http://example.com/s.jpg"),
            ("large", "http://example.com/l.jpg"),
            ("extralarge", ""),
        )
        assert self.dl._get_image_url(images) == "http://example.com/l.jpg"

    def test_returns_empty_string_when_all_urls_blank(self):
        images = _make_image_list(
            ("small", ""),
            ("medium", ""),
            ("large", ""),
            ("extralarge", ""),
        )
        assert self.dl._get_image_url(images) == ""

    def test_returns_empty_string_for_empty_list(self):
        assert self.dl._get_image_url([]) == ""


# ---------------------------------------------------------------------------
# _download_image
# ---------------------------------------------------------------------------

class TestDownloadImage:
    def setup_method(self):
        self.dl = make_downloader(Path("/tmp"))

    def test_skips_existing_file(self, tmp_path):
        existing = tmp_path / "art.jpg"
        existing.write_bytes(b"existing")

        with patch("myclass.requests.get") as mock_get:
            result = self.dl._download_image("http://example.com/art.jpg", existing)

        assert result is False
        mock_get.assert_not_called()
        assert existing.read_bytes() == b"existing"  # untouched

    def test_downloads_and_saves_new_file(self, tmp_path):
        dest = tmp_path / "new.jpg"
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content.return_value = [b"chunk1", b"chunk2"]

        with patch("myclass.requests.get", return_value=mock_resp):
            result = self.dl._download_image("http://example.com/new.jpg", dest)

        assert result is True
        assert dest.read_bytes() == b"chunk1chunk2"

    def test_raises_on_http_error(self, tmp_path):
        dest = tmp_path / "fail.jpg"
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404")

        with patch("myclass.requests.get", return_value=mock_resp):
            with pytest.raises(Exception, match="404"):
                self.dl._download_image("http://example.com/fail.jpg", dest)


# ---------------------------------------------------------------------------
# _fetch_all_pages
# ---------------------------------------------------------------------------

class TestFetchAllPages:
    def setup_method(self):
        self.dl = make_downloader(Path("/tmp"))

    def test_single_page(self):
        payload = {
            "topalbums": {
                "album": [{"name": "Album A"}, {"name": "Album B"}],
                "@attr": {"page": "1", "totalPages": "1"},
            }
        }
        with patch("myclass.requests.get", return_value=_make_response(payload)):
            result = self.dl._fetch_all_pages(
                method="user.gettopalbums",
                result_key="topalbums",
                items_key="album",
                user="testuser",
            )
        assert [a["name"] for a in result] == ["Album A", "Album B"]

    def test_multi_page(self):
        page1 = {
            "topalbums": {
                "album": [{"name": "Album A"}],
                "@attr": {"page": "1", "totalPages": "2"},
            }
        }
        page2 = {
            "topalbums": {
                "album": [{"name": "Album B"}],
                "@attr": {"page": "2", "totalPages": "2"},
            }
        }
        responses = [_make_response(page1), _make_response(page2)]
        with patch("myclass.requests.get", side_effect=responses):
            result = self.dl._fetch_all_pages(
                method="user.gettopalbums",
                result_key="topalbums",
                items_key="album",
                user="testuser",
            )
        assert [a["name"] for a in result] == ["Album A", "Album B"]

    def test_raises_on_api_error(self):
        payload = {"error": 10, "message": "Invalid API key"}
        with patch("myclass.requests.get", return_value=_make_response(payload)):
            with pytest.raises(RuntimeError, match="Invalid API key"):
                self.dl._fetch_all_pages(
                    method="user.gettopalbums",
                    result_key="topalbums",
                    items_key="album",
                    user="testuser",
                )

    def test_single_item_response_wrapped_in_list(self):
        """API returns a dict instead of a list when there is exactly one result."""
        payload = {
            "topalbums": {
                "album": {"name": "Only Album"},
                "@attr": {"page": "1", "totalPages": "1"},
            }
        }
        with patch("myclass.requests.get", return_value=_make_response(payload)):
            result = self.dl._fetch_all_pages(
                method="user.gettopalbums",
                result_key="topalbums",
                items_key="album",
                user="testuser",
            )
        assert result == [{"name": "Only Album"}]


# ---------------------------------------------------------------------------
# run() — integration (fully mocked)
# ---------------------------------------------------------------------------

class TestRun:
    def _make_album(self, artist, name, image_url):
        return {
            "name": name,
            "artist": {"name": artist},
            "image": _make_image_list(
                ("small", ""), ("medium", ""), ("large", ""), ("extralarge", image_url)
            ),
        }

    def _make_artist(self, name, image_url=""):
        return {
            "name": name,
            "image": _make_image_list(
                ("small", ""), ("medium", ""), ("large", ""), ("extralarge", image_url)
            ),
        }

    def test_run_downloads_album_art(self, tmp_path):
        albums = [
            self._make_album("Cher", "Believe", "http://example.com/believe.jpg"),
            self._make_album("Dream Theater", "Metropolis", "http://example.com/metro.jpg"),
        ]
        artists = [
            self._make_artist("Cher"),        # no image — should be skipped gracefully
            self._make_artist("Dream Theater"),
        ]

        dl = make_downloader(tmp_path)

        with patch.object(dl, "_fetch_all_pages", side_effect=[albums, artists]), \
             patch.object(dl, "_download_image", return_value=True) as mock_dl:
            dl.run()

        # Only the two albums have image URLs; artists have none
        assert mock_dl.call_count == 2
        downloaded_names = {call.args[1].name for call in mock_dl.call_args_list}
        assert "Cher - Believe.jpg" in downloaded_names
        assert "Dream Theater - Metropolis.jpg" in downloaded_names

    def test_run_creates_output_dirs(self, tmp_path):
        dl = make_downloader(tmp_path / "output")

        with patch.object(dl, "_fetch_all_pages", return_value=[]), \
             patch.object(dl, "_download_image", return_value=False):
            dl.run()

        assert (tmp_path / "output" / "albums").is_dir()
        assert (tmp_path / "output" / "artists").is_dir()


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestSafeFilename:
    def test_strips_invalid_chars(self):
        assert "/" not in _safe_filename("AC/DC")
        assert ":" not in _safe_filename("Led Zeppelin: IV")

    def test_preserves_valid_chars(self):
        result = _safe_filename("Dream Theater")
        assert result == "Dream Theater"

    def test_handles_empty_string(self):
        assert _safe_filename("") == ""


class TestUrlExtension:
    def test_jpg(self):
        assert _url_extension("http://example.com/image.jpg") == ".jpg"

    def test_png(self):
        assert _url_extension("http://example.com/image.png") == ".png"

    def test_defaults_to_jpg_when_no_extension(self):
        assert _url_extension("http://example.com/image") == ".jpg"

    def test_ignores_query_string(self):
        assert _url_extension("http://example.com/art.jpg?size=xl") == ".jpg"
