# 詳細設計: Screener (選別)

## 1. 役割
`PaperScreener` クラスは、LLM（Gemini）を利用して、収集された論文のアブストラクトを解析し、ユーザーが定義した研究スコープへの適合性を判定する。

## 2. 主要機能

### 2.1 LLM 判定 (`_call_llm`)
- **モデル:** `gemini-2.0-flash-lite` (デフォルト)。
- **プロンプト:** `prompts/screening.txt` を使用。
    - `research_scope`: 自然言語クエリ (`natural_language_query`) とキーワードから構成される検索意図。
    - `title`, `abstract`: 論文の情報。
- **JSON Mode:** `google-genai` の SDK 機能を使い、構造化データとして取得。
    - `relevance_score` (0-10)
    - `relevance_reason` (理由)
    - `summary` (日本語による簡潔な要約)
- **Pydantic 連携:** `ScreeningResult` モデルを用いて、LLM の出力を検証。

### 2.2 並列処理 (`screen_papers`)
- **方式:** `ThreadPoolExecutor` によるスレッド並列実行。
- **並列数:** デフォルト 5 スレッド。
- **進捗管理:** `tqdm` ベースの `ProgressTracker` を用いて、処理状況を可視化。
- **エラー耐性:** 個別の論文で LLM 呼び出しが失敗しても、ログを記録しつつ全体の処理を継続。失敗した論文はスコア 0 としてマークされる。

## 3. 処理フロー
1. Phase 1 から論文リスト（DataFrame）を受け取る。
2. アブストラクトが存在する論文のみを対象に並列処理。
3. LLM が 0-10 の `relevance_score` とその理由を生成。
4. 元の DataFrame に結果のカラムを結合して返す。

## 4. 非機能仕様
- **スループット:** 並列処理により、数百件の論文を数分以内にスクリーニング可能。
- **コスト:** Flash-Lite モデルを採用することで、大量のトークン消費を抑え、コスト効率を最大化。
- **ロギング:** LLM からの無効なレスポンスや API 接続エラーを詳細に記録。
