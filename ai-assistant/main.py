"""
AI-assistentin pääsilmukka – MVP.

Virtaus:
  1. [Optionaalinen wake word -vaihe]
  2. Kuunnellaan käyttäjää (VAD)
  3. STT muuttaa puheen tekstiksi
  4. Router tarkistaa onko moduulille tarkoitettu komento
  5. Jos ei → LLM (Claude) vastaa streaming-tilassa
  6. TTS puhuu vastauksen ääneen

Käynnistys:
  python main.py
  python main.py --debug
  python main.py --text   # tekstisyöte mikrofonin sijaan (testaus)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Varmistetaan että projektin juurihakemisto on Python-polussa
sys.path.insert(0, str(Path(__file__).parent))


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )
    # Hiljennetään turhat kirjastologit
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-assistentti")
    parser.add_argument("--debug", action="store_true", help="Debug-loki")
    parser.add_argument(
        "--text", action="store_true",
        help="Tekstisyöte mikrofonin sijaan (testausta varten)"
    )
    parser.add_argument(
        "--no-tts", action="store_true",
        help="Ei TTS-toistoa (tulostaa vain tekstin)"
    )
    return parser.parse_args()


def run(text_mode: bool = False, no_tts: bool = False) -> None:
    from core.config import (
        load_settings,
        build_listener_config,
        build_transcriber_config,
        build_tts_config,
        build_llm_config,
        build_router_config,
    )
    from core.speech.listener import AudioListener
    from core.speech.transcriber import Transcriber
    from core.tts.synthesizer import create_tts
    from core.llm.client import LLMClient
    from core.router.router import Router
    from core.memory.conversation import ConversationMemory
    from core.personality.loader import PersonalityLoader

    logger = logging.getLogger(__name__)

    # ── Asetukset ──────────────────────────────────────────────────────────────
    settings = load_settings()

    # ── Persoonallisuus & system prompt ────────────────────────────────────────
    personality_loader = PersonalityLoader()
    prompt_builder = personality_loader.load()
    system_prompt = prompt_builder.build()

    # ── Komponenttien alustus ─────────────────────────────────────────────────
    logger.info("Alustetaan komponentit…")

    transcriber = Transcriber(build_transcriber_config(settings))
    transcriber.warmup()

    tts = create_tts(build_tts_config(settings))
    llm = LLMClient(build_llm_config(settings), system_prompt=system_prompt)
    router = Router(build_router_config(settings))
    memory = ConversationMemory()

    if not text_mode:
        listener = AudioListener(build_listener_config(settings))

    logger.info("Assistentti valmis. Paina Ctrl+C lopettaaksesi.")

    if not no_tts:
        tts.speak("Moi. Olen Kaisa. Miten voin auttaa?")

    # ── Pääsilmukka ───────────────────────────────────────────────────────────
    while True:
        try:
            # 1. Äänen tai tekstin vastaanotto
            if text_mode:
                user_input = input("\nSinä: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "lopeta"):
                    break
            else:
                print("\n[Kuunnellaan…]")
                audio = listener.listen()
                user_input = transcriber.transcribe(audio)
                if not user_input:
                    logger.debug("Tyhjä tunnistus, kuunnellaan uudelleen")
                    continue
                print(f"Sinä: {user_input}")

            # 2. Lopetuskomento
            if any(word in user_input.lower() for word in ["lopeta", "sammu", "sulje"]):
                tts.speak("Selvä. Suljetaan.")
                break

            # 3. Muistihistoria
            memory.add_user(user_input)
            history = memory.get_history()

            # 4. Reititys moduuleille
            module_response = router.route(user_input)

            if module_response is not None:
                # Moduuli vastasi
                response_text = module_response
                print(f"Kaisa: {response_text}")
                memory.add_assistant(response_text)
                if not no_tts:
                    tts.speak(response_text)
            else:
                # 5. LLM vastaa streaming-tilassa
                print("Kaisa: ", end="", flush=True)
                response_parts: list[str] = []
                tts_buffer = ""
                tts_sentence_endings = {".", "!", "?", "…"}

                for token in llm.stream(user_input, history):
                    print(token, end="", flush=True)
                    response_parts.append(token)
                    tts_buffer += token

                    # TTS aloittaa lauseen valmistuttua – ei odoteta koko vastausta
                    if not no_tts and any(c in tts_buffer for c in tts_sentence_endings):
                        sentences = _split_at_sentence_end(tts_buffer)
                        for sentence in sentences[:-1]:
                            if sentence.strip():
                                tts.speak(sentence.strip())
                        tts_buffer = sentences[-1]

                # Loput puhutaan
                if not no_tts and tts_buffer.strip():
                    tts.speak(tts_buffer.strip())

                print()  # rivinvaihto
                full_response = "".join(response_parts)
                memory.add_assistant(full_response)

        except KeyboardInterrupt:
            print("\n\nKeskeytettiin.")
            break
        except Exception as exc:
            logger.error("Virhe pääsilmukassa: %s", exc, exc_info=True)
            if not no_tts:
                tts.speak("Tapahtui virhe. Kokeillaan uudelleen.")


def _split_at_sentence_end(text: str) -> list[str]:
    """Pilkkoo tekstin lauseisiin TTS-streamingille."""
    import re
    parts = re.split(r"(?<=[.!?…])\s+", text)
    return parts if parts else [text]


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.debug)
    run(text_mode=args.text, no_tts=args.no_tts)
