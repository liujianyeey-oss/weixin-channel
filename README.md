# weixin-channel

从 TencentCloud Octop Gateway 抽取的个人微信 iLink Bot 独立 Python 包，保留统一消息模型、streaming events、constraints、media backend、push routing 和多账号支持。

本项目是非官方独立包，不隶属于或代表 Tencent、TencentCloud 或微信官方。

项目仓库：<https://github.com/liujianyeey-oss/weixin-channel>。

> 当前仅完成离线验证。真实微信扫码登录、收发消息和媒体上传下载尚未做过在线 smoke test，使用前请先在自有测试账号和隔离环境中验证。

## 功能

- 微信扫码登录接口和 iLink Bot API 客户端
- HTTP long-poll 收取消息
- 文本发送和自动分段
- 图片、文件、视频的 AES 加解密与 CDN 上传下载
- 多账号、消息队列、session lock 和 push routing

## 环境要求

- Python 3.12 或更高版本
- 使用真实通道时，需要有效的 iLink Bot token 和账号配置

## 安装

在项目根目录执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

开发安装及测试依赖：

```bash
python -m pip install -e '.[dev]'
```

## Echo 示例

凭证只通过环境变量传入，不要把真实 token 写入源码、文档或 Git 历史。

```bash
export WEIXIN_BOT_TOKEN='your-bot-token'
export WEIXIN_ACCOUNT_ID='your-account-id'
# 可选；默认值如下：
export WEIXIN_BASE_URL='https://ilinkai.weixin.qq.com'
python examples/echo.py
```

| 环境变量 | 是否必需 | 说明 |
|---|---|---|
| `WEIXIN_BOT_TOKEN` | 是 | iLink Bot 凭证 |
| `WEIXIN_ACCOUNT_ID` | 否 | 账号标识，示例默认为 `weixin` |
| `WEIXIN_BASE_URL` | 否 | API 地址，默认为 `https://ilinkai.weixin.qq.com` |

示例使用 `WeixinChannelRunner`，会接通 channel 队列、worker、session lock、media backend 和 push 接口。直接使用 `WeixinChannel` 时，如果需要完整 inbound 处理管线，应显式调用 `set_enqueue_callback`，或使用 runner。

Runner 默认使用 `WeixinConfig.media_dir` 作为 `FileSystemMediaBackend` 根目录，也可以显式传入自己的 `media_backend`。扫码接口由 `WeixinQRLogin` 提供；获得的 `bot_token`、`account_id`、`base_url` 应保存到安全存储中。

## 测试

```bash
pytest
```

测试不需要真实微信账号。贡献补丁前请运行完整离线测试，具体见 [贡献指南](CONTRIBUTING.md)。

## 文档

- [架构与协议说明](docs/ARCHITECTURE.md)
- [独立化迁移记录](docs/MIGRATION_PLAN.md)
- [路线图](ROADMAP.md)
- [上游来源与同步策略](UPSTREAM.md)
- [安全策略](SECURITY.md)

## License

[MIT License](LICENSE)，继承自 TencentCloud Octop Gateway。来源和归属说明见 [NOTICE.md](NOTICE.md)。
