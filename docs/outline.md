# 仕様書: Review Paper Automator

## 1. プロジェクト概要

### 1.1 目的

特定の研究テーマにおいて、Seed Paper（重要論文）およびキーワードを起点に先行研究を芋づる式に探索し、レビュー論文（Survey Paper）の執筆に耐えうる100件以上の高品質な論文リストを自動生成する。さらに、各論文について「手法」「結果」などの要約を生成する。

### 1.2 スコープ

*   **対象データソース:** Semantic Scholar (S2AG), ArXiv (Abstract補完用)
*   **対象ドキュメント:** 英語の学術論文（Title, Abstract）
*   **インターフェース:** Streamlit Web UI および CLI
*   **最終成果物:** 比較検討用のCSVマトリックス（一覧表）

---

## 2. システムアーキテクチャ

システムは以下の3つのパイプライン処理で構成される。

## 2. システムアーキテクチャ

システムは、**反復的な検索と選別のループ**によって高品質な論文を収集する。

1.  **Iterative Loop (反復プロセス)**
    *   **Iteration 1:** キーワード検索および明示的なSeed Paperから初期候補を収集。
    *   **Screening & Scoring:** LLMを用いて自然言語クエリに対する関連度を判定し、同時に要約を生成。
    *   **Snowballing (Iteration 2+):** 高スコアの論文を新たなSeedとして、引用ネットワークを探索して候補を拡張。
    *   これを指定回数 (`iterations`) 繰り返す。

2.  **Output Generation**
    *   最終的に収集・選別された論文をスコア順にソートし、CSVとして出力する。

---

## 3. 詳細機能要件

### 3.1 Iterative Collection & Screening

*   **入力:**
    *   検索キーワード (`keywords`)
    *   自然言語クエリ (`natural_language_query`) - *スコアリング重視*
    *   Seed Papers (`seed_paper_dois`)
    *   反復回数 (`iterations`)
    *   スノーボール対象数 (`top_n_for_snowball`)
    *   その他: `keyword_search_limit`, `max_related_papers`, `screening_threshold`
*   **処理フロー:**
    1.  **Initial Collection (Iter 1):** キーワードとSeed DOIから候補を一括取得。
    2.  **Processing:** 重複排除、フィルタリング (`min_citations`, `year_range`)、Abstract補完 (ArXiv)。
    3.  **Screening:** LLMにより `relevance_score`, `relevance_reason`, `summary` (日本語) を生成。
    4.  **Save:** 中間結果 (`interim`) と Rawデータ (`raw`) を保存。
    5.  **Snowballing (Iter 2+):** 直前のループで高評価だった上位 N 件の引用・被引用を取得し、次回の候補とする。
*   **出力:**
    *   `raw/collected_papers_iter_X.csv`: 各回の収集生データ
    *   `interim/screened_papers_cumulative.csv`: 累積のスクリーニング結果

### 3.2 Final Output

*   **入力:** 累積スクリーニング結果
*   **処理:**
    *   論文を `relevance_score` の降順でソート。
    *   重複の最終確認（DOIベース）。
*   **出力:** `final/final_review_matrix.csv`
    *   主要カラム: Title, Year, Citations, Abstract, Score, Reason, Summary, DOI, URL

---

## 4. データ構造定義

### 4.1 設定ファイル (`config.yml`)

```yaml
project_name: "my_project"
search_criteria:
  keywords: ["Large Language Models", "Survey"]
  seed_paper_dois: []
  keyword_search_limit: 100
  max_related_papers: -1
  snowball_from_keywords_limit: 10
  min_citations: 5
  year_range: [2020, 2025]
  screening_threshold: 7
  iterations: 5
  top_n_for_snowball: 10

llm_settings:
  model_screening: "gemini-2.0-flash-lite"

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
│   │   └── screener.py
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
