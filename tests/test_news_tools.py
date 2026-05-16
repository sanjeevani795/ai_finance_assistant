from unittest.mock import patch

from agents.news_tools import fetch_rss_headlines


def test_fetch_rss_parses_minimal_feed() -> None:
    xml = b"""<?xml version='1.0'?><rss><channel>
    <title>Channel Title Long Enough</title>
    <item><title>First market headline example here</title></item>
    <item><title>Second headline also long text</title></item>
    </channel></rss>"""

    class Resp:
        def read(self):
            return xml

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    with patch("agents.news_tools.urllib.request.urlopen", return_value=Resp()):
        titles = fetch_rss_headlines("http://example.com/feed.xml", timeout=1.0, max_items=5)
    assert any("First market" in t for t in titles)
