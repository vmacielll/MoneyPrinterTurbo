from app.services.paragraph_timing import paragraph_durations


def _norm(s):
    import re
    return re.sub(r"[^a-z0-9]+", "", s.lower()).strip()


def test_paragraph_durations_aligns_by_character_cume():
    script = "Primeiro paragrafo aqui\n\nSegundo paragrafo com mais texto"
    cues = [
        (0.0, 2.0, "Primeiro paragrafo"),
        (2.0, 4.0, "aqui"),
        (4.0, 9.0, "Segundo paragrafo com"),
        (9.0, 11.0, "mais texto"),
    ]
    spans = paragraph_durations(script, cues, audio_duration=11.0)
    assert spans == [(0.0, 4.0), (4.0, 11.0)]


def test_paragraph_durations_fallback_when_no_cues():
    script = "Um paragrafo\n\nOutro paragrafo"
    spans = paragraph_durations(script, [], audio_duration=10.0)
    assert len(spans) == 2
    assert spans[0][0] == 0.0
    assert abs(spans[1][1] - 10.0) < 1e-6
    # proporcional ao tamanho: primeiro parágrafo é menor
    assert spans[0][1] < spans[1][1]


def test_paragraph_durations_empty_script():
    assert paragraph_durations("", [], 5.0) == []