import main
from models import Feed, Story


class Resp:
    def __init__(self, status_code=200, json_data=None, content=b""):
        self.status_code = status_code
        self._json = json_data or {}
        self.content = content

    def json(self):
        return self._json


def test_authenticate_newsblur_success_and_failure(monkeypatch):
    calls = {"post": []}

    class Sess:
        def post(self, url, data=None, **kwargs):
            calls["post"].append((url, data))
            if data.get("password") == "ok":
                return Resp(200)
            return Resp(403)

    monkeypatch.setattr(main.requests, "Session", lambda: Sess())

    s_ok = main.authenticate_newsblur("u", "ok")
    assert s_ok is not None

    s_bad = main.authenticate_newsblur("u", "bad")
    assert s_bad is None


def test_fetch_feeds_parses_and_handles_error(monkeypatch):
    class Sess:
        def __init__(self, resp):
            self._resp = resp

        def get(self, url, **kwargs):
            return self._resp

    data = {"feeds": {"1": {"feed_title": "Tech"}, "2": {"feed_title": "News"}}}
    feeds = main.fetch_feeds(Sess(Resp(200, data)))
    assert [f.title for f in feeds] == ["Tech", "News"]

    none = main.fetch_feeds(Sess(Resp(500)))
    assert none is None


def test_fetch_feed_stories_with_fallback_and_truncate(monkeypatch):
    # Prepare a feed
    feed = Feed(id="10", title="Site")

    # Raw stories: first has short content to trigger fetch_webpage, second long to truncate
    raw = {
        "stories": [
            {
                "story_title": "A",
                "story_content": "<p>short</p>",
                "story_permalink": "http://example.com/a",
                "story_hash": "h1",
            },
            {
                "story_title": "B",
                "story_content": "<p>" + ("x" * (main.MAX_CONTENT_LENGTH + 50)) + "</p>",
                "story_permalink": "http://example.com/b",
                "story_hash": "h2",
            },
        ]
    }

    class Sess:
        def get(self, url, params=None, **kwargs):
            return Resp(200, raw)

    # Force fetch_webpage to return a fallback body
    monkeypatch.setattr(main, "fetch_webpage", lambda url: "fetched content that is long enough")

    stories = main.fetch_feed_stories(Sess(), feed)
    assert len(stories) == 2
    a, b = stories
    assert a.title == "A" and "fetched content" in a.content_text
    assert len(b.content_text) == main.MAX_CONTENT_LENGTH


def test_fetch_feed_stories_none_and_empty(monkeypatch):
    feed = Feed(id="11", title="Empty")

    class Sess:
        def __init__(self, status, body):
            self._status = status
            self._body = body

        def get(self, url, params=None, **kwargs):
            return Resp(self._status, self._body)

    none = main.fetch_feed_stories(Sess(500, {}), feed)
    assert none is None

    empty = main.fetch_feed_stories(Sess(200, {"stories": []}), feed)
    assert empty == []


def test_mark_stories_as_read_posts_hashes(monkeypatch):
    posted = []

    class Sess:
        def post(self, url, data=None, **kwargs):
            posted.append((url, list(data)))
            return Resp(200)

    feed = Feed(id="1", title="X")
    feed.stories = [Story("h1", "t1", "c1", "u1"), Story("h2", "t2", "c2", "u2")]
    main.mark_stories_as_read(Sess(), [feed])

    assert posted and posted[0][0].endswith("mark_story_hashes_as_read")
    # Data should be pairs of ("story_hash", value)
    assert posted[0][1] == [("story_hash", "h1"), ("story_hash", "h2")]


def test_send_to_slack_success_and_error(monkeypatch):
    calls = []

    def fake_post(url, json=None, headers=None, **kwargs):
        calls.append((url, json))
        # First call success, second fails
        return Resp(200 if len(calls) == 1 else 500)

    monkeypatch.setattr(main.requests, "post", fake_post)

    main.send_to_slack("hello", "https://hooks.slack.test/abc")
    main.send_to_slack("hello", "https://hooks.slack.test/abc")

    assert len(calls) == 2
    assert calls[0][0].startswith("https://hooks.slack.test/")


def test_fetch_webpage_success_and_failure(monkeypatch):
    def get_ok(url, **kwargs):
        return Resp(200, json_data=None, content=b"<p>ok</p>")

    def get_fail(url, **kwargs):
        return Resp(404)

    monkeypatch.setattr(main.requests, "get", get_ok)
    assert "ok" in main.fetch_webpage("http://x")

    monkeypatch.setattr(main.requests, "get", get_fail)
    assert main.fetch_webpage("http://x") is None
