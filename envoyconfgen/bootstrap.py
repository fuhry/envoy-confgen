from __future__ import annotations
from typing import Collection

from .config import singleton

config = singleton.get_config()

import envoyproto.envoy.config.core.v3 as core
from envoyproto.envoy.config.bootstrap.v3 import bootstrap

import envoyproto.envoy.config.cluster.v3 as cluster
import envoyproto.envoy.config.listener.v3 as listener


def generate_bootstrap(
    listeners: Collection[listener.listener.Listener], clusters: Collection[cluster.cluster.Cluster]
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
                    port_value=int(config["envoy"]["admin_port"]),
                ),
            ),
        ),
        static_resources=bootstrap.Bootstrap.StaticResources(
            listeners=listeners, clusters=clusters
        ),
    )
