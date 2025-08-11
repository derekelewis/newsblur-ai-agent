import main
from models import Feed, Story


def test_summarize_stories_builds_prompt_and_returns_mock(monkeypatch):
    captured = {}

    class Msg:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, content):
            self.message = Msg(content)

    class Resp:
        def __init__(self, content):
            self.choices = [Choice(content)]

    class Completions:
        def create(self, model, messages, max_completion_tokens, temperature):
            captured["messages"] = messages
            return Resp("SUMMARY")

    class Chat:
        def __init__(self):
            self.completions = Completions()

    class OpenAIStub:
        def __init__(self):
            self.chat = Chat()

    # Replace the real OpenAI client with a stub
    monkeypatch.setattr(main, "openai", OpenAIStub())

    feed = Feed(id="1", title="My Feed")
    feed.stories = [
        Story(hash="h1", title="Title A", content_text="Content A", permalink="http://example.com/a")
    ]

    result = main.summarize_stories([feed], model_id="test-model")

    assert result == "SUMMARY"
    messages = captured["messages"]
    # System prompt present
    assert messages[0]["role"] == "system"
    # User content includes feed title and story title
    user_contents = "\n".join(m["content"] for m in messages if m["role"] == "user")
    assert "My Feed" in user_contents
    assert "Title: Title A" in user_contents

