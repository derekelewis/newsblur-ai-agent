from main import clean_html


def test_clean_html_removes_tags_and_scripts():
    html = "<div><h1>Hi</h1><p>World <a href='#'>link</a></p><script>bad()</script></div>"
    text = clean_html(html)
    assert "<" not in text and ">" not in text
    assert "Hi" in text and "World" in text and "link" in text

