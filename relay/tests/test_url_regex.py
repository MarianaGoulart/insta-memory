import pytest
from main import _INSTAGRAM_RE


@pytest.mark.parametrize("url,should_match", [
    ("https://www.instagram.com/reel/ABC123/", True),
    ("https://instagram.com/p/XYZ789", True),
    ("https://www.instagram.com/tv/DEF456/", True),
    ("https://www.instagram.com/stories/user/123/", False),
    ("https://twitter.com/reel/ABC", False),
    # Domain must match exactly — a URL that embeds instagram.com as a path must not match
    ("http://evil.com/instagram.com/reel/x", False),
    ("", False),
])
def test_url_regex(url, should_match):
    match = _INSTAGRAM_RE.search(url)
    assert bool(match) == should_match
