"""
Page Pulse — a small web tool that audits any URL.

Built for Digital Heroes Training Task (digitalheroesco.com)

Endpoints:
    GET  /                -> serves the frontend
    POST /api/audit       -> accepts {"url": "..."} and returns a JSON audit report
"""

import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")

# --- config -----------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 8
USER_AGENT = "PagePulse/1.0 (+https://digitalheroesco.com)"


# --- helpers ------------------------------------------------------------
def is_valid_url(url: str) -> bool:
    """A URL is valid for our purposes if it has an http/https scheme and a netloc."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def build_report(html: str, status_code: int, response_time_ms: int) -> dict:
    """Parse HTML and build the audit report. Pure function -> easy to unit test."""
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_tag.get("content", "").strip() if meta_tag else None

    h1_count = len(soup.find_all("h1"))

    images = soup.find_all("img")
    images_missing_alt = sum(
        1 for img in images if not img.get("alt", "").strip()
    )

    # approximate word count: strip script/style, then split on whitespace
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    word_count = len(text.split())

    return {
        "http_status": status_code,
        "response_time_ms": response_time_ms,
        "title": title,
        "meta_description": meta_description,
        "h1_count": h1_count,
        "images_total": len(images),
        "images_missing_alt": images_missing_alt,
        "word_count_approx": word_count,
    }


# --- routes -------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/audit", methods=["POST"])
def audit():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()

    if not is_valid_url(url):
        return jsonify({
            "error": "invalid_url",
            "message": "Please provide a valid http:// or https:// URL.",
        }), 400

    start = time.perf_counter()
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
    except requests.exceptions.Timeout:
        return jsonify({
            "error": "timeout",
            "message": f"The page did not respond within {REQUEST_TIMEOUT_SECONDS} seconds.",
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "connection_failed",
            "message": "Could not connect to that URL. Check the address and try again.",
        }), 502
    except requests.exceptions.RequestException as exc:
        return jsonify({
            "error": "request_failed",
            "message": str(exc),
        }), 502

    response_time_ms = round((time.perf_counter() - start) * 1000)

    content_type = resp.headers.get("Content-Type", "")
    if "text/html" not in content_type.lower():
        return jsonify({
            "error": "non_html_response",
            "message": f"That URL returned '{content_type or 'unknown'}', not an HTML page.",
            "http_status": resp.status_code,
            "response_time_ms": response_time_ms,
        }), 422

    try:
        report = build_report(resp.text, resp.status_code, response_time_ms)
    except Exception as exc:  # last-resort guard: never crash, always respond
        return jsonify({
            "error": "parse_failed",
            "message": "The page was fetched but could not be parsed.",
            "detail": str(exc),
        }), 500

    return jsonify(report), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
