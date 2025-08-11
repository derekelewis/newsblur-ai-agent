import os
import main
from models import Feed, Story


def test_main_missing_env(monkeypatch):
    # Clear required env vars
    for k in [
        "NEWSBLUR_USERNAME",
        "NEWSBLUR_PASSWORD",
        "MODEL_ID",
        "SLACK_WEBHOOK_URL",
    ]:
        monkeypatch.delenv(k, raising=False)

    # Should exit early without raising
    main.main()


def test_main_happy_path(monkeypatch):
    # Provide required env
    monkeypatch.setenv("NEWSBLUR_USERNAME", "u")
    monkeypatch.setenv("NEWSBLUR_PASSWORD", "p")
    monkeypatch.setenv("MODEL_ID", "m")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.test/x")
    monkeypatch.setenv("MARK_STORIES_AS_READ", "true")

    # Stub dependencies
    class DummySession:
        pass

    called = {"send": 0, "mark": 0}

    monkeypatch.setattr(main, "authenticate_newsblur", lambda u, p: DummySession())
    monkeypatch.setattr(main, "fetch_feeds", lambda s: [Feed(id="1", title="T")])
    monkeypatch.setattr(
        main,
        "fetch_feed_stories",
        lambda s, f: [Story(hash="h", title="t", content_text="c", permalink="u")],
    )
    monkeypatch.setattr(main, "summarize_stories", lambda feeds, model_id: "SUMMARY")

    def fake_send(summary, url):
        called["send"] += 1

    def fake_mark(session, feeds):
        called["mark"] += 1

    monkeypatch.setattr(main, "send_to_slack", fake_send)
    monkeypatch.setattr(main, "mark_stories_as_read", fake_mark)

    main.main()

    assert called["send"] == 1
    assert called["mark"] == 1

