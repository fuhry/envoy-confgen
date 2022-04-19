from os import access
import sys
import re

from typing import Collection

import envoyproto.envoy.config.listener.v3 as listener
import envoyproto.envoy.config.core.v3 as core
import envoyproto.envoy.config.route.v3 as route
from envoyproto.envoy.extensions.filters.network.http_connection_manager.v3 import http_connection_manager as hcm
from envoyproto.envoy.extensions.filters.http.router.v3 import router
from envoyproto.envoy.extensions.filters.network.tcp_proxy.v3 import tcp_proxy
from envoyproto.envoy.extensions.filters.listener.tls_inspector.v3 import tls_inspector

from .helpers import http_cluster_name, https_cluster_name, typed_config, file_access_log
from .structs import SNIProxyVirtualHost

def tls_inspector_listener_filter() -> listener.listener_components.ListenerFilter:
    return listener.listener_components.ListenerFilter(
        name="envoy.filters.listener.tls_inspector",
        typed_config=typed_config(
            tls_inspector.TlsInspector()
        )
    )


def http_connection_manager_filter(
    route_config: route.route.RouteConfiguration
) -> listener.listener_components.Filter:
    return listener.listener_components.Filter(
        name="envoy.filters.network.http_connection_manager",
        typed_config=typed_config(
            hcm.HttpConnectionManager(
                stat_prefix="ingress_http",
                access_log=[
                    file_access_log(),
                ],
                http_filters=[
                    hcm.HttpFilter(
                        name="envoy.filters.http.router",
                        typed_config=typed_config(router.Router())
                    ),
                ],
                route_config=route_config
            ),
        )
    )


def tcp_proxy_listener_filter(vhost: SNIProxyVirtualHost) -> listener.listener_components.Filter:
    return listener.listener_components.Filter(
        name="envoy.filters.network.tcp_proxy",
        typed_config=typed_config(
            tcp_proxy.TcpProxy(
                stat_prefix='ingress_https',
                access_log=[
                    file_access_log(),
                ],
                cluster=https_cluster_name(vhost),
            ),
        ),
    )


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
                        tcp_proxy_listener_filter(vhost),
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
