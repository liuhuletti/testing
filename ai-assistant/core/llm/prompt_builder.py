"""
Rakentaa system-promptin persoonallisuudesta ja aktiivisista moduuleista.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersonalityConfig:
    name: str = "Kaisa"
    system_prompt: str = ""
    traits: list[str] | None = None


class PromptBuilder:
    """
    Yhdistää persoonallisuuden ja moduulien ohjeet yhtenäiseksi system-promptiksi.
    """

    def __init__(self, personality: PersonalityConfig) -> None:
        self.personality = personality
        self._module_prompts: dict[str, str] = {}

    def register_module_prompt(self, module_name: str, prompt: str) -> None:
        """Moduulit voivat rekisteröidä oman ohjeensa system-promptiin."""
        self._module_prompts[module_name] = prompt

    def unregister_module_prompt(self, module_name: str) -> None:
        self._module_prompts.pop(module_name, None)

    def build(self) -> str:
        parts = [self.personality.system_prompt]
        for name, prompt in self._module_prompts.items():
            if prompt.strip():
                parts.append(f"\n## {name}\n{prompt.strip()}")
        return "\n".join(p for p in parts if p.strip())
