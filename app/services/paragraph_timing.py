import re

from app.utils import utils


def _normalize(text: str) -> str:
    normalized = utils.normalize_script_for_subtitle_matching(text)
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


def paragraph_durations(
    script: str,
    cues: list[tuple[float, float, str]],
    audio_duration: float,
) -> list[tuple[float, float]]:
    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    # Fallback: sem legendas, distribuir proporcionalmente ao tamanho.
    if not cues:
        total_chars = sum(len(_normalize(p)) for p in paragraphs) or 1
        spans = []
        cursor = 0.0
        for p in paragraphs:
            share = len(_normalize(p)) / total_chars * audio_duration
            spans.append((cursor, cursor + share))
            cursor += share
        spans[-1] = (spans[-1][0], audio_duration)
        return spans

    # Alinhamento por cume de caracteres: cada parágrafo corresponde a um
    # intervalo contíguo de falas, na ordem de leitura.
    paragraph_norm = [_normalize(p) for p in paragraphs]
    para_ends = []
    acc = 0
    for pn in paragraph_norm:
        acc += len(pn)
        para_ends.append(acc)

    spans = []
    para_index = 0
    cue_acc = 0
    current_start = cues[0][0]
    for start, end, text in cues:
        cue_acc += len(_normalize(text))
        if para_index < len(paragraph_norm) - 1 and cue_acc >= para_ends[para_index]:
            spans.append((current_start, end))
            para_index += 1
            current_start = end
    # último parágrafo encerra na duração total do áudio
    spans.append((current_start, audio_duration))
    return spans