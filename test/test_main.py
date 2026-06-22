import socket
import pytest
import main

@pytest.fixture()
def client():
    """Flaskのテストクライアントを返す。"""
    main.app.config.update(TESTING=True)

    with main.app.test_client() as test_client:
        yield test_client

def test_index_returns_success(client):
    """トップページが正常に表示されることを確認する"""
    response = client.get('/')
    
    assert response.status_code == 200
    assert b"API Runner" in response.data

def test_validate_public_https_url(monkeypatch):
    """公開IPを返すHTTPS URLが許可されていることを確認する。"""
    address_info = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("93.184.216.34", 443),
        )
    ]

    monkeypatch.setattr(main.socket, "getaddrinfo", lambda *args, **kwargs: address_info)

url = "https://example.com/api"

assert main.validate_api_url(url) == url

def test_reject_http_url():
    """HTTP URLが拒否されることを確認する。"""
    with pytest.raises(main.URLValidationError, match="https"):
        main.validate_api_url("http://example.com/api")

def test_reject_private_ip(monkeypatch):
    """プライベートIPへの接続が拒否されることを確認する。"""
    address_info = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("192.168.1.10", 443),
        )
    ]
    monkeypatch.setattr(main.socket, "getaddrinfo", lambda *args, **kwargs: address_info)

    with pytest.raises(main.URLValidationError, match="内部アドレス"):
        main.validate_api_url("https://internal.example.com")