import os
import shutil
from pathlib import Path

import pytest
from src.io_utils import create_run_directory, load_config


def test_load_config(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("project_name: 'test'", encoding="utf-8")

    config = load_config(str(config_file))
    assert config["project_name"] == "test"


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

    # クリーンアップ
    shutil.rmtree(data_dir)
