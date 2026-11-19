"""Step 3：お酒の価格比較アプリ（Streamlit）

検索キーワード → 楽天 / Yahoo! の API → normalize.py の整形・グルーピング → 画面表示。
"""
import os

import streamlit as st
from dotenv import load_dotenv

from fetch import fetch_rakuten, fetch_yahoo
from normalize import normalize_and_group, items_from_rakuten_data, items_from_yahoo_data

load_dotenv()

st.set_page_config(page_title="お酒の価格比較", page_icon="🍶")


def get_secret(name: str) -> str:
    """公開環境では Streamlit の Secrets、ローカルでは .env から読む。"""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.environ.get(name, "")


@st.cache_data(ttl=3600, show_spinner=False)
def search_all(keyword: str, _rakuten_id: str, _yahoo_id: str) -> dict:
    """両 API を叩いて、整形・グルーピングまで済ませた結果を返す（1時間キャッシュ）。
    楽天の ID が未設定（または dummy）の間は、Yahoo! だけを検索する。"""
    items, errors, notes = [], [], []
    if _rakuten_id and _rakuten_id != "dummy":
        data, err = fetch_rakuten(keyword, _rakuten_id)
        if data is not None:
            items.extend(items_from_rakuten_data(data))
        else:
            errors.append(f"楽天市場：{err}")
    else:
        notes.append("楽天市場は ID 未設定のため検索していません")
    if _yahoo_id:
        data, err = fetch_yahoo(keyword, _yahoo_id)
        if data is not None:
            items.extend(items_from_yahoo_data(data))
        else:
            errors.append(f"Yahoo!ショッピング：{err}")
    return {"groups": normalize_and_group(items), "errors": errors,
            "notes": notes, "total": len(items)}


def yen(v) -> str:
    if v is None:
        return "-"
    return f"{v:,.0f}円"


SOURCE_LABEL = {"rakuten": "楽天", "yahoo": "Yahoo!"}


def show_group(g: dict):
    """1グループ分（同じ容量・本数の商品たち）を表示する。"""
    c = g["cheapest"]
    vol = f"{c['volume_ml']}ml" if c["volume_ml"] else "容量不明"
    st.subheader(f"{c['name']}（{vol} × {c['count']}本）")
    # 最安を強調表示
    unit = f"100mlあたり {yen(c['price_per_100ml'])}"
    st.success(
        f"最安 **{yen(c['price'])}**（{unit}）"
        f" — {c['shop']}［{SOURCE_LABEL[c['source']]}］ ※送料別"
    )
    if c["url"]:
        st.link_button("最安の商品ページを開く", c["url"])
    rows = []
    for it in g["items"]:
        rows.append({
            "価格（円）": it["price"],
            "100mlあたり（円）": None if it["price_per_100ml"] is None else round(it["price_per_100ml"]),
            "1本あたり（円）": None if it["price_per_bottle"] is None else round(it["price_per_bottle"]),
            "ショップ": it["shop"],
            "どこ": SOURCE_LABEL[it["source"]],
            "URL": it["url"],
        })
    st.dataframe(
        rows,
        column_config={"URL": st.column_config.LinkColumn("商品ページ")},
        hide_index=True,
        use_container_width=True,
    )


st.title("🍶 お酒の価格比較")
st.caption(
    "楽天市場と Yahoo!ショッピングの価格を比べます。"
    "表示価格は税込・**送料別**です（送料はショップごとに異なります）。"
    "最安は「送料を含まない最安」です。"
)

rakuten_id = get_secret("RAKUTEN_APP_ID")
yahoo_id = get_secret("YAHOO_APP_ID")
if not yahoo_id and not rakuten_id:
    st.error("API の ID が設定されていません。ローカルでは .env、公開環境では Secrets を確認してください。")
    st.stop()

with st.form("search_form"):
    keyword = st.text_input("銘柄名で検索", placeholder="例：山崎 / プレミアムモルツ 350ml")
    submitted = st.form_submit_button("検索")

if submitted and keyword.strip():
    with st.spinner("価格を調べています…"):
        st.session_state["result"] = search_all(keyword.strip(), rakuten_id, yahoo_id)

result = st.session_state.get("result")
if result is not None:
    for n in result["notes"]:
        st.info(n)
    for e in result["errors"]:
        st.warning(f"一部の取得に失敗しました（{e}）。取得できた分だけ表示しています。")
    if result["total"] == 0 and not result["errors"]:
        st.info("該当する商品が見つかりませんでした。銘柄名を変えて試してください。")
    groups = result["groups"]
    normal = [g for g in groups if g["is_valid_comparison"]]
    others = [g for g in groups if not g["is_valid_comparison"]]
    for g in normal:
        show_group(g)
    if others:
        st.divider()
        st.subheader("その他（セット商品・容量不明など。中身や条件がそろわないため別枠）")
        for g in others:
            show_group(g)
