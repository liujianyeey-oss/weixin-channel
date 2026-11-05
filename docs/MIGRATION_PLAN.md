# 微信 Channel 完整独立化迁移计划

## 1. 目标与边界

**目标**：在 `weixin-channel` 建立完全独立的 Python 包，保留 Octop Gateway 中微信 iLink 通道的完整运行时能力，不依赖 `octop-gateway`，也不修改 Octop 仓库。

**范围**：

- 保留完整 `WeixinChannel`，不是精简 callback 版；
- 保留统一消息模型、streaming events、constraints、media backend、push routing、subject registry；
- 补齐协议和通道行为测试，不引入 Octop 主工程；
- 明确 fork 维护责任，后续协议变更需自己同步。

**非目标**：

- 不迁移 FastAPI 控制台；
- 不迁移 SQLite 持久化和 Octop 用户/权限系统；
- 不迁移 Agent processor；
- 不迁移其他平台通道；
- 不修改 Octop 源码。

## 2. 现状盘点

源实现来自已安装的 `octop-gateway==1.0.3`，位置：

```text
<octop-gateway-site-packages>/octop_gateway/
```

微信通道文件：

```text
channels/weixin/channel.py     992 行
channels/weixin/login_qr.py    241 行
channels/weixin/api.py         230 行
channels/weixin/media.py       179 行
channels/weixin/types.py       117 行
channels/weixin/text.py         30 行
channels/weixin/__init__.py     26 行
```

完整 `WeixinChannel` 还依赖 gateway 通用核心：

```text
channel.py        1142 行   BaseChannel、ChannelConfig、MessageProcessor
models.py          332 行   ContentPart、InboundMessage、MessageEvent、ChannelSubject
constraints.py     282 行   RateLimiter、ReplyTimeoutGuard、TypingKeepalive
push_routing.py     44 行   context token 常量和 subject alias
media.py            75 行   MediaBackend 接口
utils.py           182 行   Debouncer、事件流关闭、文本/媒体提取、消息合并
group_context.py   315 行   群上下文管理
```

微信协议层 1815 行，通用核心 2372 行，合计约 4187 行。完整独立化是迁移一个最小 gateway runtime，而不是只复制一个微信文件。

`manager.py`（1056 行）负责多平台注册和 worker 池。第一版建议不迁移，用更小的 `WeixinChannelRunner` 替代；以后确实需要多平台或复杂调度时再评估。

## 3. 目标包结构

```text
weixin-channel/
├── pyproject.toml
├── README.md
├── LICENSE
├── UPSTREAM.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── MIGRATION_PLAN.md
├── examples/
│   └── echo.py
├── src/
│   └── weixin_channel/
│       ├── __init__.py
│       ├── api.py
│       ├── channel.py
│       ├── constraints.py
│       ├── core.py
│       ├── group_context.py
│       ├── login_qr.py
│       ├── media.py
│       ├── media_backend.py
│       ├── models.py
│       ├── push_routing.py
│       ├── runner.py
│       ├── text.py
│       ├── types.py
│       └── utils.py
└── tests/
    ├── test_api.py
    ├── test_channel.py
    ├── test_config.py
    ├── test_constraints.py
    ├── test_media.py
    ├── test_models.py
    └── test_runner.py
```

## 4. 迁移阶段

### Phase 0 — 冻结基线

1. 记录源版本、源仓库和 MIT License；
2. 归档当前精简原型，避免丢掉文档；
3. 创建独立 venv，避免和当前环境中已有的 `weixin_channel` 包冲突；
4. 确认 Octop 仓库不被修改。

**验收**：

- `Octop` 的 `git status` 保持干净；
- 独立项目有唯一顶层 `src/weixin_channel`。

### Phase 1 — 迁移通用核心

按依赖顺序迁移：

1. `models.py`
2. `push_routing.py`
3. `constraints.py`
4. `media.py` → `media_backend.py`
5. `utils.py`
6. `group_context.py`
7. `channel.py` → `core.py`

要求：

- 只改 import 路径；
- 保留原行为和公共 API；
- 不做风格化重写；
- 保留 MIT License。

**验收**：

- `python -m compileall` 通过；
- 核心模型和 constraints 单测通过；
- `BaseChannel` 生命周期、队列、debounce、媒体读取行为保持一致。

### Phase 2 — 迁移微信协议层

按依赖顺序迁移：

1. `types.py`
2. `api.py`
3. `media.py`
4. `text.py`
5. `login_qr.py`
6. `channel.py`
7. `__init__.py`

要求：

