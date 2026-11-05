"""Standalone WeChat (iLink Bot) channel extracted from Octop Gateway."""

from .channel import WeixinAccountConfig, WeixinChannel, WeixinConfig
from .constraints import ChannelConstraints
from .core import BaseChannel, ChannelConfig, ChannelCredentialsError, MessageProcessor
from .login_qr import QRCodeResponse, WeixinQRLogin, WeixinQrWaitResult
from .media_backend import FileSystemMediaBackend, MediaBackend
from .models import ChannelSubject, ContentPart, InboundMessage, MessageEvent
from .runner import WeixinChannelRunner

__all__ = [
    "BaseChannel",
    "ChannelConfig",
    "ChannelConstraints",
    "ChannelCredentialsError",
    "ChannelSubject",
    "ContentPart",
    "FileSystemMediaBackend",
    "InboundMessage",
    "MediaBackend",
    "MessageEvent",
    "MessageProcessor",
    "QRCodeResponse",
    "WeixinAccountConfig",
    "WeixinChannel",
    "WeixinChannelRunner",
    "WeixinConfig",
    "WeixinQRLogin",
    "WeixinQrWaitResult",
]
