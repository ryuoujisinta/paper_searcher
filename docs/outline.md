# 仕様書: Review Paper Automator

## 1. プロジェクト概要

### 1.1 目的

特定の研究テーマにおいて、Seed Paper（重要論文）およびキーワードを起点に先行研究を芋づる式に探索し、レビュー論文（Survey Paper）の執筆に耐えうる100件以上の高品質な論文リストを自動生成する。さらに、各論文の「手法」「結果」「課題」などをLLMを用いて構造化データとして抽出する。

### 1.2 スコープ

* **対象データソース:** Semantic Scholar (S2AG)
* **対象ドキュメント:** 英語の学術論文（Title, Abstract）
* **最終成果物:** 比較検討用のCSVマトリックス（一覧表）

---

## 2. システムアーキテクチャ

システムは以下の3つのパイプライン処理で構成される。

1. **Phase 1: Collection (広範な収集)**
* キーワード検索と引用ネットワーク探索（Snowball Sampling）を組み合わせ、母集団（300-500件）を形成する。


2. **Phase 2: Screening (選別)**
* LLMを用いてアブストラクトを読み込み、研究テーマへの関連性を判定してノイズを除去する。


3. **Phase 3: Extraction (情報抽出)**
* 選別された論文からレビューに必要な項目（課題、手法、結果など）を抽出し、構造化する。



---

## 3. 詳細機能要件

### Phase 1: Collection (収集)

* **入力:**
* 検索キーワード（例: "LLM Hallucination Detection"）
* Seed Papers（DOIリスト 3〜5件）
* 検索期間（例: 2020-2025）


* **処理:**
1. **Keyword Search:** APIを用いて直近の関連論文を取得（Top 50-100）。
2. **Citation Mining:** Seed Papersの「参考文献(References)」と「被引用文献(Citations)」を2階層まで取得。
3. **Deduplication:** DOIまたはTitleをキーとして重複を排除する。
4. **Basic Filter:**
* `Citation Count`: しきい値（例: 10以上）未満を除外。
* `Publication Type`: Review, Journal Article, Conference を優先（Preprintを含めるかはConfigで指定）。




* **出力:** 候補論文リスト（CSV/Pickle）

### Phase 2: Screening (選別)

* **入力:** Phase 1の候補論文リスト（Title, Abstract必須）
* **処理:**
* LLM (Gemini 2.5 Flash Lite) に対して以下の判定を行わせる。
* **判定基準:** ユーザーが指定した「Research Scope」に合致するか。


* **出力:**
* フィルタリング済みの論文リスト
* 中間カラム追加: `relevance_score` (0-10), `relevance_reason`



### Phase 3: Extraction (抽出)

* **入力:** Phase 2で合格した論文リスト
* **処理:**
* LLM (Gemini 2.5 Flash Lite) を用いてJSON Modeで以下の情報を抽出する。


* **抽出項目 (Schema):**
1. `problem`: 取り組んでいる具体的な課題
2. `method`: 提案手法・アルゴリズム名
3. `dataset`: 使用データセット
4. `metric`: 評価指標と結果（数値）
5. `limitation`: 限界点・未解決課題
6. `category`: 論文のカテゴリ分類（Method / Survey / Theory / Application）
7. `one_line_summary`: 1行要約（日本語/英語）


* **出力:** 最終CSVファイル (`review_matrix.csv`)

---

## 4. データ構造定義

### 4.1 設定ファイル (`config.yml`)

```yaml
project_name: "My_Review_2025"
api_settings:
  semantic_scholar_api_key: "YOUR_KEY_HERE" # Optional but recommended
  google_api_key: "YOUR_KEY_HERE"

search_criteria:
  keywords: ["Large Language Models", "Chain of Thought"]
  seed_paper_dois:
    - "10.48550/arXiv.2201.11903"
    - "10.1145/3397271.3401075"
  min_citations: 15
  year_range: [2021, 2025]

llm_settings:
  model_screening: "gemini-2.5-flash-lite"
  model_extraction: "gemini-2.5-flash-lite"

```

### 4.2 出力ファイル仕様 (`final_review.csv`)

| Column Name | Description |
| --- | --- |
| **Title** | 論文タイトル |
| **Year** | 出版年 |
| **Citations** | 被引用数 |
| **Relevance** | 関連度スコア (1-10) |
| **Category** | 自動分類カテゴリ |
| **Problem** | 研究課題 |
| **Method** | 提案手法 |
| **Result** | 主な結果 |
| **Limitations** | 課題・限界 |
| **URL** | PDF/S2リンク |

---

## 5. 技術スタック & 推奨ライブラリ

* **Language:** Python 3.13
* **Package Manager:** `uv`
* **API Client:**
* `requests`: HTTPリクエスト
* `tenacity`: APIレート制限対策（リトライ処理）


* **Data Processing:**
* `pandas`: データフレーム操作、CSV出力


* **LLM Integration:**
* `google-generativeai`: Google Generative AI Python SDK
* `pydantic`: 出力JSONの型定義・検証



---

## 6. 非機能要件・制約事項

1. **API Rate Limits:**
* Semantic Scholar API (Public) はレート制限（例: 100 requests/5min）があるため、リクエスト間に `time.sleep()` を挟むか、適切なWait処理を実装する。


2. **Cost Control:**
* 全フェーズで極めて安価かつ高性能な `gemini-2.5-flash-lite` を使用し、コストを最小化する。
* 概算コスト: 論文100件のフルプロセス（母集団500件）で $0.10 (約15円) 程度を想定。


3. **Data Persistence & Organization:**
* 出力ディレクトリは `data/YYYYMMDD_ProjectName/` 形式とし、実行時のタイムスタンプとプロジェクト名を含める。
* 各フェーズ終了ごとに中間ファイルを保存し、エラー発生時に途中から再開できるようにする（Checkpointing）。
* 実行時に使用された `config.yml` を、実行ログや再現性の確保のため出力ディレクトリ内にコピーして保存する。



---

## 7. ディレクトリ構成案

```text
├── data/
│   └── <YYYYMMDD_ProjectName>/ # 実行ごとに生成されるフォルダ
│       ├── config.yml         # 実行時にコピーされた設定ファイル
│       ├── raw/                # APIから取得した生データ
│       ├── interim/            # スクリーニング後の中間データ
│       └── final/              # 最終的なCSV出力
├── src/
│   ├── collector.py    # API連携・論文収集ロジック
│   ├── screener.py     # LLMによるフィルタリング
│   ├── extractor.py    # LLMによる情報抽出
│   └── utils.py        # ファイルIO、共通関数
├── config.yml         # 設定ファイル
├── main.py             # 実行エントリーポイント
├── pyproject.toml      # 依存ライブラリ管理 (uv)
└── README.md

```

---

## 8. 環境構築 (Environment Setup)

本プロジェクトではパッケージ管理に `uv` を使用します。

### 8.1 uvのインストール
`uv` がインストールされていない場合は、以下のコマンドでインストールしてください。
```powershell
powershell -ExecutionPolicy ByPass -c "ir https://astral.sh/uv/install.ps1"
```

### 8.2 プロジェクトのセットアップ
リポジトリをクローンした後、プロジェクトディレクトリで以下のコマンドを実行して仮想環境の作成と依存関係のインストールを行います。

```powershell
# 仮想環境の作成と同期
uv sync
```

### 8.3 実行方法
仮想環境内でスクリプトを実行するには、`uv run` を使用します。
```powershell
uv run main.py
```
