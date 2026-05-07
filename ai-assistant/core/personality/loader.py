"""
Lataa persoonallisuuden YAML-tiedostosta.

Persoonallisuuden vaihto käy muuttamalla config/personality.yaml –
ei tarvita koodimuutoksia.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from core.llm.prompt_builder import PersonalityConfig, PromptBuilder

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("config/personality.yaml")


class PersonalityLoader:
    """
    Käyttö:
        loader = PersonalityLoader()
        builder = loader.load()
        system_prompt = builder.build()
    """

    def __init__(self, config_path: Path | str = DEFAULT_CONFIG) -> None:
        self.path = Path(config_path)

    def load(self) -> PromptBuilder:
        data = self._read_yaml()
        personality = PersonalityConfig(
            name=data.get("name", "Assistentti"),
            system_prompt=data.get("system_prompt", ""),
            traits=data.get("traits", []),
        )
        builder = PromptBuilder(personality)
        logger.info("Persoonallisuus ladattu: '%s'", personality.name)
        return builder

    def _read_yaml(self) -> dict:
        if not self.path.exists():
            logger.warning("Persoonallisuustiedostoa ei löydy: %s", self.path)
            return {}
        with self.path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
