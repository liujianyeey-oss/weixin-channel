from weixin_channel.models import InboundMessage, MessageEvent, TextContent


def test_inbound_text_property() -> None:
    message = InboundMessage(
        channel_id="channel",
        content=[TextContent(text="hello"), TextContent(text="world")],
    )
    expected = "hello" + chr(10) + "world"
    assert message.text == expected
    assert not message.has_media


def test_message_event_factories() -> None:
    assert MessageEvent.text("hello").content[0].text == "hello"
    assert MessageEvent.delta("x").type.value == "delta"
    assert MessageEvent.completed().type.value == "completed"
