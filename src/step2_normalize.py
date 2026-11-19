# Step 2：整形（正規化）の試作スクリプト（お酒の価格比較サービス）
#
# 役割：Step 1 で保存した data/out_rakuten.json / data/out_yahoo.json を読み、
#       API ごとにバラバラな形式を共通レコードにそろえて、価格順に表示する。
#       そろえた結果は data/normalized.json に保存する（Step 3 で使う）。
#
# 使い方：
#   uv run python src/step2_normalize.py
#
# ★ extract_volume_count（商品名から容量・本数・単価を取り出す中核）は、
#   2026-11-19 に本人の依頼で Muse が実装した。考え方はガイド
#   step2-normalize-prototype.md の2章と、関数内のコメント参照。
#   それ以外の部分（JSON の読み込み・共通形式への変換・表示・保存）も完成コード。
#
# ※ 片方の JSON がまだ無い場合は、その API をスキップして続行する。
#   楽天は ID が取れてからでないと out_rakuten.json が作られないため。

import json
import re
import unicodedata
from pathlib import Path

# プロジェクト直下（このファイルの2つ上のフォルダ）を基準にする（Step 1 と同じ）。
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


def _price_to_int(value) -> int:
    """価格を int にそろえる。'11,495' のような文字列でも受け付ける。失敗したら 0。"""
    if value is None:
        return 0
    m = re.search(r"\d+", str(value).replace(",", ""))
    return int(m.group()) if m else 0


# --- Yahoo!ショッピングの JSON を共通レコードに変換する ---
def load_yahoo() -> list:
    path = DATA_DIR / "out_yahoo.json"
    if not path.exists():
        print("Yahoo!: out_yahoo.json がまだ無いのでスキップします")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for hit in data.get("hits", []):
        # ショップ名は seller という辞書の中の name に入っている
        seller = hit.get("seller")
        shop = seller.get("name", "") if isinstance(seller, dict) else ""
        records.append({
            "source": "yahoo",
            "name": hit.get("name", ""),
            "price": _price_to_int(hit.get("price")),
            "url": hit.get("url", ""),
            "shop": shop,
            "jan_code": hit.get("janCode") or None,
        })
    print(f"Yahoo!: {len(records)} 件を読み込みました")
    return records


# --- 楽天市場の JSON を共通レコードに変換する ---
def load_rakuten() -> list:
    path = DATA_DIR / "out_rakuten.json"
    if not path.exists():
        print("楽天: out_rakuten.json がまだ無いのでスキップします")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for wrapper in data.get("Items", []):
        # 商品本体は Items の各要素の中の Item に入っている
        item = wrapper.get("Item", wrapper)
        records.append({
            "source": "rakuten",
            "name": item.get("itemName", ""),
            "price": _price_to_int(item.get("itemPrice")),
            "url": item.get("itemUrl", ""),
            "shop": item.get("shopName", ""),
            # 楽天の商品検索 API の返り値には JAN コードが含まれないので None
            "jan_code": None,
        })
    print(f"楽天: {len(records)} 件を読み込みました")
    return records


def _to_ml(number: str, unit: str) -> float:
    """容量の数字と単位を ml に統一する。L（リットル）は 1000 倍、cc は ml と同じ。"""
    value = float(number)
    if unit.lower() in ("l", "リットル"):
        return value * 1000
    return value


