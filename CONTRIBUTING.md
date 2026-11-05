# 贡献指南

欢迎提交问题复现、边界测试、文档修正和小范围代码改进。

## 开发环境

需要 Python 3.12+。在项目根目录执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]' build
pytest
python -m build
```

不要修改系统 Python。若修改协议实现，请补充不依赖真实微信账号的离线测试，覆盖正常、异常和边界行为。

## 提交改动

1. 使用 Issue 说明问题、预期行为、最小复现和实际结果；安全漏洞请按 `SECURITY.md` 私密报告。
2. 每个 PR 聚焦一个问题，说明修改范围、测试命令和结果。
3. 保持现有模块结构和异步处理方式，不引入未经验证的新依赖。
4. 修改安装、配置或公开 API 时，同步更新 README 和相关文档。
5. 涉及上游同步时，更新 `UPSTREAM.md` 中的版本或映射信息。

## 数据与凭证

不要提交真实 bot token、account ID、context token、二维码登录数据、用户消息、媒体文件、个人路径或内部服务地址。日志和截图必须脱敏。真实微信在线验证不是提交补丁的前置条件；如果执行过，请说明范围，但不要附可识别用户或账号的数据。
