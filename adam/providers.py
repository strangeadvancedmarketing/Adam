"""
Adam Framework — LLM Provider Abstraction Layer

Supports Gemini, OpenAI, Anthropic, Ollama, and any OpenAI-compatible endpoint.
Used by reconcile_memory and other tools that need LLM completions.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

import requests


class LLMProvider(Protocol):
    """Interface for LLM providers."""

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        """Send a completion request and return the text response."""
        ...


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for an LLM provider."""
    provider: str  # gemini, openai, anthropic, ollama
    api_key: str = ""
    base_url: str = ""
    model: str = ""

    @staticmethod
    def from_env() -> ProviderConfig:
        """Auto-detect provider from environment variables."""
        if os.environ.get("GEMINI_API_KEY"):
            return ProviderConfig(
                provider="gemini",
                api_key=os.environ["GEMINI_API_KEY"],
                model=os.environ.get("ADAM_MODEL", "gemini-1.5-flash"),
            )
        if os.environ.get("OPENAI_API_KEY"):
            return ProviderConfig(
                provider="openai",
                api_key=os.environ["OPENAI_API_KEY"],
                base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.environ.get("ADAM_MODEL", "gpt-4o-mini"),
            )
        if os.environ.get("ANTHROPIC_API_KEY"):
            return ProviderConfig(
                provider="anthropic",
                api_key=os.environ["ANTHROPIC_API_KEY"],
                model=os.environ.get("ADAM_MODEL", "claude-sonnet-4-6"),
            )
        # Default to Ollama (local, no key needed)
        return ProviderConfig(
            provider="ollama",
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.environ.get("ADAM_MODEL", "llama3.3"),
        )

    @staticmethod
    def from_config_file(path: str) -> ProviderConfig:
        """Read provider config from an openclaw.json or mcporter.json file."""
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # Try Gemini key from openclaw.json env block
        env = cfg.get("env", {})
        if env.get("GEMINI_API_KEY"):
            return ProviderConfig(
                provider="gemini",
                api_key=env["GEMINI_API_KEY"],
                model="gemini-1.5-flash",
            )

        # Try mcporter.json nested under mcpServers.gemini.env
        servers = cfg.get("mcpServers", cfg.get("servers", {}))
        gemini_env = servers.get("gemini", {}).get("env", {})
        if gemini_env.get("GEMINI_API_KEY"):
            return ProviderConfig(
                provider="gemini",
                api_key=gemini_env["GEMINI_API_KEY"],
                model="gemini-1.5-flash",
            )

        # Try OpenAI-compatible from model config
        model_cfg = cfg.get("model", {})
        if model_cfg.get("baseURL"):
            return ProviderConfig(
                provider="openai",
                api_key=model_cfg.get("apiKey", env.get("OPENAI_API_KEY", "")),
                base_url=model_cfg["baseURL"],
                model=model_cfg.get("name", "gpt-4o-mini"),
            )

        raise ValueError(f"No LLM provider credentials found in {path}")


class GeminiProvider:
    """Google Gemini API provider."""

    def __init__(self, config: ProviderConfig) -> None:
        self.api_key = config.api_key
        self.model = config.model or "gemini-1.5-flash"

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


class OpenAIProvider:
    """OpenAI-compatible API provider (works with OpenAI, OpenRouter, Ollama, etc.)."""

    def __init__(self, config: ProviderConfig) -> None:
        self.api_key = config.api_key
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.model = config.model or "gpt-4o-mini"

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class AnthropicProvider:
    """Anthropic Claude API provider."""

    def __init__(self, config: ProviderConfig) -> None:
        self.api_key = config.api_key
        self.model = config.model or "claude-sonnet-4-6"

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


class OllamaProvider:
    """Ollama local model provider (OpenAI-compatible endpoint)."""

    def __init__(self, config: ProviderConfig) -> None:
        self.base_url = config.base_url or "http://localhost:11434"
        self.model = config.model or "llama3.3"

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# Provider registry
_PROVIDERS: dict[str, type] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}


def create_provider(config: ProviderConfig) -> LLMProvider:
    """Create an LLM provider instance from config."""
    provider_cls = _PROVIDERS.get(config.provider)
    if provider_cls is None:
        # Fall back to OpenAI-compatible for unknown providers
        provider_cls = OpenAIProvider
    return provider_cls(config)


def get_provider(config_path: str | None = None) -> LLMProvider:
    """Get an LLM provider, trying config file first, then environment."""
    if config_path:
        cfg = ProviderConfig.from_config_file(config_path)
    else:
        cfg = ProviderConfig.from_env()
    return create_provider(cfg)
