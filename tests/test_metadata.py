import music_downloader.metadata as metadata


def test_embed_metadata_dispatches_to_flac(monkeypatch):
    calls = []
    monkeypatch.setattr(
        metadata, "embed_flac_tags", lambda *args, **kwargs: calls.append(("flac", args, kwargs))
    )
    monkeypatch.setattr(
        metadata, "embed_id3_tags", lambda *args, **kwargs: calls.append(("id3", args, kwargs))
    )

    metadata.embed_metadata("song.flac", {"name": "Song"}, bitrate="flac")

    assert calls[0][0] == "flac"


def test_embed_metadata_dispatches_to_id3(monkeypatch):
    calls = []
    monkeypatch.setattr(
        metadata, "embed_flac_tags", lambda *args, **kwargs: calls.append(("flac", args, kwargs))
    )
    monkeypatch.setattr(
        metadata, "embed_id3_tags", lambda *args, **kwargs: calls.append(("id3", args, kwargs))
    )

    metadata.embed_metadata("song.mp3", {"name": "Song"}, bitrate="320")

    assert calls[0][0] == "id3"
