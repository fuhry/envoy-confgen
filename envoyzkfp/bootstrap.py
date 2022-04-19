from __future__ import annotations
from typing import Collection

from .config import singleton
from .structs import SNIProxyListener, SNIProxyVirtualHost

config = singleton.get_config()

import envoyproto.envoy.config.core.v3 as core
from envoyproto.envoy.config.bootstrap.v3 import bootstrap

from .cluster import sni_reverse_proxy_http_cluster, sni_reverse_proxy_https_cluster
from .listener import sni_reverse_proxy_listener

def generate_bootstrap(
    listeners: Collection[SNIProxyListener],
    vhosts: Collection[SNIProxyVirtualHost]
) -> bootstrap.Bootstrap:
    """
    Given lists of listeners and virtual hosts, generates a complete envoy toplevel config
    for a zero-knowledge edge proxy.
    """
    return bootstrap.Bootstrap(
        admin=bootstrap.Admin(
            access_log=[],
            address=core.address.Address(
                socket_address=core.address.SocketAddress(
                    address="127.0.0.1",
                    port_value=int(config['envoy']['admin_port']),
                ),
            ),
        ),
        static_resources=bootstrap.Bootstrap.StaticResources(
            listeners=[
                sni_reverse_proxy_listener(l.protocol, l.address, l.port, vhosts)
                for l in listeners
            ],
            clusters=[
                sni_reverse_proxy_http_cluster(vhost)
                for vhost in vhosts
            ] + [
                sni_reverse_proxy_https_cluster(vhost)
                for vhost in vhosts
            ]
        ),
    )
