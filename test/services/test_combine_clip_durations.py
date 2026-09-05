from unittest.mock import patch

from app.models.schema import VideoFitMode
from app.services import video


def test_combine_videos_accepts_clip_durations_param():
    with patch.object(video, "AudioFileClip"), \
         patch.object(video, "subclipped", create=True), \
         patch.object(video, "concat_video_clips_with_ffmpeg") as concat:
        # Exercita apenas a assinatura + passagem, sem render real.
        # AudioFileClip fake devolve duration 4.0.
        fake_audio = video.AudioFileClip.return_value
        fake_audio.duration = 4.0
        fake_audio.close.return_value = None
        video.combine_videos(
            combined_video_path="/tmp/c.mp4",
            video_paths=[],
            audio_file="/tmp/audio.mp3",
            video_aspect="9:16",
            video_concat_mode="sequential",
            clip_durations=[3.0],
            video_fit_mode=VideoFitMode.cover,
        )
    # sem exceção == assinatura aceita clip_durations