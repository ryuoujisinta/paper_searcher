# 仕様書: Review Paper Automator

## 1. プロジェクト概要

### 1.1 目的

特定の研究テーマにおいて、Seed Paper（重要論文）およびキーワードを起点に先行研究を芋づる式に探索し、レビュー論文（Survey Paper）の執筆に耐えうる100件以上の高品質な論文リストを自動生成する。さらに、各論文の「手法」「結果」「課題」などをLLMを用いて構造化データとして抽出する。

### 1.2 スコープ

*   **対象データソース:** Semantic Scholar (S2AG), ArXiv (Abstract補完用)
*   **対象ドキュメント:** 英語の学術論文（Title, Abstract）
*   **インターフェース:** Streamlit Web UI および CLI
*   **最終成果物:** 比較検討用のCSVマトリックス（一覧表）

---

## 2. システムアーキテクチャ

システムは以下の3つのパイプライン処理で構成される。

1.  **Phase 1: Collection (広範な収集)**
    *   キーワード検索と引用ネットワーク探索（Snowball Sampling）を組み合わせ、母集団を形成する。
    *   S2AGで抄録が取得できない場合、ArXiv APIを利用して補完を試みる。

2.  **Phase 2: Screening (選別)**
    *   LLMを用いてアブストラクトを読み込み、研究テーマへの関連性を判定してノイズを除去する。
    *   `screening_threshold` に基づき、高品質な論文のみを次フェーズに送る。

3.  **Phase 3: Extraction (情報抽出)**
    *   選別された論文からレビューに必要な項目（課題、手法、結果など）を抽出し、構造化する。
    *   並列処理により、多数の論文を効率的に処理する。

---

## 3. 詳細機能要件

### Phase 1: Collection (収集)

*   **入力:**
    *   検索キーワード（複数指定可能）
    *   Seed Papers（DOIリスト）
    *   検索期間（Year Range）
    *   `snowball_from_keywords_limit`: キーワード検索上位の結果をスノーボールサンプリングの起点に追加する数
*   **処理:**
    1.  **Keyword Search:** APIを用いて関連論文を取得。
    2.  **Snowballing:** Seed Papers およびキーワード上位論文の参考文献(References)と引用文献(Citations)を取得。
    3.  **Deduplication:** DOIまたはTitleをキーとして重複を排除。
    4.  **Basic Filter:** `min_citations` 未満、指定期間外を除外。
    5.  **Abstract Completion:** ArXiv APIを用いて欠損しているアブストラクトを補完。
*   **出力:** 候補論文リスト（CSV/Checkpoint）

### Phase 2: Screening (選別)

*   **入力:** Phase 1の候補論文リスト
*   **処理:**
    *   LLM (Gemini 2.0 Flash Lite) を用いて、キーワード群から構築されたResearch Scopeへの合致度を判定。
    *   各論文に `relevance_score` (0-10) と `relevance_reason` を付与。
*   **出力:** フィルタリング済み論文リスト

### Phase 3: Extraction (抽出)

*   **入力:** Phase 2で合格した論文リスト（`relevance_score` >= `screening_threshold`）
*   **処理:**
    *   LLM (Gemini 2.0 Flash Lite) を用いてJSON Modeで構造化情報を抽出。
*   **抽出項目 (Schema):** `problem`, `method`, `dataset`, `metric`, `limitation`, `category`, `one_line_summary` (日本語)
*   **出力:** 最終CSVファイル (`final_review_matrix.csv`)

---

## 4. データ構造定義

### 4.1 設定ファイル (`config.yml`)

```yaml
project_name: "my_project"
search_criteria:
  keywords: ["Large Language Models", "Survey"]
  seed_paper_dois: []
  snowball_from_keywords_limit: 5
  min_citations: 10
  year_range: [2020, 2025]
  screening_threshold: 7

llm_settings:
  model_screening: "gemini-2.0-flash-lite"
  model_extraction: "gemini-2.0-flash-lite"

logging:
  level: "INFO"
```

### 4.2 ディレクトリ構成

実行ごとにタイムスタンプ付きのディレクトリが `data/<project_name>/` 配下に作成される。

```text
├── data/
│   └── <project_name>/
│       └── <YYYYMMDD_HHMMSS>/
│           ├── config.yml          # 実行時の設定コピー
│           ├── raw/                # Phase 1 結果
│           ├── interim/            # Phase 2 結果
│           └── final/              # Phase 3 結果 (最終出力)
```

---

## 5. 技術スタック

*   **Language:** Python 3.13
*   **Package Manager:** `uv`
*   **UI Framework:** `streamlit`
*   **API Client:** `google-genai` (Gemini API), `arxiv`, `requests`
*   **Utilities:** `pandas`, `pydantic`, `tenacity`, `tqdm`, `python-dotenv`

---

## 6. 非機能要件

1.  **Checkpointing:** 各フェーズの結果を保存し、再実行時に中断箇所から再開可能。
2.  **Concurrency:** LLM呼び出しを `ThreadPoolExecutor` で並列化し、スループットを向上。
3.  **UI:** インタラクティブな設定変更、パイプライン実行ログのリアルタイム表示、結果のデータフレーム表示・ダウンロード機能。

---

## 7. ディレクトリ構成 (実装)

```text
├── app.py              # Streamlit Web UI
├── main.py             # CLI 実行エントリーポイント
├── config.yml          # デフォルト設定
├── src/
│   ├── core/           # パイプライン本体
│   │   ├── collector.py
│   │   ├── screener.py
│   │   └── extractor.py
│   ├── models/         # Pydantic モデル定義
│   │   └── models.py
│   └── utils/          # 共通ユーティリティ
│       ├── constants.py
│       ├── io_utils.py
│       └── logging_config.py
├── prompts/            # LLM用プロンプトテンプレート
└── data/               # 実行結果格納
```

---

## 8. 実行方法

### 8.1 Web UI での実行
```powershell
uv run streamlit run app.py
```

### 8.2 CLI での実行
```powershell
uv run main.py
```