- 将 `octop_gateway.channels.weixin.*` 改为 `weixin_channel.*`；
- 保留完整 `WeixinChannel`；
- 保留 typing、占位消息、media、context token、stream 事件处理；
- 保留 session expired 暂停策略。

**验收**：

- 代码中无 `octop_gateway` import；
- `WeixinChannel` 可导入、可实例化；
- 配置解析兼容 Octop 保存的 `config_json`；
- 离线 API fixture 测试通过。

### Phase 3 — 迁移运行入口

新增 `WeixinChannelRunner`，职责：

- 启动/停止一个或多个 `WeixinChannel`
- 串接 `MessageProcessor`
- 暴露 push API
- 可选注入 `MediaBackend`
- 暴露运行状态和 session expired 状态

第一版不做多平台 manager，只服务微信通道和多账号场景。

**验收**：

- echo 示例可运行；
- Ctrl+C 或任务取消后通道正常停止；
- session expired 后状态可观测。

### Phase 4 — 测试迁移

离线测试：

- 配置兼容 `accounts[]` 和旧平铺字段；
- inbound parsing（text/image/file/video/voice）；
- context token 更新；
- media 加解密和上传下载 URL 构造；
- 文本切分；
- typing 事件；
- stream 事件合并；
- session expired 暂停；
- push routing；
- `MediaBackend` 读写。

在线 smoke（可选，不进 CI）：

- 扫码登录；
- 发送一条文本；
- 接收一条文本；
- 上传下载一个媒体文件。

**验收**：

- 单测不依赖真实微信账号；
- 全量离线测试通过；
- 在线 smoke 单独标记。

### Phase 5 — 文档与示例

更新：

- `README.md`：安装、扫码、运行、停止、错误处理；
- `docs/ARCHITECTURE.md`：完整链路和模块关系；
- `UPSTREAM.md`：源版本、源文件映射、同步策略；
- `examples/echo.py`；
- 可选 `examples/media.py`。

**验收**：新用户不读 Octop 源码也能运行。

### Phase 6 — 集成审计

检查：

- 是否仍 import `octop_gateway` 或 Octop 主工程；
- 是否复制了不必要的平台代码；
- 是否泄漏 token 到日志；
- rate limit、typing、context token 行为是否完整；
- MIT License 和源版本是否记录。

**验收**：

```bash
rg "octop_gateway|from octop" weixin-channel
```

无结果。

## 5. 行为兼容要求

必须保留：

- `WeixinConfig.from_dict()` 兼容 `accounts[]` 和旧平铺配置；
- `WeixinChannel.start()/stop()` 生命周期；
- `MessageProcessor = Callable[[InboundMessage], AsyncIterator[MessageEvent]]`
- 文本、图片、文件、视频、语音的入站解析；
- `MediaBackend` 可插拔；
- `push_text/push_content/push_to_all`
- subject registry；
- context token 刷新和 listener；
- typing indicator；
- text splitting；
- encrypted media；
- session expired pause。

## 6. 风险与决策

### 维护风险

完全 fork 后无法自动继承 `octop-gateway` 更新。需要维护 `UPSTREAM.md`，记录源版本和同步策略。

### 协议风险

iLink API 没有公开稳定性承诺，认证头、字段名或媒体流程可能变化。API fixture 能帮助快速定位破坏性变更。

### 安全风险

- `bot_token` 是长期敏感凭证；
- context token 是会话路由状态；
- 媒体可能包含敏感内容；
- 日志不得输出完整 token。

### 命名冲突

当前环境中已有其他 `weixin_channel` 包，验证必须使用独立 venv。

## 7. 建议执行顺序

1. 归档精简原型；
2. 重建唯一顶层包结构；
3. 迁移通用核心；
4. 迁移微信实现；
5. 写 runner 和示例；
6. 补测试；
7. 建独立 venv 安装并验证；
8. 清理精简版残留。

## 8. 验收清单

- [x] Octop 仓库 `git status` 干净
- [x] 包内无 `octop_gateway` / Octop 主工程 import
- [x] 完整 `WeixinChannel` 可导入、可实例化
- [x] 支持 `MessageEvent` streaming processor
- [x] 支持 `MediaBackend`
- [x] 支持 context token listener
- [x] 支持 push API
- [x] 支持多账号
- [x] 离线单测全部通过
- [x] 独立 venv 可安装
- [x] echo 示例代码路径可运行（未做真实微信 smoke test）
- [x] 文档完整

在线验收（待完成，不阻塞离线迁移）：

- [ ] 扫码登录成功
- [ ] 接收一条文本
- [ ] 发送一条文本
- [ ] 上传并下载一个媒体文件
