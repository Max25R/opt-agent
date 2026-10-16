import pytest

from opt_agent.config import API_KEY_VAR, MissingAPIKeyError, get_api_key


def test_reads_key_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(API_KEY_VAR, "env-key")
    assert get_api_key(tmp_path / "missing.env") == "env-key"


def test_falls_back_to_dotenv_file(monkeypatch, tmp_path):
    monkeypatch.delenv(API_KEY_VAR, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"{API_KEY_VAR}=file-key\n")
    assert get_api_key(env_file) == "file-key"


def test_environment_takes_precedence_over_file(monkeypatch, tmp_path):
    monkeypatch.setenv(API_KEY_VAR, "env-key")
    env_file = tmp_path / ".env"
    env_file.write_text(f"{API_KEY_VAR}=file-key\n")
    assert get_api_key(env_file) == "env-key"


def test_missing_key_raises_helpful_error(monkeypatch, tmp_path):
    monkeypatch.delenv(API_KEY_VAR, raising=False)
    with pytest.raises(MissingAPIKeyError, match=r"\.env\.example"):
        get_api_key(tmp_path / "missing.env")
