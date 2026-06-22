# API Runner

API Runner is a small Flask web app for sending GET requests to a URL from a browser and viewing the response on the same page.

## Features

- Enter any API URL in the web form
- Run the request with one button
- Display the HTTP status code and response body
- Pretty-print JSON responses
- Show request errors on the page

## Requirements

- Python 3.10 or later
- Tested with Python 3.14
- pip

This project expects commands to use the local virtual environment at `.venv`.

## Setup

Create and activate a virtual environment if it does not already exist:

```bash
python3 -m venv .venv
```

Install dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

## Run

Start the Flask development server:

```bash
.venv/bin/python main.py
```

Open the app in your browser:

```text
http://127.0.0.1:5000
```

## Usage

1. Enter an API URL, such as `https://api.github.com`.
2. Click `実行`.
3. Check the response displayed below the form.

## Files

- `main.py`: Flask application and web UI
- `requirements.txt`: Python dependencies
- `.gitignore`: Local files excluded from Git
