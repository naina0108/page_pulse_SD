# Page Pulse

A small web tool that audits any URL — HTTP status, response time, page title, meta description, H1 count, images missing alt text, and approximate word count.

Built for the Digital Heroes SDE internship qualification task ([digitalheroesco.com](https://digitalheroesco.com)).

**Live demo:** _add your deployed URL here_
**Repo:** _add your GitHub repo link here_

---

## Setup

### Run locally
```bash
pip install -r requirements.txt
python app.py

Then open http://localhost:5000 in a browser.

### Run tests
```bash
python -m unittest test_app.py -v

Tests mock all network calls, so no internet connection is required to run them.
Deploy (Render, free tier)
1. Push this repo to GitHub.
2. On render.com, choose New → Blueprint and point it at the repo (it will read render.yaml automatically).
If Blueprint isn't available: New → Web Service → connect the repo → Build Command pip install -r requirements.txt → Start Command gunicorn app:app.
3. Deploy. Render gives you a live https://<your-app>.onrender.com URL.

API Contract
POST /api/audit
Request body
Json
{ "url": "https://example.com" }

Success — 200 OK
Json
{
  "http_status": 200,
  "response_time_ms": 184,
  "title": "Example Domain",
  "meta_description": "An example page",
  "h1_count": 1,
  "images_total": 3,
  "images_missing_alt": 1,
  "word_count_approx": 42
}

Error responses — always JSON, always a clean status code, never a stack trace:
Status
error value
When
400
invalid_url
URL missing or not a valid http(s) URL
502
connection_failed
DNS/connection failure
504
timeout
Target page didn't respond in time
422
non_html_response
URL returned non-HTML content (e.g. JSON, an image)
500
parse_failed
Page fetched but couldn't be parsed


