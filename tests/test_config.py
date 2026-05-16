from pathlib import Path

from core.config import AppConfig, load_config


def test_load_config_shapes() -> None:
    cfg = load_config()
    assert isinstance(cfg, AppConfig)
    assert cfg.openai_chat_model
    assert cfg.rag_retrieval_k > 0


def test_paths_are_under_project() -> None:
    cfg = load_config()
    assert cfg.logs_dir.name == "logs"
    assert cfg.faiss_index_name
