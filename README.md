# Review Paper Automator

特定の研究テーマに関して、重要論文（Seed Papers）やキーワードを起点に先行研究を効率的に収集・選別し、レビュー論文（Survey Paper）の執筆を支援するツールです。

## 🚀 主な機能

- **Phase 1: Collection (収集)**: Semantic Scholar API を使用し、キーワード検索と引用ネットワーク探索（スノーボールサンプリング）を組み合わせて候補論文を収集します。多段階の反復プロセスにより、関連性の高い論文を効率的に発掘します。
- **Phase 2: Screening (選別)**: LLM (Gemini 1.5 Flash など) を用いて、アブストラクトの内容が研究スコープに合致するかを自動判定し、要約を生成します。

## 🛠 技術スタック

- **Language:** Python 3.13
- **Package Manager:** [uv](https://github.com/astral-sh/uv)
- **Framework:** [Streamlit](https://streamlit.io/) (Web UI)
- **API:** Semantic Scholar (S2AG), ArXiv
- **LLM:** Google Generative AI (Gemini)
- **Libraries:** `pandas`, `pydantic`, `tenacity`, `pyyaml`

## 📦 セットアップ

### 1. uv のインストール

`uv` がインストールされていない場合は、公式サイトの指示に従ってインストールしてください。
(Windows の例: `powershell -ExecutionPolicy ByPass -c "ir https://astral.sh/uv/install.ps1"`)

### 2. 依存関係のインストール

プロジェクトディレクトリで以下のコマンドを実行します。

```powershell
uv sync
```

### 3. 環境設定

`.env` ファイルを作成し、必要な API キーを設定してください。

```env
GOOGLE_API_KEY=your_google_api_key
# SEMANTIC_SCHOLAR_API_KEY=your_s2_api_key (推奨)
```

## 📖 使い方

### Web UI での実行（推奨）

以下のコマンドでダッシュボードを起動し、ブラウザ上で設定編集と実行を行えます。

```powershell
uv run streamlit run app.py
```

### CLI での実行

1. `config.yml` を編集し、検索キーワードや Seed Paper の DOI、フィルタリング条件を設定します。
2. 以下のコマンドでプロジェクトを実行します。

```powershell
uv run main.py
```

## 📁 ディレクトリ構成

- `src/`: ソースコード (Collector, Screener 等)
- `data/`: 実行結果や中間データ（プロジェクト名+日付ごとに保存）
- `docs/`: 仕様書などのドキュメント
    - `design/`: 詳細設計書 (`collector.md`, `screener.md`, `dashboard.md`)
    - `manuals/`: 運用・テストマニュアル (`operations.md`, `testing.md`)
    - `reference/`: データ定義 (`data_dictionary.md`)
- `prompts/`: LLM 用のプロンプトテンプレート
- `config.yml`: 検索・選別の設定
- `app.py`: Web UI エントリーポイント
- `main.py`: CLI エントリーポイント
- `pyproject.toml`: 依存ライブラリ管理

## 📝 ライセンス

MIT License
