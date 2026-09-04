from app.models.schema import MaterialInfo, VideoParams


def test_video_params_accepts_selected_materials():
    p = VideoParams(
        video_subject="test",
        selected_materials=[
            MaterialInfo(provider="pexels", url="https://example.com/a.mp4", duration=5),
            MaterialInfo(provider="pexels", url="https://example.com/b.mp4", duration=6),
        ],
    )
    assert len(p.selected_materials) == 2
    assert p.selected_materials[0].url == "https://example.com/a.mp4"


def test_selected_materials_defaults_to_none():
    p = VideoParams(video_subject="test")
    assert p.selected_materials is None