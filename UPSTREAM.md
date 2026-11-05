# Upstream source

This package was forked from TencentCloud's MIT-licensed
`octop-gateway` project.

## Source version

- Distribution: `octop-gateway==1.0.3`
- Repository: https://github.com/TencentCloud/octop-gateway
- Local source snapshot:
  `<octop-gateway-site-packages>/octop_gateway`

## Source mapping

```text
octop_gateway/models.py                 -> src/weixin_channel/models.py
octop_gateway/push_routing.py           -> src/weixin_channel/push_routing.py
octop_gateway/constraints.py            -> src/weixin_channel/constraints.py
octop_gateway/media.py                  -> src/weixin_channel/media_backend.py
octop_gateway/utils.py                  -> src/weixin_channel/utils.py
octop_gateway/group_context.py          -> src/weixin_channel/group_context.py
octop_gateway/channel.py                -> src/weixin_channel/core.py
octop_gateway/channels/weixin/types.py  -> src/weixin_channel/types.py
octop_gateway/channels/weixin/api.py    -> src/weixin_channel/api.py
octop_gateway/channels/weixin/media.py  -> src/weixin_channel/media.py
octop_gateway/channels/weixin/text.py   -> src/weixin_channel/text.py
octop_gateway/channels/weixin/login_qr.py -> src/weixin_channel/login_qr.py
octop_gateway/channels/weixin/channel.py -> src/weixin_channel/channel.py
```

`src/weixin_channel/runner.py` is a small independent runner inspired by the
queue/worker portion of `octop_gateway.manager`. The full multi-platform
`ChannelManager` is intentionally not forked.

## Sync policy

1. Compare changes against the same files in the upstream repository.
2. Apply protocol fixes first (`types.py`, `api.py`, `media.py`,
   `login_qr.py`, and `channel.py`).
3. Re-run the offline test suite.
4. Update this file whenever the source version changes.
