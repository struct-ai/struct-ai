"""Pydantic schema for .struct-ia.yaml — local architectural configuration.

Layers are ordered from lowest (most foundational, index 0) to highest (most
outer). Position in the list IS the dependency level: a layer at index i may
only import layers at index <= i.
"""

from typing import Literal

from pydantic import BaseModel, Field

ProviderSlug = Literal["openai", "anthropic", "google", "mistral", "ollama"]

_VALID_PROVIDERS: tuple[ProviderSlug, ...] = (
    "openai",
    "anthropic",
    "google",
    "mistral",
    "ollama",
)


class LayerConfig(BaseModel):
    """Single layer: a named architectural layer mapped to directory paths."""

    name: str = Field(..., description="Layer name (e.g. domain, infrastructure).")
    paths: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Directory paths relative to the project package root "
            "(e.g. ['core'] or ['src/core'])."
        ),
    )

    model_config = {"frozen": True}


class StructIaConfig(BaseModel):
    """Root configuration schema for struct-ia.

    ``layers`` is an ordered list from lowest to highest architectural layer.
    The index of each entry defines its dependency level.

    ``provider`` selects the active LLM adapter. Accepted values:
    "openai" | "anthropic" | "google" | "mistral" | "ollama".
    When omitted, the factory falls back to auto-detection via environment
    variables (OPENAI_API_KEY → openai, etc.).
    """

    project_package: str = Field(
        ..., description="Python package name of the project being analyzed."
    )
    layers: list[LayerConfig] = Field(
        ...,
        min_length=1,
        description="Ordered list of architectural layers (lowest → highest).",
    )
    provider: ProviderSlug | None = Field(
        default=None,
        description=(
            "LLM provider slug. One of: openai, anthropic, google, mistral, ollama. "
            "Defaults to auto-detection from environment variables."
        ),
    )

    model_config = {"frozen": True}


DEFAULT_CONFIG = StructIaConfig(
    project_package="struct_ai",
    layers=[
        LayerConfig(name="domain", paths=["core"]),
        LayerConfig(name="infrastructure", paths=["adapters"]),
        LayerConfig(name="entrypoints", paths=["entrypoints"]),
    ],
)
