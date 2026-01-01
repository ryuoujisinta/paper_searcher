import os
import shutil

import pytest

from src.utils.io_utils import create_run_directory, load_config


def test_load_config(tmp_path):
    config_file = tmp_path / "config.yml"
    config_content = """
project_name: 'test'
logging:
  level: 'INFO'
search_criteria:
  keywords: ['test']
  seed_paper_dois: []
llm_settings:
  model_screening: 'dummy'
"""
    config_file.write_text(config_content.strip(), encoding="utf-8")

    config = load_config(str(config_file))
    assert config.project_name == "test"
    assert config.logging.level == "INFO"


def test_load_config_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_config.yml")


def test_create_run_directory(tmp_path, monkeypatch):
    # data/ ディレクトリを一時ディレクトリ配下に作成するように変更
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # OSのカレントディレクトリをtmp_pathに変更
    os.chdir(tmp_path)

    # ダミーの設定ファイル
    with open("config.yml", "w") as f:
        f.write("project_name: 'test_project'")

    run_dir = create_run_directory("test_project")

    assert run_dir.exists()
    assert (run_dir / "raw").exists()
    assert (run_dir / "config.yml").exists()

    # Clean up
    if data_dir.exists():
        shutil.rmtree(data_dir)
