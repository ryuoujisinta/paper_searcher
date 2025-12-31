import subprocess
from pathlib import Path

import streamlit as st
import pandas as pd

from src.utils.constants import CSS_FILE
from src.utils.io_utils import load_config, save_config
from src.models.models import Config, LLMSettings, LoggingConfig, SearchCriteria

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
    menu_options = {
        "⚙️ 設定": "config",
        "🚀 実行": "exec"
    }
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
            keywords = st.text_area("キーワード (1行に1つ)", value="\n".join(config.search_criteria.keywords), height=150)

            doi_help = "例: 10.1145/3639148 (10.から始まる形式)"
            seed_dois_raw = st.text_area("シード論文のDOI (1行に1つ)",
                                         value="\n".join(config.search_criteria.seed_paper_dois),
                                         height=150,
                                         help=doi_help)

            # DOI Format Check
            import re
            doi_pattern = re.compile(r"^10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+$")
            seed_dois = [d.strip() for d in seed_dois_raw.split("\n") if d.strip()]
            invalid_dois = [d for d in seed_dois if not doi_pattern.match(d)]

            if invalid_dois:
                st.warning(f"⚠️ 無効なDOI形式が検出されました: {', '.join(invalid_dois)}")

        with col2:
            limit_col1, limit_col2 = st.columns(2)
            with limit_col1:
                snowball_limit = st.number_input("スノーボール制限", value=config.search_criteria.snowball_from_keywords_limit)
            with limit_col2:
                min_citations = st.number_input("最小引用数", value=config.search_criteria.min_citations)

            st.write("発行年範囲")
            year_col1, year_col2 = st.columns(2)
            with year_col1:
                start_year = st.number_input(
                    "開始",
                    value=config.search_criteria.year_range[0],
                    min_value=2000,
                    max_value=2026
                )
            with year_col2:
                end_year = st.number_input(
                    "終了",
                    value=config.search_criteria.year_range[1],
                    min_value=2000,
                    max_value=2026
                )
            year_range = [start_year, end_year]
            screening_threshold = st.slider(
                "スクリーニングしきい値 (1-10)", 1, 10,
                value=config.search_criteria.screening_threshold
            )

        st.divider()

        with st.expander("⚙️ 詳細設定", expanded=False):
            adv1, adv2 = st.columns(2)
            with adv1:
                st.markdown("**LLM 設定**")
                model_screening = st.text_input("スクリーニング用モデル", config.llm_settings.model_screening)
                model_extraction = st.text_input("データ抽出用モデル", config.llm_settings.model_extraction)
            with adv2:
                st.markdown("**ロギング設定**")
                log_level = st.selectbox(
                    "ログレベル",
                    ["DEBUG", "INFO", "WARNING", "ERROR"],
                    index=["DEBUG", "INFO", "WARNING", "ERROR"].index(config.logging.level)
                )

        # Update config object for saving
        updated_config = Config(
            project_name=project_name,
            llm_settings=LLMSettings(model_screening=model_screening, model_extraction=model_extraction),
            logging=LoggingConfig(level=log_level),
            search_criteria=SearchCriteria(
                keywords=[k.strip() for k in keywords.split("\n") if k.strip()],
                seed_paper_dois=seed_dois,
                snowball_from_keywords_limit=snowball_limit,
                min_citations=min_citations,
                year_range=list(year_range),
                screening_threshold=screening_threshold
            )
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
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
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
                st.error(f"パイプラインが終了コード {process.returncode} で失敗しました。")

        st.divider()

        # Results Viewer
        st.header("📊 実行結果")
        project_name = config.project_name
        data_dir = Path("data") / project_name
        if data_dir.exists():
            runs = sorted([d for d in data_dir.iterdir() if d.is_dir()], reverse=True)
            if runs:
                selected_run = st.selectbox("結果を表示する実行を選択してください", runs, format_func=lambda x: x.name)

                final_csv = selected_run / "final" / "final_review_matrix.csv"
                if final_csv.exists():
                    st.subheader(f"{selected_run.name} の結果")
                    df = pd.read_csv(final_csv)
                    st.dataframe(df)

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
            st.info(f"プロジェクト {project_name} のデータディレクトリが見つかりません。")


if __name__ == "__main__":
    main()
