"""Step 1 の実験コードを、アプリから使える形にしたもの。
楽天・Yahoo! の API を叩いて、生の JSON（dict）を返す。"""
import requests

RAKUTEN_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
YAHOO_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"


def fetch_rakuten(keyword: str, app_id: str):
    """(data, error) を返す。成功したら error は None、失敗したら data が None。"""
    try:
        r = requests.get(
            RAKUTEN_URL,
            params={
                "format": "json",
                "applicationId": app_id,
                "keyword": keyword,
                "hits": 30,  # 1回で取る件数。v1 はページングしない
                "sort": "standard",
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json(), None
    except requests.RequestException as e:
        return None, f"取得に失敗しました（{e.__class__.__name__}）"


def fetch_yahoo(keyword: str, app_id: str):
    """(data, error) を返す。fetch_rakuten と同じ約束。"""
    try:
        r = requests.get(
            YAHOO_URL,
            params={
                "appid": app_id,
                "query": keyword,
                "results": 30,
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json(), None
    except requests.RequestException as e:
        return None, f"取得に失敗しました（{e.__class__.__name__}）"
