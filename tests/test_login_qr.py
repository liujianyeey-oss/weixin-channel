import logging

import pytest

from weixin_channel.login_qr import WeixinQRLogin, _qr_status_debug_fields


def test_rejects_non_https_qr_url() -> None:
    with pytest.raises(ValueError, match="Only HTTPS"):
        WeixinQRLogin(qr_base_url="http://ilinkai.weixin.qq.com")


def test_rejects_unauthorized_host() -> None:
    with pytest.raises(ValueError, match="Unauthorized host"):
        WeixinQRLogin(qr_base_url="https://example.com")


def test_qr_debug_fields_redact_credentials() -> None:
    fields = _qr_status_debug_fields(
        {
            "status": "confirmed",
            "bot_token": "SECRET_BOT_TOKEN",
            "ilink_bot_id": "bot@example.com",
            "baseurl": "https://ilinkai.weixin.qq.com",
            "ilink_user_id": "user",
        }
    )

    rendered = repr(fields)
    assert "SECRET_BOT_TOKEN" not in rendered
    assert "bot@example.com" not in rendered
    assert fields["status"] == "confirmed"


async def test_qr_fetch_and_status_calls_do_not_log_credentials(
    monkeypatch, caplog
) -> None:
    caplog.set_level(logging.DEBUG, logger="weixin_channel.login_qr")
    login = WeixinQRLogin()

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None, headers=None):
            if url.endswith("get_bot_qrcode"):
                response = FakeResponse()
                response.payload = {
                    "qrcode": "SECRET_QR_TOKEN",
                    "qrcode_img_content": "SECRET_QR_CONTENT",
                }
                return response
            response = FakeResponse()
            response.payload = {
                "status": "confirmed",
                "bot_token": "SECRET_BOT_TOKEN",
                "ilink_bot_id": "SECRET_BOT_ID",
                "baseurl": "https://ilinkai.weixin.qq.com",
                "ilink_user_id": "SECRET_USER_ID",
            }
            return response

    monkeypatch.setattr("weixin_channel.login_qr.httpx.AsyncClient", FakeClient)
    await login.fetch_qr_code()
    result = await login.wait_for_login("SECRET_QR_TOKEN", timeout_s=0.1)

    assert result.connected is True
    assert "SECRET_QR_TOKEN" not in caplog.text
    assert "SECRET_QR_CONTENT" not in caplog.text
    assert "SECRET_BOT_TOKEN" not in caplog.text
    assert "SECRET_BOT_ID" not in caplog.text
    assert "SECRET_USER_ID" not in caplog.text
