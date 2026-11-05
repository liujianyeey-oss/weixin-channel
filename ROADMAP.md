# Implementation roadmap

This file tracks incremental execution of
[docs/MIGRATION_PLAN.md](docs/MIGRATION_PLAN.md).

## Subtasks

### Phase 0 — Baseline

- [x] Confirm the source distribution and license.
- [x] Add an upstream source map.
- [x] Ensure only `weixin-channel` is modified.
- [x] Remove or archive the earlier minimal prototype.

### Phase 1 — Core runtime

- [x] Import unified message models.
- [x] Import push-routing helpers.
- [x] Import channel constraints.
- [x] Import `MediaBackend`.
- [x] Import shared channel utilities.
- [x] Import group-context management.
- [x] Import `BaseChannel`.
- [x] Compile the complete core.

### Phase 2 — WeChat protocol

- [x] Import wire types.
- [x] Import iLink API client.
- [x] Import encrypted media helpers.
- [x] Import text splitter.
- [x] Import QR login.
- [x] Import full `WeixinChannel`.
- [x] Remove every `octop_gateway` import.

### Phase 3 — Runner

- [x] Implement queue wiring for channel enqueue callbacks.
- [x] Implement one or more workers per channel.
- [x] Preserve session locks and same-session batching.
- [x] Expose push methods and subject registry.
- [x] Support optional `MediaBackend`.
- [x] Expose start/stop and channel status.

### Phase 4 — Offline tests

- [x] Test message models and event merging.
- [x] Test constraints.
- [x] Test media backend and crypto helpers.
- [x] Test config parsing.
- [x] Test inbound parsing.
- [x] Test runner queue and worker behavior.
- [x] Test QR URL SSRF protection.

### Phase 5 — Examples and docs

- [x] Add an echo bot example.
- [x] Update README for the full implementation.
- [x] Document token storage and session expiration.

### Phase 6 — Verification

- [x] Compile all sources.
- [x] Run all offline tests.
- [x] Install in an isolated virtual environment.
- [x] Confirm Octop's git status is unchanged.
- [ ] Run an online WeChat login / send / receive smoke test.
