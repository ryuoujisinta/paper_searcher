# Data Dictionary

## 概要
本プロジェクトで扱われるデータ（論文リスト）の構造定義。
データは主に Pandas DataFrame として保持され、フェーズごとにカラムが追加・統合される。

## 1. データモデル (DataFrame Schema)

### 1.1 共通基本カラム
すべてのフェーズで保持される論文の基本情報。

| カラム名 | 型 | 説明 | 備考 |
| :--- | :--- | :--- | :--- |
| `paperId` | `str` | S2AGが発行する一意なID | 基本的にこのIDで識別 |
| `title` | `str` | 論文タイトル | |
| `abstract` | `str` | 論文アブストラクト | ArXiv補完等の対象 |
| `year` | `int` | 出版年 | 欠損時は `NaN` または `0` |
| `citationCount` | `int` | 被引用数 | `citations` ではない点に注意 |
| `url` | `str` | 論文へのURL | S2AGまたはArXivのリンク |
| `externalIds` | `dict/str` | 外部ID (DOI, ArXiv, MAG等) | JSON文字列または辞書 |
| `doi` | `str` | DOI (Digital Object Identifier) | `externalIds` から抽出・正規化 |

### 1.2 Collector 追加カラム (Raw Data)
収集フェーズ (`src.core.collector`) で付与される情報。

| カラム名 | 型 | 説明 | 備考 |
| :--- | :--- | :--- | :--- |
| `source` | `str` | 収集源 | `keyword_search`, `seed_paper`, `snowball` 等 |
| `iteration` | `int` | 収集されたイテレーション回数 | 1-indexed |

### 1.3 Screener 追加カラム (Interim/Final Data)
選別フェーズ (`src.core.screener`) でLLMにより生成される情報。

| カラム名 | 型 | 説明 | 備考 |
| :--- | :--- | :--- | :--- |
| `relevance_score` | `int` | 研究スコープとの関連度 | 0〜10の整数 |
| `relevance_reason` | `str` | 関連度スコアの理由 | LLM生成テキスト (日本語) |
| `summary` | `str` | 論文の要約 | LLM生成テキスト (日本語) |

## 2. ファイル出力仕様

### 2.1 Raw Data (`data/<project>/<timestamp>/raw/*.csv`)
- Collectorが収集した直後の生データ。
- カラム: 共通基本カラム + Collector追加カラム

### 2.2 Interim Data (`data/<project>/<timestamp>/interim/*.csv`)
- Screening済みのデータ。
- カラム: Raw Data + Screener追加カラム

### 2.3 Final Output (`data/<project>/<timestamp>/final/final_review_matrix.csv`)
- 最終成果物。ユーザーが見やすいようにカラム順序が整理されている。

**出力カラム順序:**
1. `relevance_score`
2. `title`
3. `year`
4. `citationCount`
5. `summary`
6. `relevance_reason`
7. `url`
8. `doi`
9. `abstract`
