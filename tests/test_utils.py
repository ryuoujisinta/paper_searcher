import os
import shutil
from unittest.mock import patch

import pytest
import pandas as pd

from src.utils.io_utils import (
    create_run_directory,
    load_config,
    save_config,
    get_prompt,
    save_checkpoint,
    load_checkpoint
)
from src.models.models import Config


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


def test_save_config(tmp_path):
    config = Config(
        project_name="saved_project",
        search_criteria={
            "keywords": ["test"],
            "seed_paper_dois": []
        },
        llm_settings={"model_screening": "dummy"}
    )
    save_path = tmp_path / "saved_config.yml"
    save_config(config, save_path)

    assert save_path.exists()
    loaded = load_config(save_path)
    assert loaded.project_name == "saved_project"


def test_get_prompt(tmp_path):
    # Mock PROMPTS_DIR
    mock_prompts_dir = tmp_path / "prompts"
    mock_prompts_dir.mkdir()
    (mock_prompts_dir / "test_prompt.txt").write_text("Hello {name}", encoding="utf-8")

    # Patch the global constant in the module where it's used
    with patch("src.utils.io_utils.PROMPTS_DIR", mock_prompts_dir):
        content = get_prompt("test_prompt")
        assert content == "Hello {name}"

        with pytest.raises(FileNotFoundError):
            get_prompt("missing_prompt")


def test_checkpoint_io(tmp_path):
    # Test DataFrame CSV
    df = pd.DataFrame({"col": [1, 2]})
    csv_path = tmp_path / "test.csv"
    save_checkpoint(df, csv_path)
    assert csv_path.exists()
    loaded_df = load_checkpoint(csv_path)
    assert len(loaded_df) == 2

    # Test DataFrame Pickle
    pkl_path = tmp_path / "test.pkl"
    save_checkpoint(df, pkl_path)
    assert pkl_path.exists()
    loaded_pkl = load_checkpoint(pkl_path)
    assert len(loaded_pkl) == 2

    # Test Generic Pickle
    data = {"key": "value"}
    obj_path = tmp_path / "test.obj"
    save_checkpoint(data, obj_path)
    assert obj_path.exists()
    loaded_data = load_checkpoint(obj_path)
    assert loaded_data["key"] == "value"
