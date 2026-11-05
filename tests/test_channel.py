from weixin_channel.channel import WeixinChannel, WeixinConfig
from weixin_channel.models import ImageContent


async def echo(message):
    yield {"type": "message", "content": [{"type": "text", "text": message.text}]}


def test_channel_parse_inbound_text() -> None:
    channel = WeixinChannel(
        echo,
        config=WeixinConfig.from_dict(
            {"accounts": [{"account_id": "a", "token": "secret"}]}
        ),
    )
    message = channel.parse_inbound(
        {
            "_account_id": "a",
            "from_user_id": "user",
            "item_list": [
                {
                    "type": 1,
                    "text_item": {"text": "hello"},
                }
            ],
        }
    )
    assert message.text == "hello"
    assert message.channel_subject is not None
    assert message.channel_subject.subject_id == "user"
    assert message.metadata["account_id"] == "a"


def test_channel_session_status_reports_running_account() -> None:
    channel = WeixinChannel(
        echo,
        config=WeixinConfig.from_dict(
            {"accounts": [{"account_id": "a", "token": "secret"}]}
        ),
    )
    assert channel.session_status() == {
        "a": {"running": False, "paused": False, "resume_at": None}
    }


def test_channel_session_status_reports_paused_account() -> None:
    import time

    channel = WeixinChannel(
        echo,
        config=WeixinConfig.from_dict(
            {"accounts": [{"account_id": "a", "token": "secret"}]}
        ),
    )
    channel._session_pause_until["a"] = time.monotonic() + 300
    status = channel.session_status()["a"]
    assert status["running"] is False
    assert status["paused"] is True
    assert status["resume_at"] is not None


async def test_channel_media_refreshes_context_token_listener(monkeypatch) -> None:
    channel = WeixinChannel(
        echo,
        config=WeixinConfig.from_dict(
            {"accounts": [{"account_id": "a", "token": "secret"}]}
        ),
    )
    recorded: list[tuple[str, str, str]] = []
    channel.set_context_token_listener(
        lambda account_id, user_id, token, token_ms: recorded.append(
            (account_id, user_id, token)
        )
    )

    class FakeAPI:
        async def send_items(self, to_user_id, items, context_token=""):
            class Response:
                context_token = "refreshed-token"
                data = {}

            return Response()

    class FakeMedia(ImageContent):
        pass

    async def fake_api(account, timeout_s=None):
        return FakeAPI()

    async def fake_upload(**kwargs):
        return {"image_item": {}}

    async def fake_load(media):
        return b"image-bytes", "image/png"

    monkeypatch.setattr(channel, "_api", fake_api)
    monkeypatch.setattr(channel, "_upload_media_part", fake_upload)
    monkeypatch.setattr(channel, "load_media_bytes", fake_load)

    subject = channel.parse_inbound(
        {
            "_account_id": "a",
            "from_user_id": "user",
            "context_token": "old-token",
            "item_list": [{"type": 1, "text_item": {"text": "hello"}}],
        }
    ).channel_subject
    assert subject is not None
    sent = await channel._deliver_media(subject, FakeMedia())
    assert sent is True
    assert recorded == [("a", "user", "refreshed-token")]
