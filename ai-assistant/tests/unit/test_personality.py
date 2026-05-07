"""
Testit: core/personality/ ja core/llm/prompt_builder.py
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from core.llm.prompt_builder import PersonalityConfig, PromptBuilder
from core.personality.loader import PersonalityLoader


class TestPromptBuilder:
    def _make_builder(self, prompt: str = "Olet Kaisa.") -> PromptBuilder:
        return PromptBuilder(PersonalityConfig(name="Kaisa", system_prompt=prompt))

    def test_build_returns_system_prompt(self):
        builder = self._make_builder("Olet Kaisa.")
        result = builder.build()
        assert "Olet Kaisa." in result

    def test_register_module_prompt(self):
        builder = self._make_builder("Base prompt.")
        builder.register_module_prompt("calendar", "Hallitset kalenterin.")
        result = builder.build()
        assert "Hallitset kalenterin." in result
        assert "calendar" in result

    def test_unregister_module_prompt(self):
        builder = self._make_builder("Base.")
        builder.register_module_prompt("calendar", "Kalenteri-ohje.")
        builder.unregister_module_prompt("calendar")
        result = builder.build()
        assert "Kalenteri-ohje." not in result

    def test_multiple_module_prompts(self):
        builder = self._make_builder("Base.")
        builder.register_module_prompt("calendar", "Kalenteri.")
        builder.register_module_prompt("tasks", "Tehtävät.")
        result = builder.build()
        assert "Kalenteri." in result
        assert "Tehtävät." in result

    def test_empty_module_prompt_ignored(self):
        builder = self._make_builder("Base.")
        builder.register_module_prompt("empty", "   ")
        result = builder.build()
        assert "empty" not in result

    def test_unregister_nonexistent_is_noop(self):
        builder = self._make_builder("Base.")
        builder.unregister_module_prompt("ei_ole")  # ei poikkeusta


class TestPersonalityLoader:
    def _write_yaml(self, data: dict, path: Path) -> None:
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

    def test_load_valid_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "personality.yaml"
            self._write_yaml({
                "name": "Testi",
                "system_prompt": "Olet testityttö.",
                "traits": ["suora", "hauska"],
            }, config_path)

            loader = PersonalityLoader(config_path)
            builder = loader.load()
            result = builder.build()
            assert "Olet testityttö." in result

    def test_load_missing_file_returns_default(self):
        loader = PersonalityLoader("/ei/ole/tiedostoa.yaml")
        builder = loader.load()
        # Ei kaadu, palauttaa tyhjän buildin
        result = builder.build()
        assert isinstance(result, str)

    def test_load_empty_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "empty.yaml"
            config_path.write_text("")
            loader = PersonalityLoader(config_path)
            builder = loader.load()
            assert isinstance(builder.build(), str)

    def test_personality_name_loaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "p.yaml"
            self._write_yaml({"name": "Kaisa", "system_prompt": "Prompt."}, config_path)
            loader = PersonalityLoader(config_path)
            builder = loader.load()
            assert builder.personality.name == "Kaisa"
