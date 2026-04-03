"""Tests for adam.providers module."""

import os

import pytest

from adam.providers import (
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderConfig,
    create_provider,
)


class TestProviderConfig:
    def test_from_env_gemini(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cfg = ProviderConfig.from_env()
        assert cfg.provider == "gemini"
        assert cfg.api_key == "test-key"

    def test_from_env_openai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cfg = ProviderConfig.from_env()
        assert cfg.provider == "openai"

    def test_from_env_anthropic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        cfg = ProviderConfig.from_env()
        assert cfg.provider == "anthropic"

    def test_from_env_defaults_to_ollama(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cfg = ProviderConfig.from_env()
        assert cfg.provider == "ollama"

    def test_from_config_file(self, tmp_path: pytest.TempPathFactory) -> None:
        config = {"env": {"GEMINI_API_KEY": "file-key"}}
        config_file = tmp_path / "config.json"  # type: ignore[operator]
        config_file.write_text('{"env": {"GEMINI_API_KEY": "file-key"}}')
        cfg = ProviderConfig.from_config_file(str(config_file))
        assert cfg.provider == "gemini"
        assert cfg.api_key == "file-key"


class TestCreateProvider:
    def test_creates_gemini(self) -> None:
        cfg = ProviderConfig(provider="gemini", api_key="test")
        provider = create_provider(cfg)
        assert isinstance(provider, GeminiProvider)

    def test_creates_openai(self) -> None:
        cfg = ProviderConfig(provider="openai", api_key="test")
        provider = create_provider(cfg)
        assert isinstance(provider, OpenAIProvider)

    def test_creates_anthropic(self) -> None:
        cfg = ProviderConfig(provider="anthropic", api_key="test")
        provider = create_provider(cfg)
        assert isinstance(provider, AnthropicProvider)

    def test_creates_ollama(self) -> None:
        cfg = ProviderConfig(provider="ollama")
        provider = create_provider(cfg)
        assert isinstance(provider, OllamaProvider)

    def test_unknown_falls_back_to_openai(self) -> None:
        cfg = ProviderConfig(provider="custom", base_url="http://localhost:1234")
        provider = create_provider(cfg)
        assert isinstance(provider, OpenAIProvider)
