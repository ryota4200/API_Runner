from __future__ import annotations

import ipaddress
import json
import socket
from typing import Any
from urllib.parse import urlparse

import requests
from flask import Flask, render_template_string, request


app = Flask(__name__)
DEFAULT_API_URL = "https://api.github.com"
ALLOWED_SCHEMES = {"https"}
ALLOWED_CONTENT_TYPES = {"application/json", "text/plain", "text/csv"}
MAX_RESPONSE_BYTES = 1024 * 1024
RESPONSE_CHUNK_SIZE = 8192


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


class URLValidationError(ValueError):
    pass


class ResponseValidationError(ValueError):
    pass


def validate_api_url(url: str) -> str:
    url = url.strip()
    parsed_url = urlparse(url)

    if parsed_url.scheme not in ALLOWED_SCHEMES:
        raise URLValidationError("https のURLのみ実行できます。")

    if not parsed_url.hostname:
        raise URLValidationError("ホスト名を含むURLを入力してください。")

    if parsed_url.username or parsed_url.password:
        raise URLValidationError("認証情報を含むURLは使用できません。")

    try:
        port = parsed_url.port or 443
    except ValueError as error:
        raise URLValidationError("ポート番号が不正です。") from error

    try:
        address_info = socket.getaddrinfo(parsed_url.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise URLValidationError(f"ホスト名を解決できません: {parsed_url.hostname}") from error

    resolved_ips = {info[4][0] for info in address_info}
    for resolved_ip in resolved_ips:
        ip_address = ipaddress.ip_address(resolved_ip)
        if not ip_address.is_global:
            raise URLValidationError(
                "localhost、プライベートIP、リンクローカルIPなどの内部アドレスにはアクセスできません。"
            )

    return url


def get_content_type(response: requests.Response) -> str:
    return response.headers.get("content-type", "").split(";", 1)[0].strip().lower()


def validate_response_headers(response: requests.Response) -> str:
    content_type = get_content_type(response)
    if not content_type:
        raise ResponseValidationError("Content-Type がないレスポンスは受け付けません。")

    is_allowed_content_type = content_type in ALLOWED_CONTENT_TYPES or content_type.endswith("+json")
    if not is_allowed_content_type:
        raise ResponseValidationError(f"対象外の Content-Type です: {content_type}")

    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            content_length_bytes = int(content_length)
        except ValueError as error:
            raise ResponseValidationError("Content-Length が不正です。") from error

        if content_length_bytes < 0:
            raise ResponseValidationError("Content-Length が不正です。")

        if content_length_bytes > MAX_RESPONSE_BYTES:
            raise ResponseValidationError(
                f"レスポンスが大きすぎます。最大 {MAX_RESPONSE_BYTES} bytes までです。"
            )

    return content_type


def read_limited_response(response: requests.Response) -> bytes:
    chunks = []
    total_bytes = 0

    for chunk in response.iter_content(chunk_size=RESPONSE_CHUNK_SIZE):
        if not chunk:
            continue

        total_bytes += len(chunk)
        if total_bytes > MAX_RESPONSE_BYTES:
            raise ResponseValidationError(
                f"レスポンスが大きすぎます。最大 {MAX_RESPONSE_BYTES} bytes までです。"
            )

        chunks.append(chunk)

    return b"".join(chunks)


def decode_response_body(response: requests.Response, body: bytes) -> str:
    encoding = response.encoding or "utf-8"
    return body.decode(encoding, errors="replace")


def format_response_body(response: requests.Response, body: bytes) -> str:
    content_type = get_content_type(response)
    body_text = decode_response_body(response, body)

    if content_type == "application/json" or content_type.endswith("+json"):
        payload: Any = json.loads(body_text)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    return body_text


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    url = request.form.get("url", DEFAULT_API_URL)
    result = None

    if request.method == "POST":
        try:
            validated_url = validate_api_url(url)
            with requests.get(
                validated_url,
                timeout=(3, 10),
                allow_redirects=False,
                stream=True,
            ) as response:
                validate_response_headers(response)
                response_body = read_limited_response(response)
                formatted_body = format_response_body(response, response_body)

            result = {
                "title": "実行結果",
                "status_code": response.status_code,
                "body": formatted_body,
                "error": response.status_code >= 400,
            }
        except URLValidationError as error:
            result = {
                "title": "URLエラー",
                "status_code": None,
                "body": str(error),
                "error": True,
            }
        except ResponseValidationError as error:
            result = {
                "title": "レスポンスエラー",
                "status_code": None,
                "body": str(error),
                "error": True,
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
    app.run(host="127.0.0.1", port=5000, debug=False)
