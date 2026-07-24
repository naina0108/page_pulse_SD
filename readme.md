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
```

Then open http://localhost:5000 in a browser.

### Run tests
```bash
python -m unittest test_app.py -v
```

Tests mock all network calls, so no internet connection is required to run them.


### Deploy (Render, free tier)

1. Push this repo to GitHub.
2. On render.com, choose **New → Blueprint** and point it at the repo (it will read `render.yaml` automatically).
If Blueprint isn't available: **New → Web Service** → connect the repo → Build Command `pip install -r requirements.txt` → Start Command `gunicorn app:app.`
3. Deploy. Render gives you a live `https://<your-app>.onrender.com` URL.

---

# API Contract
POST `/api/audit`

### Request body
```Json
{ "url": "https://example.com" }
```

### Success — `200 OK`
```Json
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
```

**Error responses** — always JSON, always a clean status code, never a stack trace:

Status | `error` value | When
--- | --- | ---
`400` | `invalid_url` | URL missing or not a valid http(s) URL
`502` | `connection_failed` | DNS/connection failure
`504` | `timeout` | Target page didn't respond in time
`422` | `non_html_response` | URL returned non-HTML content (e.g. JSON, an image)
`500` | `parse_failed` | Page fetched but couldn't be parsed

Every error response includes a human-readable message field for the frontend to display directly.

--- 

# Design Decisions
1. Parsing logic is a pure function, separate from the route.

`build_report(html, status_code, response_time_ms)` takes plain strings/numbers in and returns a plain dict out — it doesn't touch `requests` or Flask at all. This is what makes the test suite possible without mocking half the internet: the parsing tests just hand it raw HTML strings. The network and error-handling concerns live only in the `/api/audit` route.

2. Validate the URL before making any network call.
   
`is_valid_url()` checks the scheme and netloc up front and returns `400` immediately for garbage input. The alternative — letting `requests` throw and catching that — would work, but it means every malformed string still triggers a real network attempt, which is slower and behaves inconsistently across malformed inputs (some raise, some don't). Failing fast on obviously-bad input is both quicker and more predictable.

3. Distinguish failure types with different HTTP status codes instead of one generic `"error."`
   
A timeout `(504)`, a DNS failure `(502)`, and a non-HTML response `(422)` are different problems with different likely fixes for the person hitting the API. Collapsing them into a single `400/500` would satisfy "never crash" but would make the API harder to build against — a frontend (or another API consumer) can't tell "try again later" apart from "that URL will never work" without the distinct codes.

---
# Tech Stack

- Backend: Flask + requests + BeautifulSoup4
- Frontend: Vanilla HTML/CSS/JS (no build step, no framework)
- Tests: Python's built-in unittest, with unittest.mock for network isolation
- Deploy target: Render (free tier)


