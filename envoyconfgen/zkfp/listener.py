from os import access
import sys
import re

from typing import Collection

import envoyproto.envoy.config.listener.v3 as listener
import envoyproto.envoy.config.core.v3 as core
import envoyproto.envoy.config.route.v3 as route

from envoyconfgen.filters import (
    tls_inspector_listener_filter,
    http_connection_manager_filter,
    tcp_proxy_listener_filter,
)
from envoyconfgen.helpers import typed_config, file_access_log
from envoyconfgen.structs import SNIProxyVirtualHost

from .helpers import http_cluster_name, https_cluster_name



def http_virtual_host(vhost: SNIProxyVirtualHost) -> route.route_components.VirtualHost:
    return route.route_components.VirtualHost(
        name='%s_service_%s_%d' % ((vhost.host), 'http', vhost.http_port),
        domains=vhost.patterns + [
            f'{pattern}:{vhost.http_port}'
            for pattern in vhost.patterns
        ],
        routes=[
            route.route_components.Route(
                match=route.route_components.RouteMatch(prefix='/'),
                route=route.route_components.RouteAction(
                    cluster=http_cluster_name(vhost),
                ),
            ),
        ],
    )


def sni_proxy_http_routes(vhosts: Collection[SNIProxyVirtualHost]) -> route.route.RouteConfiguration:
    rc = route.route.RouteConfiguration(
        name='local_route',
        virtual_hosts=[
            http_virtual_host(vhost)
            for vhost in vhosts
        ]
    )
    
    return rc


def sni_reverse_proxy_listener(
    protocol: str,
    address: str = '::',
    port: int = 443,
    virtual_hosts: Collection[SNIProxyVirtualHost] = [],
) -> listener.listener.Listener:
    filter_chains = []
    listener_filters = []
    if protocol == 'http':
        # http listeners get to do this the easy way using real virtual hosts
        filter_chains.append(
            listener.listener_components.FilterChain(
                filters=[
                    http_connection_manager_filter(
                        route_config=sni_proxy_http_routes(virtual_hosts)
                    ),
                ],
            )
        )
    elif protocol == 'https':
        # https listeners have to match much earlier in the negotiation process - the
        # `server_name` field gets populated by the `tls_inspector` listener filter and
        # is used here for matching.
        # we use one filter chain per backend, with matching happening on simple wildcard
        # patterns not unlike the `domains` property on virtual hosts
        # order matters for these, as the first pattern matched is the chosen backend
        for vhost in virtual_hosts:
            filter_chains.append(
                listener.listener_components.FilterChain(
                    filter_chain_match=listener.listener_components.FilterChainMatch(
                        server_names=[
                            pattern
                            for pattern in vhost.patterns
                        ],
                    ),
                    filters=[
                        tcp_proxy_listener_filter(https_cluster_name(vhost)),
                    ],
                )
            )
        listener_filters.append(tls_inspector_listener_filter())

    return listener.listener.Listener(
        name=f"{protocol}_{port}",
        address=core.address.Address(
            socket_address=core.address.SocketAddress(
                address=address,
                port_value=port,
                ipv4_compat=True,
            ),
        ),
        listener_filters=listener_filters,
        filter_chains=filter_chains,
    )
