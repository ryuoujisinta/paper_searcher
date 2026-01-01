# 結合テスト観点書 (Integration Test Plan)

## 1. 目的
本ドキュメントは、論文自動レビューパイプライン（`Collector`, `Screener`, `Main`, `App`）の各モジュール間連携が正しく機能し、システム全体として要件を満たすことを確認するための結合テスト計画を定義する。

## 2. テスト対象範囲
以下のモジュール間の連携およびデータフローを対象とする。

1.  **UI - Backend連携**: `app.py`（Streamlit UI）と `main.py`（実行スクリプト）の連携。設定ファイル（`config.yml`）を介したパラメータの受け渡し。
2.  **Collector - Screener連携**: 論文収集機能とスクリーニング機能のデータ連携。DataFrameの構造的一貫性。
3.  **Core Logic - External API連携**: 各種外部API（Semantic Scholar, ArXiv, Google Gemini）との接続とエラーハンドリング（モックまたは実環境での動作確認）。
4.  **Iterative Pipeline連携**: `main.py` における反復処理（Search -> Screen -> Snowball -> Search）のロジック整合性。

## 3. テスト環境
-   **OS**: Windows
-   **Python**: 3.x
-   **Dependencies**: `requirements.txt` / `pyproject.toml` に記載のライブラリ
-   **External APIs**:
    -   Semantic Scholar API (Public)
    -   ArXiv API (Public)
    -   Google Gemini API (API Key required)

## 4. テスト観点 (Test Viewpoints)

### 4.1 機能結合観点 (Functional Integration)
| ID | 観点 | 説明 |
| :--- | :--- | :--- |
| **IT-F-01** | パイプライン実行（正常系） | UIから正常にパイプラインを起動し、全工程がエラーなく完了すること。 |
| **IT-F-02** | 設定パラメータの反映 | UIで設定したキーワード、期間、件数制限が、バックエンドの各処理に正しく反映されていること。 |
| **IT-F-03** | スノーボールサンプリング連携 | 1回目の結果（高スコア論文）が、2回目の検索シードとして正しく利用されていること。 |
| **IT-F-04** | 抄録補完機能の連携 | Semantic Scholarで抄録がない論文に対し、ArXiv検索による補完が機能し、Screenerに渡されていること。 |

### 4.2 データ整合性観点 (Data Consistency)
| ID | 観点 | 説明 |
| :--- | :--- | :--- |
| **IT-D-01** | データ構造の維持 | `Collector`が出力するDataFrameのカラム（doi, title, abstract等）が、`Screener`の入力要件を満たしていること。 |
| **IT-D-02** | 結果データの保存 | `raw`, `interim`, `final` ディレクトリに、各段階のCSVが仕様通りのフォーマットで保存されていること。 |
| **IT-D-03** | 文字コード・形式 | 日本語を含むデータが文字化けせず（UTF-8 sig）、CSVとして正しくAre読み書きできること。 |

### 4.3 異常系・境界値観点 (Error Handling & Boundary)
| ID | 観点 | 説明 |
| :--- | :--- | :--- |
| **IT-E-01** | APIエラーハンドリング | 外部API（S2, Gemini）がエラー（429, 500等）を返した際、システムがクラッシュせず、適切にリトライまたはスキップすること。 |
| **IT-E-02** | 検索結果ゼロ時の挙動 | キーワード検索でヒット件数が0件の場合、またはフィルタリングですべて除外された場合、適切に処理を終了（または通知）すること。 |
| **IT-E-03** | 不正な入力データ | DOI形式不正や、必須フィールド欠損（Titleなし等）の論文データが含まれていた場合、当該レコードをスキップして処理を継続すること。 |

### 4.4 UI/操作性観点 (UI Experience)
| ID | 観点 | 説明 |
| :--- | :--- | :--- |
| **IT-U-01** | 実行ログの表示 | パイプライン実行中、UI上にリアルタイム（に近い）ログが表示され、進行状況が把握できること。 |
| **IT-U-02** | 結果の閲覧・DL | 実行完了後、生成された成果物（CSV）をUI上でプレビューおよびダウンロードできること。 |
