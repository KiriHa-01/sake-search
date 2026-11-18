# Step 2：整形（正規化）の試作スクリプト（お酒の価格比較サービス）
#
# 役割：Step 1 で保存した data/out_rakuten.json / data/out_yahoo.json を読み、
#       API ごとにバラバラな形式を共通レコードにそろえて、価格順に表示する。
#       そろえた結果は data/normalized.json に保存する（Step 3 で使う）。
#
# 使い方：
#   uv run python src/step2_normalize.py
#
# ★ 自分で書く部分は、商品名から容量（ml）と本数を取り出して単価を計算する
#   extract_volume_count 関数の1か所だけ。「TODO（自分で書く）」のマーカーが
#   付いている。考え方はガイド step2-normalize-prototype.md の2章参照。
#   それ以外の部分（JSON の読み込み・共通形式への変換・表示・保存）は完成コード。
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


# --- 正規化の中核：商品名から容量・本数を抜き出して単価を出す ---
def extract_volume_count(name: str, price: int):
    # ============================================================
    # TODO（自分で書く）: 商品名から「1本あたりの容量（ml）」と「本数」を
    #   取り出し、「100ml あたりの単価」まで計算して返す。
    #   戻り値は (volume_ml, count, price_per_100ml) の3つ組。
    #   容量が取り出せなければ volume_ml と price_per_100ml は None、
    #   本数が読み取れなければ count は 1 とする。
    #
    #   手がかり（ガイド step2-normalize-prototype.md の2章に詳しくある）：
    #   - まず unicodedata.normalize("NFKC", name) で全角の数字・英字を
    #     半角に寄せると、正規表現が書きやすくなる。
    #   - 容量は「数字 + 単位」の形を探す。例：700ml / 1.8L / 500cc。
    #     L（リットル）は 1000 倍して ml に統一する。cc は ml と同じ。
    #     正規表現なら r"(\d+(?:\.\d+)?)\s*(ml|リットル|l|cc)" のような形。
    #   - 本数は「×24本」「350ml×24缶」「6缶パック×4」「2本セット」の
    #     ような表記から読む。「6缶パック×4」は掛け算で 24 本になる。
    #   - 罠：「計8.4L」「合計8400ml」は1本の容量ではなく総容量。
    #     「山崎12年」の 12 は熟成年数、「43%」は度数で、どちらも容量ではない。
    #     単位（ml / L）が付いた数字だけを拾えば、基本的には混ざらない。
    #   - 単価は price / (volume_ml × count) × 100 で「100ml あたり」になる。
    #
    #   いまは仮の値を返している（このままでも全体は動くが、単価は出ない）。
    # ============================================================
    return None, 1, None


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
