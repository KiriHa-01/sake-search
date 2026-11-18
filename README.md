# お酒の価格比較サービス（sake-search）

銘柄名で検索すると、楽天市場と Yahoo!ショッピングの公式 API から価格を取得し、ショップ別の価格一覧と、容量・本数を揃えた最安値を表示するサービス。v1 は Python + Streamlit で作り、Streamlit Community Cloud（無料）に公開する予定。対象のお酒は全般だが、開始時はウイスキーとビールに絞る。

スクレイピングは行わず、公式 API のみを使う。v1 では送料込み比較・ポイント考慮・アフィリエイトは入れない（v2 以降）。

## 進捗と全体像

| Step | 内容 | 状態 |
|---|---|---|
| Step 1 | 両 API を叩いて返却形式を確認する実験 | ← このフォルダはここまで用意済み |
| Step 2 | 整形と名寄せの試作（共通形式＋容量・本数の抽出＋グルーピング） | Step 1 の保存 JSON を使う |
| Step 3 | Streamlit アプリ化と公開 | |

データの流れ（完成形）：検索 → 両 API を叩く → 整形（共通形式） → グルーピング → 最安表示。

## セットアップ（WSL の Ubuntu で）

前提：uv がインストール済みであること。

```bash
# このフォルダの中身を ~/dev/sake-search に置く（フォルダ名は sake-search にする）
cd ~/dev/sake-search
uv sync
```

### 1. 楽天のアプリ ID を取る（無料・5分ほど）

1. https://webservice.rakuten.co.jp/ を開く
2. 楽天会員の ID でログインする
3. 「アプリ ID 発行」（新規アプリ登録）に進む
4. 入力項目：
   - アプリ名：`sake-price-check` など、自分が分かれば何でもよい
   - アプリ URL：必須なら自分の GitHub プロフィール（https://github.com/KiriHa-01）の URL でよい（後から変更できる）
5. 発行された「アプリケーション ID」を控える

※ アフィリエイト ID は今は不要（収益化のときに別途考える）。

### 2. Yahoo! のアプリケーション ID を取る（無料・5分ほど）

1. https://developer.yahoo.co.jp/ を開く
2. Yahoo! JAPAN ID でログインする
3. 「アプリケーションを登録する」に進む
4. 入力項目：
   - アプリケーションの種類：「サーバーサイド」を選ぶ
   - アプリケーション名：`sake-price-check` など
   - サイト URL：楽天と同様、GitHub プロフィールの URL でよい
5. 発行された「Client ID（アプリケーション ID）」を控える

### 3. .env を作る

プロジェクト直下に `.env` というファイルを作り、取得した ID を書く（雛形は `.env.example`）。

```
RAKUTEN_APP_ID=（楽天のアプリケーションID）
YAHOO_APP_ID=（Yahoo! の Client ID）
```

- ID はこの `.env` の中だけに置く。コードに直書きしない。
- `.env` は `.gitignore` で除外済みなので GitHub には上がらない。
- アプリ ID はパスワードではないけれど公開しない。スクリーンショットを送るときは ID が写っていないか確認する。

## Step 1 実験の実行方法

まず `src/step1_api_experiment.py` の **params の穴埋め（下記「自分で書く部分」）を済ませてから**実行する。

```bash
uv run python src/step1_api_experiment.py 山崎
uv run python src/step1_api_experiment.py "プレミアムモルツ 350ml"
```

出力と保存先：

- ターミナルに両 API の status・件数・先頭の商品名と価格が出る
- レスポンスの JSON が `data/out_rakuten.json` と `data/out_yahoo.json` に保存される（この2ファイルが Step 2 の入力になる。Step 2 のガイドがプロジェクト直下のファイルを前提にしている場合は、この2つを直下にコピーすればよい）
- `.env` が無い・ID が空の場合は、API を叩かずに「アプリ ID が設定されていません」という案内が出て終了する

実行結果（両方の status、件数、先頭の商品名と価格）は Muse に伝える。エラーが出たらエラー本文もそのまま見せる。

## 自分で書く部分（Step 1 の課題）

`src/step1_api_experiment.py` の中で、`TODO（自分で書く）` のマーカーが付いた **params（検索条件の辞書）の2か所だけ**を書く。楽天と Yahoo! で1か所ずつ。目安15分。

- 楽天：`format` / `applicationId` / `keyword` / `hits` / `sort` の5つ
- Yahoo!：`appid` / `query` / `results` の3つ（楽天とキーの名前が違う点に注意）

ここが「API 呼び出しの核」で、「どのキーワードで・何件・どういう並びで取るか」を API に伝える場所。それ以外（.env 読み込み・保存・表示）は完成コードのまま使う。

詳しい書き方と完成版（詰まったら見る用）は、ガイド `step1-api-experiment.md` の4章・6章にある。ただし完成版は先に眺めるのではなく、自分で書いてから照合する順序で。

## フォルダ構成

```
liquor-price-compare/
├── README.md
├── pyproject.toml        # uv 用。依存は requests と python-dotenv のみ
├── .env.example          # ID の雛形（.env にコピーして使う）
├── .gitignore            # .env と data/ の生 JSON を除外
├── src/
│   └── step1_api_experiment.py   # Step 1 実験スクリプト（params だけ穴埋め）
└── data/
    └── .gitkeep          # 実験結果の JSON はここに保存される（Git 管理外）
```
