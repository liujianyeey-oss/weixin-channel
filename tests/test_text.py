from weixin_channel.text import split_weixin_text


def test_short_text_returns_one_piece() -> None:
    assert split_weixin_text("hello") == ["hello"]


def test_splits_on_newline_boundary() -> None:
    text = "a" * 90 + "\n" + "b" * 90
    assert split_weixin_text(text, limit=100) == ["a" * 90, "b" * 90]


def test_long_text_without_boundary_splits_by_limit() -> None:
    text = "x" * 210
    assert split_weixin_text(text, limit=100) == ["x" * 100, "x" * 100, "x" * 10]
