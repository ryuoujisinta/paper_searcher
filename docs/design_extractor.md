# 詳細設計: Extractor (情報抽出)

## 1. 役割
`PaperExtractor` クラスは、スクリーニングを通過した高品質な論文のみを対象に、レビュー論文の執筆（比較表の作成）に必要な詳細情報を LLM で抽出する。

## 2. 主要機能

### 2.1 構造化データ抽出 (`_call_llm`)
- **モデル:** `gemini-2.0-flash-lite`。
- **抽出スキーマ (`ExtractionResult`):** 全て文字列（Pydantic で定義）。
    1. `problem`: 具体的な研究課題。
    2. `method`: 提案手法の名称。
    3. `dataset`: 使用したデータセット。
    4. `metric`: 評価指標と主な結果数値。
    5. `limitation`: 論文内で言及されている限界点。
    6. `category`: `Method`, `Survey`, `Theory`, `Application` から選択。
    7. `one_line_summary`: 日本語による簡潔な1行要約。

### 2.2 並列処理 (`extract_info`)
- **方式:** `ThreadPoolExecutor` を使用。
- **同期処理:** スクリーニング同様、`ProgressTracker` で進捗を表示。
- **フォールバック:** エラー発生時は全フィールドを `"Error"` として埋め、リストの整合性を維持。

## 3. 処理フロー
1. スクリーニング後の `relevance_score` が閾値以上の論文を抽出対象とする。
2. 論文ごとにアブストラクトを入力とし、LLM を呼び出す。
3. 抽出された情報を DataFrame のカラムとして追加。
4. 最終的なレビューマトリックスとして返却。

## 4. 非機能仕様
- **出力品質:** `response_mime_type: "application/json"` と `response_schema` を指定することで、確実な JSON 構造を保証。
- **要約の言語:** プロンプトにて「日本語での要約」を明示的に指示。
