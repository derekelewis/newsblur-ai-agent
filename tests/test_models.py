from models import Feed, Story


def test_feed_defaults():
    feed = Feed(id="1", title="Tech")
    assert feed.stories == []


def test_story_dataclass():
    story = Story(hash="h1", title="T", content_text="C", permalink="http://x")
    assert story.title == "T"
    assert story.permalink.startswith("http")

