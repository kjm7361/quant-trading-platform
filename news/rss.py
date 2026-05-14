import xml.etree.ElementTree as ET
from urllib.parse import quote
from urllib.request import urlopen, Request


def _fetch_xml(url, timeout=10):
    req = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def google_news_rss(query, hl="en-US", gl="US", ceid="US:en"):
    """
    Returns a list of dicts: [{title, link, source, published}]
    Uses Google News RSS (no API key required).
    """
    q = quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"

    xml_bytes = _fetch_xml(url)
    root = ET.fromstring(xml_bytes)

    items = []
    for item in root.findall("./channel/item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        pub = item.findtext("pubDate") or ""

        # Source sometimes appears in title like: "Headline - Source"
        source = ""
        if " - " in title:
            parts = title.rsplit(" - ", 1)
            if len(parts) == 2:
                title, source = parts[0], parts[1]

        items.append({
            "title": title.strip(),
            "link": link.strip(),
            "source": source.strip(),
            "published": pub.strip()
        })

    return items


def market_headlines():
    # Broad market query
    return google_news_rss("US stock market OR S&P 500 OR Nasdaq OR Dow Jones OR Federal Reserve")


def ticker_headlines(ticker):
    t = str(ticker).strip().upper()
    # Examples: "AAPL stock", "TSLA earnings"
    return google_news_rss(f"{t} stock OR {t} earnings OR {t} guidance OR {t} analyst")
