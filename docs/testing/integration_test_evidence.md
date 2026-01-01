# 結合テスト根拠資料 (Integration Test Evidence)

## 1. 概要
本ドキュメントは、2026年1月1日に実施された結合テストの結果を裏付けるエビデンス（出力ログ、生成データ、スクリーンショット等）の所在と内容をまとめたものである。

## 2. 実機テスト実施結果 (Backend)

`main.py` を用いたパイプライン実行テストの成果物は以下のディレクトリに保存されている。

| テストID | テスト項目名 | プロジェクト名 (Config) | 生成データディレクトリ (Evidence Path) | 主な確認事項 |
| :--- | :--- | :--- | :--- | :--- |
| **TC-F-01** | 基本フロー実行 | `test_integration_f01` | `data/20260101_164837_test_integration_f01` | ・`final/final_review_matrix.csv` が生成されていること。<br>・Relevance Score付与済みの論文が含まれていること。 |
| **TC-F-02** | Snowball反復実行確認 | `test_integration_f02` | `data/20260101_164928_test_integration_f02` | ・`raw/collected_papers_iter_1.csv` と `iter_2` (cumulative) の増分確認。<br>・Iteration 2で収集された論文がSnowball由来であること。 |
| **TC-F-03** | フィルタリング条件の反映 | `test_integration_f03` | `data/20260101_165011_test_integration_f03` | ・検索ヒット数が10件に対し、最終出力が0件であること（`min_citations=1000` により全件除外された結果）。 |
| **TC-E-01** | 無効なAPIキー | `test_integration_e01` | `data/20260101_165048_test_integration_e01` | ・ログに `400 INVALID_ARGUMENT` エラーが記録されていること。<br>・プロセスが異常終了せず完了していること。 |
| **TC-E-02** | 検索結果ゼロ件 | `test_integration_e02` | `data/20260101_165128_test_integration_e02` | ・ログに `Searching papers for keywords: xhdkjhfkjsdhf` およびS2 APIのリトライ/空結果が記録されていること。 |
| **TC-E-03** | UIからの無効なDOI入力 | `test_integration_e03` | `data/20260101_165222_test_integration_e03` | ・`seed_paper_dois: ['invalid_doi']` に対する処理ログ。<br>・APIリトライ後にスキップまたは空結果となっていること。 |

## 3. UI自動操作テスト実施結果 (Frontend)

ブラウザ自動操作ツールを用いたUIテストの結果。

### TC-U-01: 設定保存の永続化
*   **実施日時**: 2026-01-01 16:54頃
*   **実施内容**:
    1.  `app.py` 起動
    2.  プロジェクト名を `UI_Test_Project` に変更
    3.  キーワードを `Test Keyword` に変更
    4.  「設定を保存」ボタン押下
    5.  ページリロード
*   **確認結果**:
    *   リロード後もプロジェクト名およびキーワードが変更後の値（`UI_Test_Project`, `Test Keyword`）で表示されることを確認。
*   **エビデンスファイル**:
    *   自動操作ログ・録画: `ui_test_tcu01_1767254064266.webp` (Artifactsディレクトリに保存)

### TC-U-02: 結果CSVのダウンロード
*   **実施結果**: 未完了 (ユーザー指示により中断)
*   **備考**: `TC-F-01` 等の結果ディレクトリから手動でCSVを開くことでデータ内容は確認済み。UI上のダウンロードボタン動作のみ未検証。

## 4. 補足情報の確認方法
各テスト実行時の詳細なログや、具体的なデータの確認が必要な場合は、上記の `Evidence Path` 内の `final_review_matrix.csv` または `app.log` (設定されていれば) を参照すること。
特に `TC-D-01` (データ整合性) については、`TC-F-01` の出力CSVを用いて下記項目を目視確認済み：
*   日本語サマリ (`summary`) の存在
*   `relevance_score` の付与
*   文字化けがないこと (UTF-8)
