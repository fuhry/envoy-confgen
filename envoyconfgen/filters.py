import envoyproto.envoy.config.core.v3 as core
import envoyproto.envoy.config.listener.v3 as listener
import envoyproto.envoy.config.route.v3 as route

from envoyproto.envoy.extensions.filters.http.router.v3 import router
from envoyproto.envoy.extensions.filters.network.http_connection_manager.v3 import http_connection_manager as hcm
from envoyproto.envoy.extensions.transport_sockets.proxy_protocol.v3 import upstream_proxy_protocol as upp
from envoyproto.envoy.extensions.transport_sockets.raw_buffer.v3 import raw_buffer
from envoyproto.envoy.extensions.filters.network.tcp_proxy.v3 import tcp_proxy
from envoyproto.envoy.extensions.filters.listener.tls_inspector.v3 import tls_inspector

from .helpers import file_access_log, typed_config

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


def tcp_proxy_listener_filter(cluster_name: str) -> listener.listener_components.Filter:
    return listener.listener_components.Filter(
        name="envoy.filters.network.tcp_proxy",
        typed_config=typed_config(
            tcp_proxy.TcpProxy(
                stat_prefix='ingress_https',
                access_log=[
                    file_access_log(),
                ],
                cluster=cluster_name,
            ),
        ),
    )


def proxy_protocol_transport_socket(version: core.proxy_protocol.ProxyProtocolConfig.Version) -> core.base.TransportSocket:
    """
    Factory for proxy protocol transport sockets - supports proxy protocol both v1 and v2
    """
    return core.base.TransportSocket(
        name="envoy.transport_sockets.proxy_protocol",
        typed_config=typed_config(
            upp.ProxyProtocolUpstreamTransport(
                config=core.proxy_protocol.ProxyProtocolConfig(
                    version=version,
                ),
                transport_socket=core.base.TransportSocket(
                    name="envoy.transport_sockets.raw_buffer",
                    typed_config=typed_config(raw_buffer.RawBuffer())
                )
            ),
        )
    )
