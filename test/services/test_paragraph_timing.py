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


def test_paragraph_durations_cue_aligned_all_cjk_falls_back_proportional():
    # CJK é removido por _normalize; o alinhamento por cume colapsaria todos
    # os limites em 0. Deve degradar para distribuição proporcional ao tamanho.
    script = "你好世界\n\n人工智能很好"
    cues = [(0.0, 2.0, "你好世界"), (2.0, 5.0, "人工智能"), (5.0, 8.0, "很好")]
    spans = paragraph_durations(script, cues, audio_duration=8.0)
    assert len(spans) == 2
    assert spans[0][0] == 0.0
    assert abs(spans[0][1] - 3.2) < 1e-6
    assert abs(spans[1][1] - 8.0) < 1e-6


def test_paragraph_durations_cjk_no_zero_length_spans():
    script = "你好\n\n世界很大"
    spans = paragraph_durations(
        script, [(0.0, 1.0, "你好"), (1.0, 2.0, "世界很大")], audio_duration=2.0
    )
    assert all(end > start for start, end in spans)


def test_paragraph_durations_fallback_mixed_latin_cjk_sizes():
    # Mesmo sem legendas, um parágrafo CJK não pode ganhar peso zero
    # (antigamente share==0 -> duração zero).
    script = "你好世界\n\nalpha"
    spans = paragraph_durations(script, [], audio_duration=6.0)
    assert spans[0][1] - spans[0][0] > 1.0
    assert spans[1][1] - spans[1][0] > 0.0