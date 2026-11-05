import asyncio
import os

from weixin_channel import MessageEvent, WeixinChannelRunner, WeixinConfig


async def echo(message):
    yield MessageEvent.text(message.text or "[empty message]")


async def main() -> None:
    token = os.environ["WEIXIN_BOT_TOKEN"]
    account_id = os.environ.get("WEIXIN_ACCOUNT_ID", "weixin")
    base_url = os.environ.get("WEIXIN_BASE_URL", "https://ilinkai.weixin.qq.com")

    config = WeixinConfig.from_dict(
        {
            "accounts": [
                {
                    "account_id": account_id,
                    "token": token,
                    "base_url": base_url,
                }
            ]
        }
    )
    runner = WeixinChannelRunner(processor=echo, config=config)
    await runner.start()
    try:
        print("Weixin echo channel started. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
