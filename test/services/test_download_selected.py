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