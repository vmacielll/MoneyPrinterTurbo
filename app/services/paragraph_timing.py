import re

from app.utils import utils


def _normalize(text: str) -> str:
    normalized = utils.normalize_script_for_subtitle_matching(text)
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


def _speech_weight(text: str) -> int:
    normalized_len = len(_normalize(text))
    if normalized_len > 0:
        return normalized_len
    # _normalize remove texto não-latino (ex.: CJK) por completo; usar a
    # contagem bruta de caracteres não-espaço como proxy de fala para que o
    # parágrafo não ganhe peso zero (e consequentemente duração zero).
    return len(re.sub(r"\s+", "", text))


def _proportional_spans(
    paragraphs: list[str], audio_duration: float
) -> list[tuple[float, float]]:
    weights = [_speech_weight(p) for p in paragraphs]
    total = sum(weights) or 1
    spans = []
    cursor = 0.0
    for weight, paragraph in zip(weights, paragraphs):
        share = weight / total * audio_duration
        spans.append((cursor, cursor + share))
        cursor += share
    spans[-1] = (spans[-1][0], audio_duration)
    return spans


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
        return _proportional_spans(paragraphs, audio_duration)

    paragraph_norm = [_normalize(p) for p in paragraphs]
    # Texto não-latino puro (ex.: CJK) zera na normalização; o alinhamento por
    # cume de caracteres fica indefinido (todos os limites em 0), espremendo
    # todos os parágrafos nos primeiros trechos do áudio. Degradar para a
    # distribuição proporcional ao invés de produzir spans degenerados.
    if any(len(pn) == 0 for pn in paragraph_norm):
        return _proportional_spans(paragraphs, audio_duration)
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