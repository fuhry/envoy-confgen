from typing import Callable, Optional

import envoyproto.envoy.config.cluster.v3 as cluster
import envoyproto.envoy.config.core.v3 as core
import envoyproto.envoy.config.endpoint.v3 as endpoint
import envoyproto.envoy.extensions.transport_sockets.tls.v3 as tls

import google.protobuf.any_pb2
import google.protobuf.message
import google.protobuf.duration_pb2

from envoyconfgen.filters import proxy_protocol_transport_socket
from envoyconfgen.helpers import typed_config
from envoyconfgen.structs import MTLSSidecar


def mtls_sidecar_locality_endpoint(
    params: MTLSSidecar.Backend,
) -> endpoint.endpoint_components.LocalityLbEndpoints:
    return endpoint.endpoint_components.LocalityLbEndpoints(
        lb_endpoints=[
            endpoint.endpoint_components.LbEndpoint(
                endpoint=endpoint.endpoint_components.Endpoint(
                    address=core.address.Address(
                        socket_address=core.address.SocketAddress(
                            address=params.host,
                            port_value=params.port,
                        ),
                    ),
                ),
            ),
        ],
    )


def mtls_sidecar_cluster(params: MTLSSidecar.Backend) -> cluster.cluster.Cluster:
    transport_socket: Optional[core.base.TransportSocket] = None

    if params.ca_cert is not None:
        transport_socket = core.base.TransportSocket(
            name="envoy.transport_sockets.tls",
            typed_config=typed_config(
                tls.tls.UpstreamTlsContext(
                    common_tls_context=tls.tls.CommonTlsContext(
                        validation_context=tls.common.CertificateValidationContext(
                            trusted_ca=core.base.DataSource(filename=params.ca_cert),
                        ),
                    ),
                ),
            ),
        )

    return cluster.cluster.Cluster(
        name="mtls_sidecar_backend",
        connect_timeout=google.protobuf.duration_pb2.Duration(seconds=5),
        type=cluster.cluster.Cluster.LOGICAL_DNS,
        dns_lookup_family=cluster.cluster.Cluster.AUTO,
        transport_socket=transport_socket,
        load_assignment=endpoint.endpoint.ClusterLoadAssignment(
            cluster_name="mtls_sidecar_backend",
            endpoints=[mtls_sidecar_locality_endpoint(params)],
        ),
    )
