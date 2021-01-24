import yaml
import sys
import re
from copy import deepcopy

def generate_listener(protocol, backends, address='::', port=443):
    return {
        'name': f'{protocol}_{port}',
        'address': {
            'socket_address': {
                'address': address,
                'port_value': port,
                'ipv4_compat': True,
            },
        },
        'listener_filters': [
            {
                'name': 'envoy.filters.listener.tls_inspector',
                'typed_config': {
                    '@type': 'type.googleapis.com/envoy.extensions.filters.listener.tls_inspector.v3.TlsInspector',

                },
            },
        ],
        'filter_chains': generate_filter_chains(protocol, backends),
    }

def sanitize_host(h):
    return re.sub('[^a-z0-9]+', '_', h)

def generate_cluster(host, http_port=80, https_port=443, proxy_protocol=None, patterns=[]):
    clusters = []

    transport_socket_amendment = {}
    if proxy_protocol is not None:
        transport_socket_amendment = {
            'transport_socket': {
                'name': 'envoy.transport_sockets.proxy_protocol',
                'typed_config': {
                    '@type': 'type.googleapis.com/envoy.extensions.transport_sockets.proxy_protocol.v3.ProxyProtocolUpstreamTransport',
                    'config': {
                        'version': 'V2' if proxy_protocol == 'v2' else 'V1',
                    },
                    'transport_socket': {
                        'name': 'envoy.transport_sockets.raw_buffer',
                        'typed_config': {
                            '@type': 'type.googleapis.com/envoy.extensions.transport_sockets.raw_buffer.v3.RawBuffer',
                        },
                    },
                },
            }
        }

    clusters.append(dict({
        'name': '%s_http_%d' % (sanitize_host(host), http_port),
        'connect_timeout': '5s',
        'type': 'LOGICAL_DNS',
        'load_assignment': {
            'cluster_name': '%s_http_%d' % (sanitize_host(host), http_port),
            'endpoints': [
                {
                    "lb_endpoints": [
                        {
                            "endpoint": {
                                "address": {
                                    "socket_address": {
                                        "address": host,
                                        "port_value": http_port,
                                    },
                                },
                            },
                        },
                    ],
                },
            ],
        },
    }, **deepcopy(transport_socket_amendment)))

    clusters.append(dict({
        'name': '%s_https_%d' % (sanitize_host(host), https_port),
        'connect_timeout': '5s',
        'type': 'LOGICAL_DNS',
        'load_assignment': {
            'cluster_name': '%s_https_%d' % (sanitize_host(host), https_port),
            'endpoints': [
                {
                    "lb_endpoints": [
                        {
                            "endpoint": {
                                "address": {
                                    "socket_address": {
                                        "address": host,
                                        "port_value": https_port,
                                    },
                                },
                            },
                        },
                    ],
                },
            ],
        },
    }, **deepcopy(transport_socket_amendment)))

    return clusters

def generate_filter_chains(protocol, backends):
    route_config = {
        'name': 'local_route',
        'virtual_hosts': [],
    }

    if protocol == 'http':
        for backend in backends:
            port = backend['http_port'] if 'http_port' in backend else 80
            route_config['virtual_hosts'].append({
                'name': '%s_service_%s_%d' % (sanitize_host(backend['host']), protocol, port),
                'domains': backend['patterns'] + [f'{p}:{port}' for p in backend['patterns']],
                'routes': [
                    {
                        'match': { 'prefix': '/' },
                        'route': {
                            'cluster': '%s_%s_%d' % (sanitize_host(backend['host']), protocol, port),
                        },
                    }
                ],
            })

        return [
            {
                'filters': [
                    {
                        'name': 'envoy.filters.network.http_connection_manager',
                        'typed_config': {
                            '@type': 'type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager',
                            'stat_prefix': 'ingress_http',
                            'access_log': [
                                {
                                    'name': 'envoy.access_loggers.file',
                                    'typed_config': {
                                        '@type': 'type.googleapis.com/envoy.extensions.access_loggers.file.v3.FileAccessLog',
                                        'path': '/dev/stdout',
                                    },
                                },
                            ],
                            'http_filters': [
                                { 'name': 'envoy.filters.http.router' },
                            ],
                            'route_config': route_config,
                        },
                    },
                ],
            },
        ]
    elif protocol == 'https':
        return [
            {
                'filter_chain_match': {
                    'server_names': backend['patterns'],
                },
                'filters': [
                    {
                        'name': 'envoy.filters.network.tcp_proxy',
                        'typed_config': {
                            '@type': 'type.googleapis.com/envoy.extensions.filters.network.tcp_proxy.v3.TcpProxy',
                            'stat_prefix': 'ingress_https',
                            'access_log': [
                                {
                                    'name': 'envoy.access_loggers.file',
                                    'typed_config': {
                                        '@type': 'type.googleapis.com/envoy.extensions.access_loggers.file.v3.FileAccessLog',
                                        'path': '/dev/stdout',
                                    },
                                },
                            ],
                            'cluster': '%s_%s_%d' % (sanitize_host(backend['host']), protocol, backend['https_port'] if 'https_port' in backend else 443),
                        },
                    },
                ]
            }
            for backend in backends
        ]



def generate_base():
    return {
        'admin': {
            'access_log_path': '/dev/null',
            'address': {
                'socket_address': {
                    'address': '0.0.0.0',
                    'port_value': 9901,
                },
            },
        },
        'static_resources': {
            'listeners': [],
            'clusters': [],
        }
    }

def translate_to_envoy(path):
    with open(path, 'r') as fp:
        contents = yaml.safe_load(fp)

    base_config = generate_base()

    for l in contents['listeners']:
        base_config['static_resources']['listeners'] += [generate_listener(**l, backends=contents['backends'])]

    for b in contents['backends']:
        base_config['static_resources']['clusters'] += generate_cluster(**b)

    return base_config

def do_translate(args):
    result = translate_to_envoy(args.path)

    if args.output is not None:
        with open(args.output, 'w') as fp:
            fp.write(yaml.dump(result))
    else:
        sys.stdout.write(yaml.dump(result))
