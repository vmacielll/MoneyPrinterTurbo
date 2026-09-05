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


def test_get_video_materials_fails_when_partial_download_mismatch():
    """部分下载失败会让 video_paths 少于 selected_materials,必须整体失败,
    否则后续素材前移后 clip_durations 的 1:1 配对会错位。"""
    p = _params([
        MaterialInfo(provider="pexels", url="https://x/1.mp4", duration=3),
        MaterialInfo(provider="pexels", url="https://x/2.mp4", duration=4),
    ])
    with patch.object(
        tm.material, "download_selected_videos", return_value=["/t/1.mp4"]
    ) as dls, patch.object(tm, "_mark_task_failed") as mark_task_failed:
        result = tm.get_video_materials("task-1", p, ["term"], audio_duration=7.0)
    dls.assert_called_once()
    assert result is None
    mark_task_failed.assert_called_once_with(
        "task-1", "materials", "failed to download one or more selected materials"
    )


def test_generate_final_videos_passes_clip_durations_and_forces_sequential():
    """手动选材路径必须把段落时长列表原样传给 combine_videos,并强制顺序拼接
    (即使 video_count>1 且默认 concat_mode 是 random)。"""
    p = VideoParams(
        video_subject="test",
        video_script="Um paragrafo\n\nOutro paragrafo",
        video_source="pexels",
        video_count=2,
        video_concat_mode="random",
        selected_materials=[
            MaterialInfo(provider="pexels", url="https://x/1.mp4", duration=3),
            MaterialInfo(provider="pexels", url="https://x/2.mp4", duration=4),
        ],
    )
    cues = [(0.0, 3.0, "Um paragrafo"), (3.0, 7.0, "Outro paragrafo")]
    spans = [(0.0, 3.0), (3.0, 7.0)]

    with (
        patch.object(
            tm.subtitle, "parse_subtitle_cues", return_value=cues
        ) as parse_cues,
        patch.object(
            tm.paragraph_timing, "paragraph_durations", return_value=spans
        ) as para_durs,
        patch.object(tm.video, "combine_videos") as combine,
        patch.object(tm.video, "generate_video"),
        patch.object(tm.sm.state, "update_task"),
    ):
        tm.generate_final_videos(
            task_id="task-1",
            params=p,
            downloaded_videos=["/t/1.mp4", "/t/2.mp4"],
            audio_file="/t/audio.mp3",
            subtitle_path="/t/subtitle.srt",
            audio_duration=7.0,
        )

    parse_cues.assert_called_once_with("/t/subtitle.srt")
    para_durs.assert_called_once_with(p.video_script, cues, 7.0)
    assert combine.call_count == 2  # video_count=2: cada iteração recebe a mesma lista
    for call in combine.call_args_list:
        assert call.kwargs["clip_durations"] == [3.0, 4.0]
        assert call.kwargs["video_concat_mode"] == tm.VideoConcatMode.sequential