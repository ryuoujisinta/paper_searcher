import subprocess
from pathlib import Path

import streamlit as st
import yaml
import pandas as pd

from src.constants import CSS_FILE, DEFAULT_CONFIG_PATH
from src.io_utils import load_config as io_load_config

# Page Configuration
st.set_page_config(
    page_title="Paper Review Pipeline",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load and apply custom CSS from external file
if CSS_FILE.exists():
    with open(CSS_FILE, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.warning("CSS file not found.")

CONFIG_PATH = DEFAULT_CONFIG_PATH


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)


def main():
    st.title("📚 Paper Review Pipeline Dashboard")
    st.markdown("Edit your configuration and trigger the automated research review pipeline.")

    config = load_config()

    # Sidebar for navigation
    st.sidebar.header("Navigation")
    menu_options = {
        "⚙️ Configuration": "config",
        "🚀 Execution": "exec"
    }
    selection = st.sidebar.radio("Go to", list(menu_options.keys()))
    mode = menu_options[selection]

    if mode == "config":
        st.header("⚙️ Pipeline Configuration")

        st.subheader("Project Settings")
        project_name = st.text_input("Project Name", config.get("project_name", "my_project"))

        st.divider()

        st.subheader("Search Criteria")
        col1, col2 = st.columns(2)

        with col1:
            keywords = st.text_area("Keywords (one per line)", value="\n".join(config.get("search_criteria", {}).get("keywords", [])), height=150)

            doi_help = "Example: 10.1145/3639148 (Starts with 10.)"
            seed_dois_raw = st.text_area("Seed Paper DOIs (one per line)",
                                         value="\n".join(config.get("search_criteria", {}).get("seed_paper_dois", [])),
                                         height=150,
                                         help=doi_help)

            # DOI Format Check
            import re
            doi_pattern = re.compile(r"^10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+$")
            seed_dois = [d.strip() for d in seed_dois_raw.split("\n") if d.strip()]
            invalid_dois = [d for d in seed_dois if not doi_pattern.match(d)]

            if invalid_dois:
                st.warning(f"⚠️ Invalid DOI format detected: {', '.join(invalid_dois)}")

        with col2:
            limit_col1, limit_col2 = st.columns(2)
            with limit_col1:
                snowball_limit = st.number_input("Snowball Limit", value=config.get("search_criteria", {}).get("snowball_from_keywords_limit", 5))
            with limit_col2:
                min_citations = st.number_input("Min Citations", value=config.get("search_criteria", {}).get("min_citations", 10))

            st.write("Year Range")
            year_col1, year_col2 = st.columns(2)
            with year_col1:
                start_year = st.number_input("Start", value=config.get("search_criteria", {}).get("year_range", [2020, 2025])[0], min_value=2000, max_value=2026)
            with year_col2:
                end_year = st.number_input("End", value=config.get("search_criteria", {}).get("year_range", [2020, 2025])[1], min_value=2000, max_value=2026)
            year_range = [start_year, end_year]
            screening_threshold = st.slider("Screening Threshold (1-10)", 1, 10, value=config.get("search_criteria", {}).get("screening_threshold", 7))

        st.divider()

        with st.expander("⚙️ Advanced Settings", expanded=False):
            adv1, adv2 = st.columns(2)
            with adv1:
                st.markdown("**LLM Settings**")
                model_screening = st.text_input("Screening Model", config.get("llm_settings", {}).get("model_screening", "gemini-2.0-flash"))
                model_extraction = st.text_input("Extraction Model", config.get("llm_settings", {}).get("model_extraction", "gemini-2.0-flash"))
            with adv2:
                st.markdown("**Logging Settings**")
                log_level = st.selectbox("Logging Level", ["DEBUG", "INFO", "WARNING", "ERROR"], index=["DEBUG", "INFO", "WARNING", "ERROR"].index(config.get("logging", {}).get("level", "INFO")))

        # Update config object locally for persistence
        updated_config = config.copy()
        updated_config["project_name"] = project_name
        updated_config["llm_settings"] = {"model_screening": model_screening, "model_extraction": model_extraction}
        updated_config["logging"] = {"level": log_level}
        updated_config["search_criteria"] = {
            "keywords": [k.strip() for k in keywords.split("\n") if k.strip()],
            "seed_paper_dois": seed_dois,
            "snowball_from_keywords_limit": snowball_limit,
            "min_citations": min_citations,
            "year_range": list(year_range),
            "screening_threshold": screening_threshold
        }

        if st.button("💾 Save Configuration"):
            save_config(updated_config)
            st.success("Configuration saved successfully!")

    elif mode == "exec":
        # Pipeline Execution
        st.header("🚀 Pipeline Execution")
        st.info(f"Current project: **{config.get('project_name', 'my_project')}**")

        if st.button("🚀 Start Pipeline Run"):
            st.info("Starting pipeline execution...")

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
                st.success("Pipeline completed successfully!")
            else:
                st.error(f"Pipeline failed with exit code {process.returncode}")

        st.divider()

        # Results Viewer
        st.header("📊 Execution Results")
        project_name = config.get("project_name", "my_project")
        data_dir = Path("data") / project_name
        if data_dir.exists():
            runs = sorted([d for d in data_dir.iterdir() if d.is_dir()], reverse=True)
            if runs:
                selected_run = st.selectbox("Select a run to view results", runs, format_func=lambda x: x.name)

                final_csv = selected_run / "final" / "final_review_matrix.csv"
                if final_csv.exists():
                    st.subheader(f"Results for {selected_run.name}")
                    df = pd.read_csv(final_csv)
                    st.dataframe(df)

                    # Download button
                    with open(final_csv, "rb") as f:
                        st.download_button(
                            label="Download results as CSV",
                            data=f,
                            file_name=f"{project_name}_{selected_run.name}_final.csv",
                            mime="text/csv",
                        )
                else:
                    st.warning("No final results found for this run yet.")
            else:
                st.info("No runs found for this project yet.")
        else:
            st.info(f"No data directory found for project: {project_name}")


if __name__ == "__main__":
    main()
