from __future__ import annotations

import json
import sys
from typing import Any, Tuple
import yaml

import google.protobuf.json_format

from .structs import SNIProxyListener, SNIProxyVirtualHost, proxy_protocol_str_to_enum
from .bootstrap import generate_bootstrap


def translate_yaml_to_structs(path: str) -> Tuple[list[SNIProxyListener], list[SNIProxyVirtualHost]]:
    with open(path, 'r') as fp:
        contents = yaml.safe_load(fp)

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


def do_translate(args):
    listeners, vhosts = translate_yaml_to_structs(args.path)

    bootstrap = generate_bootstrap(listeners, vhosts)

    # XXX(fuhry@2022-04-18) both of the things done here are pretty awful, but (1) google
    # native protobuf doesn't support yaml so we need json as an intermediate format, and
    # (2) de-namespacing has to be done at this level because the json_format module
    # deserializes google.protobuf.Any messages and writes them as json.
    result_str = google.protobuf.json_format.MessageToJson(
        bootstrap, sort_keys=True, preserving_proto_field_name=True
    ).replace(
        'type.googleapis.com/envoyproto.', 'type.googleapis.com/'
    )

    result_str = yaml.dump(json.loads(result_str))

    if args.output is not None:
        with open(args.output, 'w') as fp:
            fp.write(result_str)
    else:
        sys.stdout.write(result_str)
