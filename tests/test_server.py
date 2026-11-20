import json
import urllib.error
import urllib.request

import pytest

from bp.server import Outcome, PrompterServer

CFG = {"mode": "write", "token": "tok-123", "title": None, "version": "0"}


@pytest.fixture
def srv():
    server = PrompterServer(dict(CFG), "127.0.0.1", 0)
    server.start()
    yield server
    server.close()


def url(srv, path):
    return f"http://127.0.0.1:{srv.port}{path}"


def get(srv, path):
    try:
        with urllib.request.urlopen(url(srv, path), timeout=5) as res:
            return res.status, res.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode()


def post(srv, path, obj, raw=None):
    data = raw if raw is not None else json.dumps(obj).encode()
    req = urllib.request.Request(
        url(srv, path), data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as err:
        body = err.read().decode()
        return err.code, (json.loads(body) if body else {})


def test_ephemeral_port_assigned(srv):
    assert srv.port > 0 and srv.token == "tok-123"


def test_get_without_token_is_403(srv):
    assert get(srv, "/")[0] == 403


def test_get_with_token_serves_page(srv):
    status, body = get(srv, "/?k=tok-123")
    assert status == 200 and 'id="bp-config"' in body


def test_get_unknown_path_with_token_is_404(srv):
    assert get(srv, "/nope?k=tok-123")[0] == 404


def test_favicon_without_token_is_403_and_server_still_waits(srv):
    assert get(srv, "/favicon.ico")[0] == 403
    assert post(srv, "/answer", {"k": "tok-123", "text": "still here"})[0] == 200
    assert srv.wait(1) == Outcome("answer", "still here")


def test_answer_sets_outcome(srv):
    status, body = post(srv, "/answer", {"k": "tok-123", "text": "héllo 🚀"})
    assert status == 200 and body == {"ok": True}
    assert srv.wait(1) == Outcome("answer", "héllo 🚀")


def test_cancel_outcome(srv):
    assert post(srv, "/cancel", {"k": "tok-123"})[0] == 200
    assert srv.wait(1) == Outcome("cancel", None)


def test_second_post_is_409(srv):
    assert post(srv, "/answer", {"k": "tok-123", "text": "first"})[0] == 200
    status, body = post(srv, "/answer", {"k": "tok-123", "text": "second"})
    assert status == 409 and body["ok"] is False
    assert srv.wait(1) == Outcome("answer", "first")


def test_wrong_token_post_is_403_and_does_not_resolve(srv):
    assert post(srv, "/answer", {"k": "nope", "text": "x"})[0] == 403
    assert srv.wait(0.2) == Outcome("timeout", None)


def test_missing_token_post_is_403(srv):
    assert post(srv, "/answer", {"text": "x"})[0] == 403


def test_malformed_json_is_400_and_server_keeps_waiting(srv):
    assert post(srv, "/answer", None, raw=b"{not json")[0] == 400
    assert post(srv, "/answer", {"k": "tok-123", "text": 5})[0] == 400
    assert post(srv, "/answer", {"k": "tok-123"})[0] == 400
    assert post(srv, "/answer", {"k": "tok-123", "text": "ok now"})[0] == 200
    assert srv.wait(1) == Outcome("answer", "ok now")


def test_large_answer_round_trips(srv):
    text = "x" * (1024 * 1024)
    assert post(srv, "/answer", {"k": "tok-123", "text": text})[0] == 200
    assert srv.wait(2).text == text


def test_timeout_outcome(srv):
    assert srv.wait(0.2) == Outcome("timeout", None)


def test_oversized_content_length_is_rejected_before_reading(srv):
    import socket
    with socket.create_connection(("127.0.0.1", srv.port), timeout=5) as sock:
        sock.sendall(
            b"POST /answer HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
            b"Content-Length: 104857600\r\n\r\n"
        )
        head = sock.recv(64)
    assert head.startswith(b"HTTP/1.0 413") or head.startswith(b"HTTP/1.1 413")
    assert srv.wait(0.2) == Outcome("timeout", None)


def test_fixed_port_can_be_reused_immediately():
    first = PrompterServer(dict(CFG), "127.0.0.1", 0)
    first.start()
    port = first.port
    assert post(first, "/answer", {"k": "tok-123", "text": "bye"})[0] == 200
    first.wait(1)
    second = PrompterServer(dict(CFG), "127.0.0.1", port)
    assert second.port == port
    second.close()
