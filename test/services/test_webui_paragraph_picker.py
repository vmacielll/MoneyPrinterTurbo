from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.config import config
from app.services import llm, material, voice

ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"


def _widget_by_key(elements, key):
    # Prefer an exact key match; keys are often prefixes of sibling widget keys
    # (e.g. "video_script" vs "video_script_prompt"), so startswith must be a
    # fallback, not the primary match.
    for item in elements:
        if str(getattr(item, "key", "")) == key:
            return item
    return next(
        item
        for item in elements
        if str(getattr(item, "key", "")).startswith(f"{key}_")
    )


class _FakePexelsOption:
    def __init__(self, duration, url="https://example.invalid/video.mp4"):
        self.duration = duration
        self.url = url
        self.source_info = {"thumbnail": ""}


def _new_app():
    # A cold Python 3.11 environment can spend over 30 seconds importing the
    # full Streamlit entrypoint and optional media stack. Keep the assertion
    # timeout above that one-time startup cost so targeted runs do not flake.
    app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=60)
    app.session_state["ui_language"] = "en"
    app.run()
    assert [str(item.value) for item in app.exception] == []
    return app


def test_paragraph_picker_estimates_durations_and_card_selection_unblocks_generation():
    """A2/A3: a busca por parágrafo exibe a duração estimada por IA e a
    seleção através dos cards clicáveis alimenta o gating de geração."""
    test_app_config = dict(config.app, video_source="pexels")

    with (
        patch.object(config, "app", test_app_config),
        patch.object(config, "ui", dict(config.ui, language="en")),
        patch.object(config, "try_save_config", return_value=True),
        patch.object(
            voice,
            "get_all_azure_voices",
            return_value=["en-US-JennyNeural-Female"],
        ),
        patch.object(llm, "generate_terms", return_value=["term one", "term two"]),
        patch.object(llm, "estimate_paragraph_durations", return_value=[3.2, 4.4]),
        patch.object(
            material,
            "search_videos_pexels",
            return_value=[_FakePexelsOption(5), _FakePexelsOption(7)],
        ),
    ):
        session = _new_app()
        session.session_state["manual_pick_per_paragraph"] = True
        _widget_by_key(session.text_area, "video_subject").set_value("Example subject")
        _widget_by_key(session.text_area, "video_script").set_value(
            "First paragraph.\n\nSecond paragraph."
        )
        session.run()

        # Generation stays blocked until every paragraph has a picked card.
        assert _widget_by_key(session.button, "generate_video_button").disabled

        _widget_by_key(session.button, "search_videos_per_paragraph").click().run()

        selection = session.session_state["per_paragraph_selection"]
        assert len(selection) == 2
        assert [entry["chosen_index"] for entry in selection] == [-1, -1]
        assert selection[0]["estimated_duration"] == 3.2
        assert selection[1]["estimated_duration"] == 4.4

        caption_values = [item.value for item in session.caption]
        assert any("3.2s estimated" in value for value in caption_values)
        assert any("4.4s estimated" in value for value in caption_values)

        # Still blocked: nothing selected yet.
        assert _widget_by_key(session.button, "generate_video_button").disabled

        # Pick a non-first card for paragraph 1 and the first card for paragraph 2.
        _widget_by_key(session.button, "per_paragraph_pick_0_1").click().run()
        _widget_by_key(session.button, "per_paragraph_pick_1_0").click().run()

        selection = session.session_state["per_paragraph_selection"]
        assert [entry["chosen_index"] for entry in selection] == [1, 0]

        # Selected card switches to the "✓ Selected" primary state.
        picked_button = _widget_by_key(session.button, "per_paragraph_pick_0_1")
        assert "✓ Selected" in picked_button.label

        # Complete selection clears the block on the generation button.
        assert not _widget_by_key(session.button, "generate_video_button").disabled