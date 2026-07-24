"""
Tests for Page Pulse.

Covers:
  1. Happy path - a normal HTML page is parsed and reported correctly.
  2. Failure case - invalid URL is rejected before any network call.
  3. Failure case - a request timeout is handled with a clean JSON error, not a crash.

Run with:  python -m unittest test_app.py -v
(No external services or network access required - requests.get is mocked.)
"""

import unittest
from unittest.mock import patch, Mock

import requests

from app import app, is_valid_url, build_report


class ParsingLogicTests(unittest.TestCase):
    """Unit tests for the pure parsing function build_report()."""

    def test_happy_path_full_page(self):
        html = """
        <html><head>
            <title>Sample Blog</title>
            <meta name="description" content="A blog about testing">
        </head><body>
            <h1>Welcome</h1>
            <img src="a.png" alt="a photo">
            <img src="b.png" alt="">
            <img src="c.png">
            <p>Some sample text for the word counter to chew on.</p>
        </body></html>
        """
        report = build_report(html, 200, 150)

        self.assertEqual(report["http_status"], 200)
        self.assertEqual(report["response_time_ms"], 150)
        self.assertEqual(report["title"], "Sample Blog")
        self.assertEqual(report["meta_description"], "A blog about testing")
        self.assertEqual(report["h1_count"], 1)
        self.assertEqual(report["images_total"], 3)
        # two images have no usable alt text: empty alt="" and missing alt
        self.assertEqual(report["images_missing_alt"], 2)
        self.assertGreater(report["word_count_approx"], 0)

    def test_missing_title_and_meta_do_not_crash(self):
        html = "<html><body><p>No head tags here.</p></body></html>"
        report = build_report(html, 200, 50)
        self.assertIsNone(report["title"])
        self.assertIsNone(report["meta_description"])
        self.assertEqual(report["h1_count"], 0)


class InvalidUrlTests(unittest.TestCase):
    """URL validation should reject bad input before any network call happens."""

    def test_is_valid_url(self):
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("http://example.com/page"))
        self.assertFalse(is_valid_url("not-a-url"))
        self.assertFalse(is_valid_url("ftp://example.com"))
        self.assertFalse(is_valid_url(""))
        self.assertFalse(is_valid_url(None))

    def test_api_rejects_invalid_url(self):
        client = app.test_client()
        resp = client.post("/api/audit", json={"url": "not-a-url"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], "invalid_url")

    def test_api_rejects_missing_url(self):
        client = app.test_client()
        resp = client.post("/api/audit", json={})
        self.assertEqual(resp.status_code, 400)


class NetworkFailureTests(unittest.TestCase):
    """The API must degrade gracefully - JSON errors, never a 500 crash or hang."""

    @patch("app.requests.get")
    def test_timeout_returns_504(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        client = app.test_client()
        resp = client.post("/api/audit", json={"url": "https://slow-site.example"})
        self.assertEqual(resp.status_code, 504)
        self.assertEqual(resp.get_json()["error"], "timeout")

    @patch("app.requests.get")
    def test_connection_error_returns_502(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()
        client = app.test_client()
        resp = client.post("/api/audit", json={"url": "https://does-not-resolve.example"})
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.get_json()["error"], "connection_failed")

    @patch("app.requests.get")
    def test_non_html_response_returns_422(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.text = "{}"
        mock_get.return_value = mock_resp

        client = app.test_client()
        resp = client.post("/api/audit", json={"url": "https://api.example.com/data"})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.get_json()["error"], "non_html_response")

    @patch("app.requests.get")
    def test_full_happy_path_through_api(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.text = "<html><head><title>Hi</title></head><body><h1>Hi</h1></body></html>"
        mock_get.return_value = mock_resp

        client = app.test_client()
        resp = client.post("/api/audit", json={"url": "https://example.com"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["title"], "Hi")
        self.assertEqual(data["h1_count"], 1)


if __name__ == "__main__":
    unittest.main()
