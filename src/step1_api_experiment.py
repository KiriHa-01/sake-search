# Step 1：API の実験スクリプト（お酒の価格比較サービス）
#
# 役割：楽天市場と Yahoo!ショッピングの API を実際に叩いて、
#       返ってくるデータの形（キー名・構造）を確認する。
#       レスポンスの JSON は data/ 配下に保存し、Step 2（整形と名寄せ）で使う。
#
# 使い方：
#   uv run python src/step1_api_experiment.py 山崎
#   uv run python src/step1_api_experiment.py "プレミアムモルツ 350ml"


import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# プロジェクト直下（このファイルの2つ上のフォルダ）を基準にする。
# どこから実行しても .env と data/ を同じ場所に読み書きするため。
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")

# --- アプリ ID のチェック ---
# ID が無いまま API を叩くと分かりにくいエラーになるので、先に案内して終わる。
# ※ ID の値そのものは画面に出さない。
_missing = [name for name in ("RAKUTEN_APP_ID", "YAHOO_APP_ID") if not os.environ.get(name)]
if _missing:
    print("アプリ ID が設定されていません:", ", ".join(_missing))
    print("プロジェクト直下に .env ファイルを作り、取得した ID を書いてください。")
    print("（.env.example が雛形です。ID の取得手順は README.md を参照）")
    sys.exit(1)

keyword = sys.argv[1] if len(sys.argv) > 1 else "山崎"
DATA_DIR.mkdir(exist_ok=True)

# --- 楽天市場 商品検索 API ---
r = requests.get(
    "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601",
    params={
        "format": "json",                             #（返り値を JSON 形式で、という指定）
        "applicationId": os.environ["RAKUTEN_APP_ID"],#（.env から読んだ ID）
        "keyword": keyword,                           #（検索キーワード）
        "hits": 5,                                    #（取る件数）
        "sort": "standard"                            #（並び順は標準）
    },
    timeout=30,
)
print("楽天 status:", r.status_code)
if r.ok:
    data = r.json()
    with open(DATA_DIR / "out_rakuten.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    items = data.get("Items", [])
    print("楽天 件数:", len(items))
    if items:
        item = items[0]["Item"]
        print("楽天 先頭のキー:", sorted(item.keys()))
        print("楽天 先頭:", item.get("itemName"), "/", item.get("itemPrice"), "円")
else:
    print("楽天 エラー本文:", r.text[:300])

# --- Yahoo! ショッピング 商品検索 API ---
r = requests.get(
    "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch",
    params={
        "appid": os.environ["YAHOO_APP_ID"],#（ID のキー名は appid）
        "query": keyword,                   #（キーワードのキー名は query）
        "results": 5,                       #（取る件数）
    },
    timeout=30,
)
print("Yahoo status:", r.status_code)
if r.ok:
    data = r.json()
    with open(DATA_DIR / "out_yahoo.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    hits = data.get("hits", [])
    print("Yahoo 件数:", len(hits))
    if hits:
        print("Yahoo 先頭のキー:", sorted(hits[0].keys()))
        print("Yahoo 先頭:", hits[0].get("name"), "/", hits[0].get("price"), "円")
else:
    print("Yahoo エラー本文:", r.text[:300])
