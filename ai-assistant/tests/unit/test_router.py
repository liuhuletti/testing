"""
Testit: core/router/router.py
"""

import pytest

from core.router.router import Intent, ModuleHandler, Router, RouterConfig


def make_router(threshold: float = 0.5) -> Router:
    return Router(RouterConfig(confidence_threshold=threshold))


def dummy_handler(text: str, params: dict) -> str:
    return f"moduuli vastasi: {text}"


class TestIntentDetection:
    def test_no_modules_returns_general(self):
        router = make_router()
        intent = router.detect_intent("mikä on sää tänään")
        assert intent.name == "general"
        assert intent.confidence == 0.0

    def test_single_keyword_match(self):
        router = make_router(threshold=0.3)
        router.register(ModuleHandler(
            name="calendar",
            keywords=["kalenteri", "tapaaminen", "varaa"],
            handler=dummy_handler,
        ))
        intent = router.detect_intent("lisää kalenteri merkintä")
        assert intent.name == "calendar"
        assert intent.confidence > 0.0

    def test_no_keyword_match(self):
        router = make_router()
        router.register(ModuleHandler(
            name="calendar",
            keywords=["kalenteri", "tapaaminen"],
            handler=dummy_handler,
        ))
        intent = router.detect_intent("millainen sää on tänään")
        assert intent.name == "general"

    def test_best_match_wins(self):
        router = make_router(threshold=0.1)
        router.register(ModuleHandler(
            name="calendar",
            keywords=["kalenteri"],
            handler=dummy_handler,
        ))
        router.register(ModuleHandler(
            name="tasks",
            keywords=["tehtävä", "lista", "tehtävät"],
            handler=dummy_handler,
        ))
        intent = router.detect_intent("lisää tehtävä tehtävälista")
        assert intent.name == "tasks"

    def test_confidence_threshold_respected(self):
        router = make_router(threshold=0.9)
        router.register(ModuleHandler(
            name="calendar",
            keywords=["kalenteri", "tapaaminen", "aika", "varaa"],
            handler=dummy_handler,
        ))
        # Vain yksi osuma neljästä = 0.25 < 0.9
        intent = router.detect_intent("kalenteri")
        assert intent.name == "general"


class TestRouting:
    def test_route_calls_handler(self):
        router = make_router(threshold=0.3)
        results = []
        router.register(ModuleHandler(
            name="calendar",
            keywords=["kalenteri"],
            handler=lambda t, p: results.append(t) or "ok",
        ))
        response = router.route("kalenteri")
        assert response == "ok"
        assert results[0] == "kalenteri"

    def test_route_returns_none_for_general(self):
        router = make_router()
        assert router.route("mikä on tänään") is None

    def test_route_handles_handler_exception(self):
        router = make_router(threshold=0.1)
        router.register(ModuleHandler(
            name="broken",
            keywords=["riko"],
            handler=lambda t, p: (_ for _ in ()).throw(RuntimeError("boom")),
        ))
        result = router.route("riko")
        assert result is None  # ei kaadu koko systeemi


class TestRegistration:
    def test_register_and_list(self):
        router = make_router()
        router.register(ModuleHandler("a", [], dummy_handler))
        router.register(ModuleHandler("b", [], dummy_handler))
        assert "a" in router.list_modules()
        assert "b" in router.list_modules()

    def test_unregister(self):
        router = make_router()
        router.register(ModuleHandler("a", [], dummy_handler))
        router.unregister("a")
        assert "a" not in router.list_modules()

    def test_unregister_nonexistent_is_noop(self):
        router = make_router()
        router.unregister("ei_ole")  # ei poikkeusta


class TestScoring:
    def test_exact_word_boundary(self):
        router = make_router()
        # "kalenteri" ei löydy sanasta "kalenterimerkintä" (word boundary)
        score = router._score("kalenterimerkintä", ["kalenteri"])
        assert score == 0.0

    def test_word_in_sentence(self):
        router = make_router()
        score = router._score("lisää kalenteri", ["kalenteri"])
        assert score == 1.0

    def test_empty_keywords(self):
        router = make_router()
        assert router._score("teksti", []) == 0.0
