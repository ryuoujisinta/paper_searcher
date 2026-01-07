import re
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st

from src.models.models import Config, LLMSettings, LoggingConfig, SearchCriteria
from src.utils.constants import CANDIDATE_COLUMNS, CSS_FILE
from src.utils.io_utils import load_config, save_config

# Page Configuration
st.set_page_config(
    page_title="論文レビュー・パイプライン",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load and apply custom CSS from external file
if CSS_FILE.exists():
    with open(CSS_FILE, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.warning("CSSファイルが見つかりません。")


def main():
    st.title("📚 論文レビュー・パイプライン ダッシュボード")
    st.markdown("設定の編集と自動リサーチレビュー・パイプラインの実行が可能です。")

    try:
        config = load_config()
    except Exception as e:
        st.error(f"設定の読み込み中にエラーが発生しました: {e}")
        return

    # Sidebar for navigation
    st.sidebar.header("ナビゲーション")
    menu_options = {"⚙️ 設定": "config", "🚀 実行": "exec", "📊 結果": "results"}
    selection = st.sidebar.radio("移動先", list(menu_options.keys()))
    mode = menu_options[selection]

    if mode == "config":
        st.header("⚙️ パイプライン設定")

        st.subheader("プロジェクト設定")
        project_name = st.text_input("プロジェクト名", config.project_name)

        st.divider()

        st.subheader("検索条件")
        col1, col2 = st.columns(2)

        with col1:
            keywords = st.text_area(
                "キーワード (1行に1つ)",
                value="\n".join(config.search_criteria.keywords),
                height=100,
            )
            nl_query = st.text_area(
                "自然言語クエリ (スコアリング用)",
                value=config.search_criteria.natural_language_query,
                height=50,
            )

            doi_help = "例: 10.1145/3639148 (10.から始まる形式)"
            seed_dois_raw = st.text_area(
                "シード論文のDOI (1行に1つ)",
                value="\n".join(config.search_criteria.seed_paper_dois),
                height=100,
                help=doi_help,
            )

            doi_pattern = re.compile(r"^10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+$")
            seed_dois = [d.strip() for d in seed_dois_raw.split("\n") if d.strip()]
            invalid_dois = [d for d in seed_dois if not doi_pattern.match(d)]

            if invalid_dois:
                st.warning(
                    f"⚠️ 無効なDOI形式が検出されました: {', '.join(invalid_dois)}"
                )

        with col2:
            st.write("反復設定")
            iter_col1, iter_col2 = st.columns(2)
            with iter_col1:
                iterations = st.number_input(
                    "反復回数",
                    value=config.search_criteria.iterations,
                    min_value=1,
                    max_value=5,
                )
            with iter_col2:
                top_n_snowball = st.number_input(
                    "Snowball件数/回",
                    value=config.search_criteria.top_n_for_snowball,
                    min_value=1,
                )

            st.divider()

            limit_col1, limit_col2 = st.columns(2)
            with limit_col1:
                keyword_limit = st.number_input(
                    "キーワード検索制限",
                    value=config.search_criteria.keyword_search_limit,
                    help="キーワード検索で取得する最大件数",
                )
            with limit_col2:
                snowball_limit = st.number_input(
                    "初期Snowball制限",
                    value=config.search_criteria.snowball_from_keywords_limit,
                    help="キーワード検索上位からシードに追加する数",
                )

            min_c_col1, min_c_col2 = st.columns(2)
            with min_c_col1:
                min_citations = st.number_input(
                    "最小引用数", value=config.search_criteria.min_citations
                )

            st.write("発行年範囲")
            year_col1, year_col2 = st.columns(2)
            with year_col1:
                start_year = st.number_input(
                    "開始",
                    value=config.search_criteria.year_range[0],
                    min_value=2000,
                    max_value=2026,
                )
            with year_col2:
                end_year = st.number_input(
                    "終了",
                    value=config.search_criteria.year_range[1],
                    min_value=2000,
                    max_value=2026,
                )
            year_range = [start_year, end_year]
            screening_threshold = st.slider(
                "スクリーニングしきい値 (1-10)",
                1,
                10,
                value=config.search_criteria.screening_threshold,
            )

        st.divider()

        with st.expander("⚙️ 詳細設定", expanded=False):
            adv1, adv2 = st.columns(2)
            with adv1:
                st.markdown("**LLM 設定**")
                model_screening = st.text_input(
                    "スクリーニング用モデル", config.llm_settings.model_screening
                )
                max_workers = st.number_input(
                    "スクリーニング並列数",
                    value=config.llm_settings.max_screening_workers,
                    min_value=1,
                    max_value=20,
                )
            with adv2:
                st.markdown("**ロギング設定**")
                log_level = st.selectbox(
                    "ログレベル",
                    ["DEBUG", "INFO", "WARNING", "ERROR"],
                    index=["DEBUG", "INFO", "WARNING", "ERROR"].index(
                        config.logging.level
                    ),
                )

            st.markdown("**その他収集設定**")
            col_other1, col_other2 = st.columns(2)
            with col_other1:
                max_related = st.number_input(
                    "詳細検索(Snowball)時の最大関連論文数 (-1=無制限)",
                    value=config.search_criteria.max_related_papers,
                    help="-1にすると対象論文のすべての参照・引用論文を取得します。",
                )
            with col_other2:
                max_retries = st.number_input(
                    "APIリトライ最大回数",
                    value=config.search_criteria.max_retries,
                    min_value=0,
                    max_value=50,
                    help="Semantic Scholar API等の呼び出し失敗時の最大リトライ回数",
                )

            st.markdown("**UI設定**")
            ui_col1, ui_col2 = st.columns(2)
            with ui_col1:
                # 既存の列 + 一般的な列の候補
                candidate_cols = list(
                    set(config.ui_settings.essential_columns + CANDIDATE_COLUMNS)
                )

                essential_cols_selected = st.multiselect(
                    "結果表示の必須列を選択",
                    options=candidate_cols,
                    default=config.ui_settings.essential_columns,
                    help="実行結果でデフォルト表示する列を選択します。",
                )

            with ui_col2:
                items_per_page_setting = st.number_input(
                    "1ページあたりの表示件数 (折り返し表示時)",
                    min_value=1,
                    max_value=100,
                    value=config.ui_settings.items_per_page,
                    help="「テキストを折り返して全体を表示」モード時のデフォルト表示件数",
                )

        # Update config object for saving
        updated_config = Config(
            project_name=project_name,
            llm_settings=LLMSettings(
                model_screening=model_screening, max_screening_workers=max_workers
            ),
            logging=LoggingConfig(level=log_level),
            search_criteria=SearchCriteria(
                keywords=[k.strip() for k in keywords.split("\n") if k.strip()],
                natural_language_query=nl_query,
                seed_paper_dois=seed_dois,
                keyword_search_limit=keyword_limit,
                max_related_papers=max_related,
                snowball_from_keywords_limit=snowball_limit,
                min_citations=min_citations,
                year_range=list(year_range),
                screening_threshold=screening_threshold,
                iterations=iterations,
                top_n_for_snowball=top_n_snowball,
                max_retries=max_retries,
            ),
            ui_settings=Config.model_construct().ui_settings.__class__(
                essential_columns=essential_cols_selected,
                items_per_page=items_per_page_setting,
            ),
        )

        if st.button("💾 設定を保存"):
            save_config(updated_config)
            st.success("設定が正常に保存されました！")

    elif mode == "exec":
        # Pipeline Execution
        st.header("🚀 パイプライン実行")
        st.info(f"現在のプロジェクト: **{config.project_name}**")

        if st.button("🚀 パイプライン実行開始"):
            st.info("パイプライン実行を開始しています...")

            log_area = st.empty()
            full_log = ""

            process = subprocess.Popen(
                ["uv", "run", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    full_log += line
                    log_area.code(full_log)

            if process.returncode == 0:
                st.success("パイプラインが正常に終了しました！")
            else:
                st.error(
                    f"パイプラインが終了コード {process.returncode} で失敗しました。"
                )

    elif mode == "results":
        # Results Viewer
        st.header("📊 実行結果")
        project_name = config.project_name
        data_dir = Path("data")
        if data_dir.exists():
            # Match directories like "YYYYMMDD_HHMMSS_{project_name}"
            # The pattern expects exactly 8 digits, underscore, 6 digits, underscore, and project_name
            pattern = re.compile(rf"^\d{{8}}_\d{{6}}_{re.escape(project_name)}$")

            runs = sorted(
                [d for d in data_dir.iterdir() if d.is_dir() and pattern.match(d.name)],
                reverse=True
            )
            if runs:
                selected_run = st.selectbox(
                    "結果を表示する実行を選択してください",
                    runs,
                    format_func=lambda x: x.name,
                )

                final_csv = selected_run / "final" / "final_review_matrix.csv"
                if final_csv.exists():
                    st.subheader(f"{selected_run.name} の結果")
                    df = pd.read_csv(final_csv)

                    # Ensure numeric columns are displayed as integers
                    for col in ["year", "citationCount"]:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

                    # Display options
                    wrap_text = st.checkbox(
                        "テキストを折り返して全体を表示 (st.table)", value=False
                    )

                    cols_to_display = df.columns.tolist()  # default all

                    # Filter columns based on settings
                    essential_cols = config.ui_settings.essential_columns
                    filtered_cols = [col for col in essential_cols if col in df.columns]
                    if filtered_cols:
                        cols_to_display = filtered_cols
                    else:
                        st.warning(
                            "表示対象の列がデータに含まれていません。すべての列を表示します。"
                        )

                    display_df = df[cols_to_display]

                    if wrap_text:
                        # Pagination for st.table
                        items_per_page = config.ui_settings.items_per_page
                        total_items = len(display_df)
                        total_pages = (total_items - 1) // items_per_page + 1

                        if total_pages > 1:
                            page_number = st.number_input(
                                "ページ番号",
                                min_value=1,
                                max_value=total_pages,
                                value=1,
                            )
                            start_idx = (page_number - 1) * items_per_page
                            end_idx = min(start_idx + items_per_page, total_items)

                            st.write(
                                f"全 {total_items} 件中 {start_idx + 1} - {end_idx} 件目を表示"
                            )
                            st.table(display_df.iloc[start_idx:end_idx])
                        else:
                            st.table(display_df)
                    else:
                        st.dataframe(display_df)

                    # Download button
                    with open(final_csv, "rb") as f:
                        st.download_button(
                            label="結果をCSVとしてダウンロード",
                            data=f,
                            file_name=f"{project_name}_{selected_run.name}_final.csv",
                            mime="text/csv",
                        )
                else:
                    st.warning("この実行の最終結果はまだ見つかりません。")
            else:
                st.info("このプロジェクトの実行結果はまだありません。")
        else:
            st.info(
                f"プロジェクト {project_name} のデータディレクトリが見つかりません。"
            )


if __name__ == "__main__":
    main()
