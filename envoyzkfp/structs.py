from __future__ import annotations
from collections import defaultdict

from typing import NamedTuple, Optional

import envoyproto.envoy.config.core.v3 as core
from envoyproto.envoy.config.core.v3.proxy_protocol_pb2 import ProxyProtocolConfig


class SNIProxyListener(NamedTuple):
    protocol: str
    port: int
    address: str


class SNIProxyVirtualHost(NamedTuple):
    host: str
    patterns: list[str]
    http_port: int = 80
    https_port: int = 443
    proxy_protocol: Optional['core.proxy_protocol.ProxyProtocolConfig.Version'] = core.proxy_protocol.ProxyProtocolConfig.V1

proxy_protocol_str_to_enum = {
    'v1': ProxyProtocolConfig.V1,
    'v2': ProxyProtocolConfig.V2,
}
