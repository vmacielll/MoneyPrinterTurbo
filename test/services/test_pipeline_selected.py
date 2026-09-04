from unittest.mock import patch

from app.models.schema import MaterialInfo, VideoParams
from app.services import task as tm


def _params(selected):
    return VideoParams(
        video_subject="test",
        video_script="Um paragrafo\n\nOutro paragrafo",
        video_source="pexels",
        selected_materials=selected,
    )


def test_get_video_materials_uses_selected_without_search():
    p = _params([
        MaterialInfo(provider="pexels", url="https://x/1.mp4", duration=3),
        MaterialInfo(provider="pexels", url="https://x/2.mp4", duration=4),
    ])
    with patch.object(tm.material, "download_videos") as dl, \
         patch.object(tm.material, "download_selected_videos", return_value=["/t/1.mp4", "/t/2.mp4"]) as dls:
        result = tm.get_video_materials("task-1", p, ["term"], audio_duration=7.0)
    dls.assert_called_once()
    dl.assert_not_called()
    assert result == ["/t/1.mp4", "/t/2.mp4"]


def test_get_video_materials_without_selection_uses_search():
    p = _params(None)
    with patch.object(tm.material, "download_videos", return_value=["/t/1.mp4"]) as dl, \
         patch.object(tm.material, "download_selected_videos") as dls:
        result = tm.get_video_materials("task-1", p, ["term"], audio_duration=7.0)
    dl.assert_called_once()
    dls.assert_not_called()
    assert result == ["/t/1.mp4"]