from __future__ import annotations

import json
from typing import Any

import requests
from flask import Flask, render_template_string, request


app = Flask(__name__)


PAGE_TEMPLATE = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>API Runner</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Arial, "Hiragino Sans", "Yu Gothic", sans-serif;
      color: #1f2937;
      background: #f4f7f9;
    }

    body {
      margin: 0;
    }

    main {
      width: min(920px, calc(100% - 32px));
      margin: 48px auto;
    }

    h1 {
      font-size: 28px;
      margin: 0 0 24px;
    }

    form {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      margin-bottom: 24px;
    }

    input[type="url"] {
      min-width: 0;
      height: 44px;
      padding: 0 14px;
      border: 1px solid #b7c2cc;
      border-radius: 6px;
      font-size: 16px;
      background: #ffffff;
      color: #111827;
    }

    button {
      height: 44px;
      padding: 0 18px;
      border: 0;
      border-radius: 6px;
      font-size: 16px;
      font-weight: 700;
      color: #ffffff;
      background: #0f766e;
      cursor: pointer;
    }

    button:hover {
      background: #115e59;
    }

    .result {
      border: 1px solid #d1d9e0;
      border-radius: 8px;
      background: #ffffff;
      overflow: hidden;
    }

    .result-header {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: space-between;
      padding: 14px 16px;
      border-bottom: 1px solid #d1d9e0;
      background: #eef3f6;
      font-weight: 700;
    }

    pre {
      margin: 0;
      padding: 16px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-size: 14px;
      line-height: 1.5;
    }

    .error {
      border-color: #fecaca;
    }

    .error .result-header {
      color: #991b1b;
      background: #fee2e2;
      border-bottom-color: #fecaca;
    }

    @media (max-width: 640px) {
      main {
        margin: 28px auto;
      }

      form {
        grid-template-columns: 1fr;
      }

      button {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <main>
    <h1>API Runner</h1>

    <form method="post">
      <input
        type="url"
        name="url"
        value="{{ url }}"
        placeholder="https://api.github.com"
        required
      >
      <button type="submit">実行</button>
    </form>

    {% if result %}
      <section class="result{% if result.error %} error{% endif %}">
        <div class="result-header">
          <span>{{ result.title }}</span>
          {% if result.status_code %}
            <span>Status: {{ result.status_code }}</span>
          {% endif %}
        </div>
        <pre>{{ result.body }}</pre>
      </section>
    {% endif %}
  </main>
</body>
</html>
"""


def format_response_body(response: requests.Response) -> str:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        payload: Any = response.json()
        return json.dumps(payload, ensure_ascii=False, indent=2)

    return response.text[:5000]


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    url = request.form.get("url", "https://api.github.com")
    result = None

    if request.method == "POST":
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = {
                "title": "実行結果",
                "status_code": response.status_code,
                "body": format_response_body(response),
                "error": False,
            }
        except requests.RequestException as error:
            result = {
                "title": "エラー",
                "status_code": None,
                "body": str(error),
                "error": True,
            }
        except ValueError as error:
            result = {
                "title": "レスポンスの解析エラー",
                "status_code": None,
                "body": str(error),
                "error": True,
            }

    return render_template_string(PAGE_TEMPLATE, url=url, result=result)


if __name__ == "__main__":
    app.run(debug=True)
