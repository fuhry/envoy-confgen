from __future__ import annotations
from abc import abstractmethod
from typing import Any, Iterable
import sys, inspect

from .zkfp.cluster import sni_reverse_proxy_http_cluster, sni_reverse_proxy_https_cluster
from .zkfp.listener import sni_reverse_proxy_listener
from .mtls_sidecar.cluster import mtls_sidecar_cluster
from .mtls_sidecar.listener import mtls_sidecar_listener
from .structs import MTLSSidecar, SNIProxyListener, SNIProxyVirtualHost

import envoyproto.envoy.config.cluster.v3 as cluster
import envoyproto.envoy.config.listener.v3 as listener


T_static_resources = tuple[list[listener.listener.Listener], list[cluster.cluster.Cluster]]
T_yaml = dict[str, Any]


class AbstractProcessor:
    @property
    @abstractmethod
    def required_keys(self) -> list[tuple[str, type]]:
        pass

    def validate_yaml(self, yaml: T_yaml) -> list[str]:
        if not isinstance(yaml, dict):
            return ['YAML must be a dictionary at the top level']

        errors = []
        for k, t in self.required_keys:
            if k not in yaml:
                errors.append(f'YAML is missing key "{k}"')
                continue
            
            if not isinstance(yaml[k], t):
                errors.append(f'key "{k}" appears to be a {yaml[k].__class__.__name__}, expected {t}')
                continue

        return errors

    @abstractmethod
    def process_yaml(self, yaml: T_yaml) -> T_static_resources:
        pass

class zkfp(AbstractProcessor):
    def _yaml_to_internal_structs(self, contents: T_yaml) -> tuple[list[SNIProxyListener], list[SNIProxyVirtualHost]]:
        listeners = [
            SNIProxyListener(**l)
            for l in contents['listeners']
        ]

        def filter_mandatory_args(backend: dict[str, Any]):
            for key in ['host', 'patterns', 'proxy_protocol']:
                if key in backend:
                    del backend[key]

            return backend

        virtual_hosts = [
            SNIProxyVirtualHost(
                host=backend['host'],
                patterns=backend['patterns'],
                proxy_protocol=(
                    proxy_protocol_str_to_enum[backend['proxy_protocol']]
                    if 'proxy_protocol' in backend and backend['proxy_protocol'] is not None
                    else None
                ),
                **filter_mandatory_args(backend)
            )
            for backend in contents['backends']
        ]

        return listeners, virtual_hosts
    

    @property
    def required_keys(self) -> list[tuple[str, type]]:
        return [
            ('listeners', list),
            ('backends', list),
        ]
        
    
    def process_yaml(self, yaml: T_yaml) -> T_static_resources:
        listeners, vhosts = self._yaml_to_internal_structs(yaml)

        envoy_listeners = [
            sni_reverse_proxy_listener(l.protocol, l.address, l.port, vhosts)
            for l in listeners
        ]

        envoy_clusters = [
            sni_reverse_proxy_http_cluster(vhost)
            for vhost in vhosts
        ] + [
            sni_reverse_proxy_https_cluster(vhost)
            for vhost in vhosts
        ]

        return envoy_listeners, envoy_clusters

class mtls_sidecar(AbstractProcessor):
    @property
    def required_keys(self) -> list[tuple[str, type]]:
        return [
            ('listener', dict),
            ('backend', dict),
        ]

    def process_yaml(self, yaml: T_yaml) -> T_static_resources:
        as_struct = MTLSSidecar(
            backend=MTLSSidecar.Backend(**yaml['backend']),
            listener=MTLSSidecar.Listener(**yaml['listener']),
        )

        envoy_clusters = [mtls_sidecar_cluster(as_struct.backend)]
        envoy_listeners = [mtls_sidecar_listener(as_struct.listener)]

        return envoy_listeners, envoy_clusters


def is_a_processor(member: Any) -> bool:
    if not isinstance(member, type):
        return False
        
    if member.__module__ != __name__:
        return False
    
    if member not in AbstractProcessor.__subclasses__():
        return False
    
    return True


def all() -> Iterable[AbstractProcessor]:
    for _, member in inspect.getmembers(sys.modules[__name__]):
        if is_a_processor(member):
            yield member
