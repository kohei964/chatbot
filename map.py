import urllib.parse

def make_map_url(query: str) -> str:
    base = "https://www.google.com/maps/search/?api=1&query="
    return base + urllib.parse.quote_plus(query)

