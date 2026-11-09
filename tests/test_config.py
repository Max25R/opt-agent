import pytest

from opt_agent.config import API_KEY_VAR, LIVE_VAR, MissingAPIKeyError, get_api_key


@pytest.fixture
def env_file(tmp_path):
    """A .env file that holds a key, as in the owner's checkout."""
    path = tmp_path / ".env"
    path.write_text(f"{API_KEY_VAR}=file-key\n")
    return path


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv(API_KEY_VAR, raising=False)
    monkeypatch.delenv(LIVE_VAR, raising=False)


def test_reads_key_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(API_KEY_VAR, "env-key")
    monkeypatch.delenv(LIVE_VAR, raising=False)
    assert get_api_key(tmp_path / "missing.env") == "env-key"


def test_an_unset_key_raises_even_with_a_key_in_dotenv(no_key, env_file):
    """The audit's point (section 7.2): unsetting the key must be enough to spend nothing."""
    with pytest.raises(MissingAPIKeyError, match=rf"{LIVE_VAR}=1"):
        get_api_key(env_file)


@pytest.mark.parametrize("value", ["", "0", "true", "yes", " 1"])
def test_only_exactly_1_opens_the_dotenv_file(no_key, env_file, monkeypatch, value):
    monkeypatch.setenv(LIVE_VAR, value)
    with pytest.raises(MissingAPIKeyError):
        get_api_key(env_file)


def test_live_falls_back_to_dotenv_file(no_key, env_file, monkeypatch):
    monkeypatch.setenv(LIVE_VAR, "1")
    assert get_api_key(env_file) == "file-key"


def test_environment_takes_precedence_over_file(monkeypatch, env_file):
    monkeypatch.setenv(API_KEY_VAR, "env-key")
    monkeypatch.setenv(LIVE_VAR, "1")
    assert get_api_key(env_file) == "env-key"


def test_live_with_no_key_anywhere_raises_helpful_error(no_key, monkeypatch, tmp_path):
    monkeypatch.setenv(LIVE_VAR, "1")
    with pytest.raises(MissingAPIKeyError, match=r"\.env\.example"):
        get_api_key(tmp_path / "missing.env")


def test_a_blank_environment_key_is_no_key(no_key, env_file, monkeypatch):
    monkeypatch.setenv(API_KEY_VAR, "   ")
    with pytest.raises(MissingAPIKeyError):
        get_api_key(env_file)
