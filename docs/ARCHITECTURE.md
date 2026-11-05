# WeChat iLink Channel 实现分析（从 Octop 抽取）

这份文档整理自 Octop 中微信通道的实现分析，作为独立模块的设计参考。

## 结论

Octop 的微信通道是一个两层实现：

- Octop 主进程负责前端配置、API、持久化和 Agent 编排；
- `octop-gateway` 负责微信 iLink Bot 协议适配，包括扫码登录、HTTP 长轮询收消息、API 发消息和媒体加解密。

它不是公众号或企业微信 webhook 机器人，而是「个人微信 iLink Bot」通道：扫码获得 `bot_token`，本地进程用该 token 主动拉取消息，再通过同一个 iLink API 回复。

## 消息链路

```text
控制台「个性化 → 通道 → 微信」（Octop 侧）
  → POST /api/agents/{agentId}/channels/weixin/qrcode/generate
  → iLink get_bot_qrcode 生成二维码
  → 用户微信扫码并确认
  → get_qrcode_status 返回 bot_token / account_id / base_url
  → 前端保存 kind="weixin" channel
  → Octop GatewayManager 注册 WeixinChannel
  → WeixinChannel getupdates 长轮询拉取消息
  → Agent processor 生成回复
  → sendmessage / getuploadurl 回发文本或媒体
```

## 配置和入口

前端文件：

- `dashboard/src/pages/Agent/Channels/components/ChannelDrawer.tsx`
- `dashboard/src/api/modules/channel.ts`
- `dashboard/src/api/types/channel.ts`
- `dashboard/src/pages/Agent/Channels/components/constants.ts`

后端 API：

- `src/octop/api/routers/channels.py`

后端 API 是薄封装，只做权限校验和结果映射，懒加载：

```python
from octop_gateway.channels.weixin.login_qr import WeixinQRLogin  # Octop 侧
```

## 扫码登录

`octop-gateway` 的 `channels/weixin/login_qr.py` 实现两阶段扫码：

1. `fetch_qr_code()`
   - 调用 `GET https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3`
   - 返回 `qrcode`（轮询 token）和 `qrcode_img_content`（二维码 URL 内容）
2. `wait_for_login(qrcode)`
   - 调用 `GET https://ilinkai.weixin.qq.com/ilink/bot/get_qrcode_status?qrcode=...`
   - 状态流转：`wait → scaned → confirmed`
   - 二维码过期自动刷新，最多 3 次

确认成功后得到：

- `bot_token`
- `ilink_bot_id`，规范化后作为 `account_id`
- `baseurl`
- `ilink_user_id`

QR API 有 SSRF 白名单限制，仅允许 `ilinkai.weixin.qq.com`。

## 持久化配置

扫码成功后，前端会保存类似下面的配置：

```json
{
  "kind": "weixin",
  "name": "weixin",
  "config": {
    "accounts": [
      {
        "account_id": "xxx",
        "token": "xxx",
        "base_url": "https://ilinkai.weixin.qq.com",
        "bot_uin": "xxx"
      }
    ],
    "bot_uin": "xxx",
    "token": "xxx",
    "base_url": "https://ilinkai.weixin.qq.com"
  }
}
```

`accounts[]` 是新格式，平铺字段是兼容旧格式。Octop 会把它存入 SQLite `channels.config_json`。当前实现没有加密 `bot_token`，配置文件和数据库访问权限就是安全边界。

## 通道启动

`src/octop/infra/gateway/gateway.py` 在服务启动或通道保存后：

1. 从 `channels` 表读取 `config_json`；
2. 解析成 `WeixinConfig`；
3. 通过 `ChannelManager.add_channel("weixin", config, ...)` 注册；
4. 注入 Agent 的消息 processor；
5. 为 stream 模式包装微信专用事件过滤器；
6. 设置媒体后端；
7. 注册 context token 刷新监听器。

## 收消息：HTTP long-poll

`WeixinChannel.start()` 为每个账号创建独立 asyncio task：

```python
asyncio.create_task(self._poll_loop(account))
```

`_poll_loop()` 调用：

```text
POST /ilink/bot/getupdates
```

关键点：

- `get_updates_buf` 是同步游标，服务端返回新 cursor；
- 默认 long-poll 35 秒；
- 空闲超时是正常状态，继续下一轮；
- `errcode=-14` 表示会话过期，通道暂停 5 分钟，需要重新扫码；
- 其他错误使用指数退避，最多 60 秒。

消息解析支持：

- 文本
- 图片
- 文件
- 视频
- 语音转文本

图片、文件、视频通过加密 CDN 媒体对象携带，需要下载并 AES 解密。

## 认证和发消息

发送文本调用：

```text
POST /ilink/bot/sendmessage
```

认证头：

```text
AuthorizationType: ilink_bot_token
Authorization: Bearer <bot_token>
X-WECHAT-UIN: <base64(random uint32)>
iLink-App-Id: bot
iLink-App-ClientVersion: 131072
```

这套认证头是协议能建立会话的关键。代码注释特别说明：`Authorization: ilink_bot_token <token>` 这种写法会被服务端拒绝，导致 `errcode=-14` 循环出现。

发送媒体调用：

```text
POST /ilink/bot/getuploadurl
POST https://novac2c.cdn.weixin.qq.com/c2c/upload
POST /ilink/bot/sendmessage
```

上传流程：

1. 生成 16 字节 AES key；
2. 计算 MD5 和文件 key；
3. 请求 upload URL；
4. AES-128-ECB 加密文件并上传；
5. 读取响应头 `x-encrypted-param`；
6. 组装 image/file/video item 后发送。

## Context token

iLink 消息里有 `context_token`。通道会：

- 从入站消息保存 `(account_id, user_id) → context_token`；
- 发送成功后如果响应刷新了 token，则更新缓存；
- Octop 主进程通过 listener 把刷新后的 token 持久化到 session 元数据；
- 主动推送时优先使用缓存 token。

这个 token 是会话路由状态的一部分，不是静态配置。

## 体验细节

- 文本超过约 2000 字符会分段；
- 发送速率默认限制为每 60 秒 5 条（分段消息计费）；
- 支持微信 typing 指示；
- 如果 typing 不可用，4 秒后发送一次 `⏳ 思考中...` 占位消息；
- stream 模式会过滤工具调用前的冗余提示文本。

## Octop 中的集成点

- 前端扫码配置：`ChannelDrawer.tsx`
- API 路由：`src/octop/api/routers/channels.py`
- 网关注册：`src/octop/infra/gateway/gateway.py`
- 会话 token 持久化：`src/octop/infra/db/repos/sessions.py`
- 协议实现（Octop 侧）：`octop_gateway/channels/weixin/*`

## 独立抽取边界

独立模块保留完整微信通道和通用 channel 运行时，不复制 Octop 的多平台注册器：

- 扫码登录
- iLink API 客户端
- 收发消息循环
- 文本切分
- 媒体加解密和上传下载
- constraints、typing、占位消息和 stream 事件处理
- 多账号配置
- `BaseChannel`、统一消息模型和 `MediaBackend`

不包含：

- FastAPI 控制台
- SQLite 持久化
- 用户/权限系统
- Agent processor
`WeixinChannelRunner` 负责原来 manager 中和微信相关的 queue、worker、session lock、
同 session 合并和 push API 接线；它不提供其他平台的注册能力。

这样做的取舍：独立模块可以直接嵌入任意 Python 项目，但需要调用方自己管理 token 持久化、账号生命周期和业务 processor。
