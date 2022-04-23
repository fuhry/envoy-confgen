from typing import Callable

import envoyproto.envoy.config.cluster.v3 as cluster
import envoyproto.envoy.config.core.v3 as core
import envoyproto.envoy.config.endpoint.v3 as endpoint

import google.protobuf.any_pb2
import google.protobuf.message
import google.protobuf.duration_pb2

from envoyconfgen.filters import proxy_protocol_transport_socket
from envoyconfgen.helpers import typed_config
from envoyconfgen.structs import SNIProxyVirtualHost
from .helpers import http_cluster_name, https_cluster_name


def sni_proxy_locality_endpoint(
    host: str, port: int
) -> endpoint.endpoint_components.LocalityLbEndpoints:
    return endpoint.endpoint_components.LocalityLbEndpoints(
        lb_endpoints=[
            endpoint.endpoint_components.LbEndpoint(
                endpoint=endpoint.endpoint_components.Endpoint(
                    address=core.address.Address(
                        socket_address=core.address.SocketAddress(address=host, port_value=port),
                    ),
                )
            ),
        ],
    )


def _sni_reverse_proxy_cluster(
    vhost: SNIProxyVirtualHost, port: int, name_func: Callable[[SNIProxyVirtualHost], str]
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


def sni_reverse_proxy_http_cluster(vhost: SNIProxyVirtualHost) -> cluster.cluster.Cluster:
    return _sni_reverse_proxy_cluster(vhost, vhost.http_port, http_cluster_name)


def sni_reverse_proxy_https_cluster(vhost: SNIProxyVirtualHost) -> cluster.cluster.Cluster:
    return _sni_reverse_proxy_cluster(vhost, vhost.https_port, https_cluster_name)
