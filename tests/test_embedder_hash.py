from asi.memory.embedder import HashEmbedder


def test_hash_embedder_is_deterministic_with_expected_dim() -> None:
    embedder = HashEmbedder(dim=16)
    a = embedder.embed("hello world")
    b = embedder.embed("hello world")
    c = embedder.embed("different text")

    assert len(a) == 16
    assert a == b
    assert a != c
