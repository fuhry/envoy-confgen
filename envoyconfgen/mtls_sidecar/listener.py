from os import access
import sys
import re

from typing import Collection

import envoyproto.envoy.config.listener.v3 as listener
import envoyproto.envoy.config.core.v3 as core
import envoyproto.envoy.config.route.v3 as route
import envoyproto.envoy.extensions.transport_sockets.tls.v3 as tls
from envoyproto.envoy.type.matcher.v3 import string, regex

from envoyconfgen.filters import (
    http_connection_manager_filter,
    tcp_proxy_listener_filter,
)
from envoyconfgen.helpers import typed_config, file_access_log
from envoyconfgen.structs import MTLSSidecar
from google.protobuf.wrappers_pb2 import BoolValue


def mtls_sidecar_virtual_host() -> route.route_components.VirtualHost:
    return route.route_components.VirtualHost(
        name="mtls_sidecar_vhost",
        domains=["*"],
        routes=[
            route.route_components.Route(
                match=route.route_components.RouteMatch(prefix="/"),
                route=route.route_components.RouteAction(
                    cluster="mtls_sidecar_backend",
                ),
            ),
        ],
    )


def mtls_sidecar_root_routes() -> route.route.RouteConfiguration:
    return route.route.RouteConfiguration(
        name="local_route",
        virtual_hosts=[mtls_sidecar_virtual_host()],
    )


def mtls_sidecar_dns_match(pattern: str) -> tls.common.SubjectAltNameMatcher:
    return tls.common.SubjectAltNameMatcher(
        san_type=tls.common.SubjectAltNameMatcher.DNS,
        matcher=string.StringMatcher(
            safe_regex=regex.RegexMatcher(
                google_re2=regex.RegexMatcher.GoogleRE2(),
                regex=(
                    "^"
                    + pattern.replace(".", "\\.")
                    .replace("**", "[A-Za-z0-9_-]+(\\.[A-Za-z0-9_-]+){0,}")
                    .replace("*", "[A-Za-z0-9_-]+")
                    + "$"
                ),
            ),
        ),
    )


def mtls_sidecar_spiffe_match(
    principal: MTLSSidecar.Listener.SPIFFEMatch,
) -> tls.common.SubjectAltNameMatcher:
    return tls.common.SubjectAltNameMatcher(
        san_type=tls.common.SubjectAltNameMatcher.URI,
        matcher=string.StringMatcher(
            safe_regex=regex.RegexMatcher(
                google_re2=regex.RegexMatcher.GoogleRE2(),
                regex=(
                    "^spiffe://"
                    + principal.trust_domain.replace(".", "\\.")
                    .replace("**", "[A-Za-z0-9_-]+(\\.[A-Za-z0-9_-]+){0,}")
                    .replace("*", "[A-Za-z0-9_-]+")
                    + "/"
                    + principal.service.replace(".", "\\.")
                    .replace("**", "[A-Za-z0-9_\.-]+(\\/[A-Za-z0-9_-]+){0,}")
                    .replace("*", "[A-Za-z0-9_\.-]+")
                    + "$"
                ),
            ),
        ),
    )


def mtls_sidecar_listener(params: MTLSSidecar.Listener) -> listener.listener.Listener:
    transport_socket = core.base.TransportSocket(
        name="envoy.transport_sockets.tls",
        typed_config=typed_config(
            tls.tls.DownstreamTlsContext(
                common_tls_context=tls.tls.CommonTlsContext(
                    validation_context=tls.common.CertificateValidationContext(
                        trusted_ca=core.base.DataSource(filename=params.ca_cert),
                        match_typed_subject_alt_names=(
                            [mtls_sidecar_dns_match(pattern) for pattern in params.match_dns]
                            + [
                                mtls_sidecar_spiffe_match(principal)
                                for principal in params.match_spiffe
                            ]
                        ),
                    ),
                    tls_certificates=[
                        tls.common.TlsCertificate(
                            certificate_chain=core.base.DataSource(filename=params.cert),
                            private_key=core.base.DataSource(filename=params.key),
                        ),
                    ],
                ),
                require_client_certificate=BoolValue(value=True),
            ),
        ),
    )

    return listener.listener.Listener(
        name="mtls_sidecar_listener",
        address=core.address.Address(
            socket_address=core.address.SocketAddress(
                address="::",
                port_value=params.port,
                ipv4_compat=True,
            ),
        ),
        filter_chains=[
            listener.listener_components.FilterChain(
                transport_socket=transport_socket,
                filters=[
                    http_connection_manager_filter(
                        route_config=mtls_sidecar_root_routes(),
                    )
                ],
            ),
        ],
    )
