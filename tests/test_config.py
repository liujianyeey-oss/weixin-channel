from weixin_channel.channel import WeixinConfig


def test_parse_flat_config() -> None:
    config = WeixinConfig.from_dict(
        {
            "token": "secret",
            "account_id": "acct",
            "base_url": "https://example.com",
        }
    )
    assert len(config.accounts) == 1
    assert config.accounts[0].token == "secret"
    assert config.accounts[0].account_id == "acct"
    assert config.accounts[0].base_url == "https://example.com"


def test_parse_accounts_config() -> None:
    config = WeixinConfig.from_dict(
        {
            "accounts": [
                {"account_id": "a", "token": "one"},
                {"account_id": "b", "token": "two"},
                {"account_id": "empty", "token": ""},
            ]
        }
    )
    assert [account.account_id for account in config.accounts] == ["a", "b"]
