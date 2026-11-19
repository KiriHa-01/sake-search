# Step 3 用の正規化モジュール（アプリから使う版）
#
# 役割：fetch.py が返した API の生 JSON（dict）を受け取り、共通レコードに
#       そろえて、同じ商品（JAN・容量・本数が同じもの）をグループに束ねる。
# 容量・本数・単価の抽出は、Step 2（src/step2_normalize.py）で自分で書いた
# extract_volume_count をそのまま使っている（TODOコメントだけ整理した）。

import re
import unicodedata


def _price_to_int(value) -> int:
    """価格を int にそろえる。'11,495' のような文字列でも受け付ける。失敗したら 0。"""
    if value is None:
        return 0
    m = re.search(r"\d+", str(value).replace(",", ""))
    return int(m.group()) if m else 0


# --- 正規化の中核：商品名から容量・本数を抜き出して単価を出す（Step 2 の実装） ---
def extract_volume_count(name: str, price: int):
    name = unicodedata.normalize("NFKC", name)  # 全角数字・英字を半角に寄せる
    total_pat = re.compile(r"(?:計|合計|総容量|トータル)(\d+(?:\.\d+)?)\s*(ml|リットル|リッター|l|cc)", re.IGNORECASE)
    volue_pat = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|リットル|リッター|l|cc)", re.IGNORECASE)

    def convert_volume_to_ml(volume_str, unit):
        volume = float(volume_str)
        unit = unit.lower()
        if unit in ["l", "リットル", "リッター"]:
            return int(volume * 1000)
        elif unit in ["ml", "cc"]:
            return int(volume)
        else:
            return None

    count_pat = re.compile(r"(\d+(?:\.\d+)?)\s*(?:本|缶|個|パック)", re.IGNORECASE)
    count_mult_pat = re.compile(r"(\d+(?:\.\d+)?)\s*(?:本|缶|個|パック)(?:パック)?\s*[×x]\s*(\d+(?:\.\d+)?)", re.IGNORECASE)

    m = count_mult_pat.search(name)
    if m:
        count = int(m.group(1)) * int(m.group(2))            # group(1) × group(2)
    elif count_pat.search(name):
        m = count_pat.search(name)
        count = int(m.group(1))                              # group(1) を int に
    else:
        count = 1

    # 容量を確定する
    m = total_pat.search(name)
    if m:
        volume_ml = convert_volume_to_ml(m.group(1), m.group(2)) / count     # 変換した総容量 ÷ count
    elif volue_pat.search(name):
        m = volue_pat.search(name)
        volume_ml = convert_volume_to_ml(m.group(1), m.group(2)) # 変換した値そのまま
    else:
        return None, count, None
    price_per_100ml = price / (volume_ml * count) * 100 if volume_ml and count else None
    return volume_ml, count, price_per_100ml


def build_item(source: str, name: str, price, shop: str, url: str, jan_code) -> dict:
    """1件分の共通レコードを作る。容量・本数・単価もここで付ける。"""
    price = _price_to_int(price)
    volume_ml, count, price_per_100ml = extract_volume_count(name, price)
    return {
        "source": source,
        "name": name,
        "price": price,
        "shop": shop,
        "url": url,
        "jan_code": jan_code,
        "volume_ml": volume_ml,
        "count": count,
        "price_per_100ml": price_per_100ml,
        "price_per_bottle": (price / count) if count else None,
    }


# --- Yahoo!ショッピングの JSON（dict）を共通レコードのリストに変換する ---
def items_from_yahoo_data(data: dict) -> list:
    items = []
    for hit in data.get("hits", []):
        seller = hit.get("seller")
        shop = seller.get("name", "") if isinstance(seller, dict) else ""
        items.append(build_item(
            "yahoo",
            hit.get("name", ""),
            hit.get("price"),
            shop,
            hit.get("url", ""),
            hit.get("janCode") or None,
        ))
    return items


# --- 楽天市場の JSON（dict）を共通レコードのリストに変換する ---
def items_from_rakuten_data(data: dict) -> list:
    items = []
    for wrapper in data.get("Items", []):
        item = wrapper.get("Item", wrapper)
        items.append(build_item(
            "rakuten",
            item.get("itemName", ""),
            item.get("itemPrice"),
            item.get("shopName", ""),
            item.get("itemUrl", ""),
            None,  # 楽天の商品検索 API の返り値には JAN コードが含まれない
        ))
    return items


def _group_key(item: dict):
    """同じ商品とみなす条件。JAN があれば JAN、なければ商品名をキーにして、
    容量と本数が同じものを同じグループにする。"""
    base = item["jan_code"] if item["jan_code"] else unicodedata.normalize("NFKC", item["name"]).strip()
    return (base, item["volume_ml"], item["count"])


def normalize_and_group(items: list) -> list:
    """共通レコードのリストをグループに束ねる。
    戻り値は {"group_key", "cheapest", "items", "is_valid_comparison"} のリスト。
    is_valid_comparison は「容量が分かり、1本売り」のグループに付くフラグで、
    画面ではこれが True のグループをメイン、False を別枠で表示する。"""
    groups = {}
    for it in items:
        groups.setdefault(_group_key(it), []).append(it)

    result = []
    for key, gitems in groups.items():
        gitems.sort(key=lambda x: x["price"])
        cheapest = gitems[0]
        valid = cheapest["volume_ml"] is not None and cheapest["count"] == 1
        result.append({
            "group_key": key,
            "cheapest": cheapest,
            "items": gitems,
            "is_valid_comparison": valid,
        })

    # グループどうしは、最安の100mlあたり単価が安い順（単価不明は後ろ）
    result.sort(key=lambda g: (g["cheapest"]["price_per_100ml"] is None,
                               g["cheapest"]["price_per_100ml"] or 0))
    return result
