from typing import Callable

import envoyproto.envoy.config.cluster.v3 as cluster
import envoyproto.envoy.config.core.v3 as core
import envoyproto.envoy.config.endpoint.v3 as endpoint
from envoyproto.envoy.extensions.transport_sockets.proxy_protocol.v3 import upstream_proxy_protocol as upp
from envoyproto.envoy.extensions.transport_sockets.raw_buffer.v3 import raw_buffer

import google.protobuf.any_pb2
import google.protobuf.message
import google.protobuf.duration_pb2

from .helpers import http_cluster_name, https_cluster_name, typed_config
from .structs import SNIProxyVirtualHost

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


def sni_proxy_locality_endpoint(host: str, port: int) -> endpoint.endpoint.ClusterLoadAssignment:
    return endpoint.endpoint_components.LocalityLbEndpoints(
        lb_endpoints=[
            endpoint.endpoint_components.LbEndpoint(
                endpoint=endpoint.endpoint_components.Endpoint(
                    address=core.address.Address(
                        socket_address=core.address.SocketAddress(
                            address=host,
                            port_value=port
                        ),
                    ),
                )
            ),
        ],
    )


def _sni_reverse_proxy_cluster(
    vhost: SNIProxyVirtualHost,
    port: int,
    name_func: Callable[[SNIProxyVirtualHost], str]
) -> cluster.cluster.Cluster:
    """
    generate a cluster for an http or https backend

    it is assumed that your backend uses the same proxy protocol settings on the http
    and https ports
    """
    transport_socket = None
    if vhost.proxy_protocol is not None:
        transport_socket = proxy_protocol_transport_socket(vhost.proxy_protocol)
    
    return cluster.cluster.Cluster(
        name=name_func(vhost),
        connect_timeout=google.protobuf.duration_pb2.Duration(seconds=5),
        type=cluster.cluster.Cluster.LOGICAL_DNS,
        dns_lookup_family=cluster.cluster.Cluster.AUTO,
        load_assignment=endpoint.endpoint.ClusterLoadAssignment(
            cluster_name=name_func(vhost),
            endpoints=[
                sni_proxy_locality_endpoint(vhost.host, port),
            ],
        ),
        transport_socket=transport_socket,
    )


def sni_reverse_proxy_http_cluster(
    vhost: SNIProxyVirtualHost
) -> cluster.cluster.Cluster:
    return _sni_reverse_proxy_cluster(vhost, vhost.http_port, http_cluster_name)


def sni_reverse_proxy_https_cluster(
    vhost: SNIProxyVirtualHost
) -> cluster.cluster.Cluster:
    return _sni_reverse_proxy_cluster(vhost, vhost.https_port, https_cluster_name)


