from unittest.mock import patch

from app.models.schema import MaterialInfo
from app.services import material


def test_download_selected_videos_calls_save_per_material_in_order():
    mats = [
        MaterialInfo(provider="pexels", url="https://x/1.mp4", duration=3),
        MaterialInfo(provider="pexels", url="https://x/2.mp4", duration=4),
    ]
    saved_paths = iter(["/tmp/1.mp4", "/tmp/2.mp4"])
    with patch.object(material, "save_video", side_effect=lambda url, save_dir="": next(saved_paths)) as sv, \
         patch.object(material, "_persist_material_sources"):
        result = material.download_selected_videos("task-1", mats, "/tmp/out")
    assert result == ["/tmp/1.mp4", "/tmp/2.mp4"]
    assert sv.call_count == 2
    # ordem preservada
    assert sv.call_args_list[0][0][0] == "https://x/1.mp4"
    assert sv.call_args_list[1][0][0] == "https://x/2.mp4"


def test_download_selected_videos_skips_failed_save():
    mats = [
        MaterialInfo(provider="pexels", url="https://x/1.mp4", duration=3),
        MaterialInfo(provider="pexels", url="https://x/bad.mp4", duration=4),
    ]
    def fake_save(url, save_dir=""):
        return "" if "bad" in url else "/tmp/1.mp4"
    with patch.object(material, "save_video", side_effect=fake_save), \
         patch.object(material, "_persist_material_sources"):
        result = material.download_selected_videos("task-1", mats, "/tmp/out")
    assert result == ["/tmp/1.mp4"]


def test_download_selected_videos_renders_image_with_clip_duration():
    mats = [MaterialInfo(provider="pexels", url="https://x/a.jpg", material_type="image")]
    with patch.object(material, "_download_image_file", return_value="/tmp/photo.jpg") as dl, \
         patch.object(material.video, "render_image_zoom_video", return_value="/tmp/photo.jpg.mp4") as render, \
         patch.object(material, "_persist_material_sources"):
        result = material.download_selected_videos(
            "task-1", mats, "/tmp/out", clip_durations=[7]
        )
    assert result == ["/tmp/photo.jpg.mp4"]
    dl.assert_called_once_with("https://x/a.jpg", "/tmp/out")
    render.assert_called_once_with("/tmp/photo.jpg", clip_duration=7)


def test_download_selected_videos_skips_image_when_download_fails():
    mats = [MaterialInfo(provider="pexels", url="https://x/a.jpg", material_type="image")]
    with patch.object(material, "_download_image_file", return_value=None), \
         patch.object(material, "save_video") as sv, \
         patch.object(material, "_persist_material_sources"):
        result = material.download_selected_videos("task-1", mats, "/tmp/out")
    assert result == []
    sv.assert_not_called()


def test_download_selected_videos_image_uses_default_duration_without_clip_durations():
    mats = [MaterialInfo(provider="pexels", url="https://x/a.jpg", material_type="image")]
    with patch.object(material, "_download_image_file", return_value="/tmp/photo.jpg"), \
         patch.object(material.video, "render_image_zoom_video", return_value="/tmp/photo.jpg.mp4") as render, \
         patch.object(material, "_persist_material_sources"):
        result = material.download_selected_videos("task-1", mats, "/tmp/out")
    assert result == ["/tmp/photo.jpg.mp4"]
    render.assert_called_once_with("/tmp/photo.jpg", clip_duration=5)