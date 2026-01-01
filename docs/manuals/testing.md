# Testing Strategy

## 1. テストの目的
- **信頼性**: パイプラインの各段階（収集、選別、統合）が期待通りに動作することを保証する。
- **保守性**: リファクタリング時の退行（リグレッション）を防ぐ。

## 2. テストの分類

### 2.1 Unit Tests (`tests/`)
モジュール単位での機能検証を行います。
- **対象**: `src/core/`, `src/utils/`
- **方針**: 外部API (Semantic Scholar, ArXiv, Gemini) は**すべてモック (Mock)** します。
- **ツール**: `pytest`, `unittest.mock`

### 2.2 Integration Tests
(現状は手動実行が主)
- APIキーを用いた実際のE2E実行 (`main.py`) により、外部サービスとの連携を確認します。
- CIには含めず、ローカル環境での開発時に実施します。

## 3. モック方針

### 3.1 Semantic Scholar (Collector)
- `requests.get` をパッチし、ダミーのJSONレスポンスを返却します。
- **検証項目**: パラメータ構築が正しいか、レスポンスのパースが正しいか、リトライロジックが呼ばれるか。

### 3.2 LLM (Screener)
- `google.genai.Client` または `_call_llm` メソッドをモックします。
- **検証項目**: プロンプト生成ロジック、JSONパースエラー時の挙動。

## 4. テスト実行方法

```powershell
# 全テストの実行
uv run pytest

# 特定ファイルのテスト
uv run pytest tests/test_collector.py
```

## 5. カバレッジと品質基準
- **Flake8**: `uv run flake8` でコードスタイル違反がないこと。
- **Coverage**: 主要なロジック分岐をカバーすることを目指す。
