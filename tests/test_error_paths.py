import os
import main
import requests
from models import Feed, Story


class BadJsonResp:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def json(self):
        raise ValueError("bad json")


def test_send_to_slack_missing_url_and_exception(monkeypatch):
    # Missing URL path
    main.send_to_slack("hi", None)

    # Exception path
    def boom(*args, **kwargs):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(main.requests, "post", boom)
    main.send_to_slack("hi", "https://hooks.slack.test/x")


def test_fetch_webpage_request_exception(monkeypatch):
    monkeypatch.setattr(
        main.requests,
        "get",
        lambda *a, **k: (_ for _ in ()).throw(requests.exceptions.RequestException("x")),
    )
    assert main.fetch_webpage("http://x") is None


def test_fetch_feeds_request_exception_and_bad_json(monkeypatch):
    class SessA:
        def get(self, url, **kwargs):
            raise requests.exceptions.RequestException("net")

    assert main.fetch_feeds(SessA()) is None

    class SessB:
        def get(self, url, **kwargs):
            return BadJsonResp(200)

    assert main.fetch_feeds(SessB()) is None


def test_fetch_feed_stories_request_exception_and_bad_json(monkeypatch):
    feed = Feed(id="1", title="T")

    class SessA:
        def get(self, url, **kwargs):
            raise requests.exceptions.RequestException("net")

    assert main.fetch_feed_stories(SessA(), feed) is None

    class SessB:
        def get(self, url, **kwargs):
            return BadJsonResp(200)

    assert main.fetch_feed_stories(SessB(), feed) is None


def test_mark_stories_as_read_exception(monkeypatch):
    class Sess:
        def post(self, url, data=None, **kwargs):
            raise requests.exceptions.RequestException("bad")

    feed = Feed(id="1", title="X")
    feed.stories = [Story("h1", "t1", "c1", "u1")]
    # Should not raise
    main.mark_stories_as_read(Sess(), [feed])


def test_clean_html_variants(monkeypatch):
    assert main.clean_html(None) == ""
    assert "ok" in main.clean_html(b"<p>ok</p>")

    # Force BeautifulSoup to raise to hit error branch
    orig_bs = main.BeautifulSoup

    def raiser(*a, **k):
        raise RuntimeError("bs error")

    monkeypatch.setattr(main, "BeautifulSoup", raiser)
    try:
        assert main.clean_html("<p>x</p>") == ""
    finally:
        monkeypatch.setattr(main, "BeautifulSoup", orig_bs)