# --- 正規化の中核：商品名から容量・本数を抜き出して単価を出す ---
def extract_volume_count(name: str, price: int):
    # ============================================================
    # 商品名から「1本あたりの容量（ml）」と「本数」を取り出し、
    # 「100ml あたりの単価」まで計算して返す。
    # 戻り値は (volume_ml, count, price_per_100ml) の3つ組。
    # 容量が取り出せなければ volume_ml と price_per_100ml は None、
    # 本数が読み取れなければ count は 1 とする。
    #
    # やり方の要点：
    #   1. NFKC で全角の数字・英字を半角に寄せてから正規表現で探す。
    #   2. 本数は「6缶パック×4」のような掛け算表記を最初に処理し、
    #      次に「×24本」、最後に「24本」「2本セット」の順で探す。
    #   3. 容量は単位（ml / L / リットル / cc）付きの数字だけを拾う。
    #      「山崎12年」の 12 や「43%」の 43 は単位が付かないので混ざらない。
    #   4. 「計8.4L」「合計8400ml」は総容量として扱い、
    #      1本あたりは総容量 ÷ 本数で出す。
    #   5. 単価は price ÷ 総容量(ml) × 100 で「100ml あたり」になる。
    # ============================================================
    s = unicodedata.normalize("NFKC", name).replace(",", "")

    # --- 本数 ---
    count = 1
    pack = re.search(r"(\d+)\s*(?:本|缶|個|袋|枚)\s*(?:入り|入|パック)?\s*[×x]\s*(\d+)", s)
    if pack:
        # 「6缶パック×4」= 6 × 4 = 24 本
        count = int(pack.group(1)) * int(pack.group(2))
    else:
        m = re.search(r"[×x]\s*(\d+)\s*(?:本|缶|個|袋|枚|パック|セット)?", s)
        if m:
            # 「350ml×24本」「×24」など
            count = int(m.group(1))
        else:
            m = re.search(r"(\d+)\s*(?:本|缶|個|袋|枚)(?:入り|入|セット)?", s)
            if m:
                # 「24本」「12缶入り」「2本セット」など
                count = int(m.group(1))
            else:
                m = re.search(r"(\d+)\s*(?:パック|セット|ケース)", s)
                if m:
                    count = int(m.group(1))

    # --- 容量 ---
    # まず「計・合計」の総容量表記を探す（1本の容量と取り違えないため）
    total_ml = None
    m = re.search(r"(?:計|合計)\s*(\d+(?:\.\d+)?)\s*(ml|リットル|l|cc)", s, re.IGNORECASE)
    if m:
        total_ml = _to_ml(m.group(1), m.group(2))

    # 1本あたりの容量（単位付きの数字のうち最初のもの）
    unit_ml = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|リットル|l|cc)", s, re.IGNORECASE)
    if m:
        unit_ml = _to_ml(m.group(1), m.group(2))

    if total_ml is not None:
        volume_ml = total_ml / count
        total = total_ml
    elif unit_ml is not None:
        volume_ml = unit_ml
        total = unit_ml * count
    else:
        return None, count, None

    # 割り切れる場合は int に寄せる（8400 / 24 = 350.0 → 350）
    if float(volume_ml).is_integer():
        volume_ml = int(volume_ml)

    price_per_100ml = price / total * 100 if total else None
    return volume_ml, count, price_per_100ml


def main():
    records = load_rakuten() + load_yahoo()
    if not records:
        print("表示できるデータがありません。")
        print("Step 1 を実行して、data/ に out_rakuten.json / out_yahoo.json を用意してください。")
        return

    # 共通レコードに、容量・本数・単価の3フィールドを足す
    for rec in records:
        volume_ml, count, price_per_100ml = extract_volume_count(rec["name"], rec["price"])
        rec["volume_ml"] = volume_ml
        rec["count"] = count
        rec["price_per_100ml"] = price_per_100ml

    # 価格が安い順に並べて表示する
    records.sort(key=lambda r: r["price"])
    print()
    print(f"=== 価格順の一覧（全 {len(records)} 件）===")
    for i, rec in enumerate(records, 1):
        source_label = "Yahoo!" if rec["source"] == "yahoo" else "楽天"
        if rec["price_per_100ml"] is not None:
            unit = f"100mlあたり {rec['price_per_100ml']:,.0f} 円"
        else:
            unit = "単価: 容量不明のため計算なし"
        print(f"{i:>3}. [{source_label}] {rec['price']:,} 円（{unit}）")
        print(f"     {rec['name']} / {rec['shop']}")

    # Step 3 で使うために、そろえた結果を保存する
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / "normalized.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print()
    print("data/normalized.json に保存しました")


if __name__ == "__main__":
    main()
