from __future__ import annotations

import json
import sys
from typing import Any, Tuple
import yaml

import google.protobuf.json_format

from .bootstrap import generate_bootstrap
from . import processors
from .structs import SNIProxyListener, SNIProxyVirtualHost, proxy_protocol_str_to_enum

from envoyproto.envoy.config.bootstrap.v3 import bootstrap


def process_yaml(processor: AbstractProcessor, yaml_path: str) -> bootstrap.Bootstrap:
    with open(yaml_path, "r") as fp:
        contents = yaml.safe_load(fp)

    assert isinstance(contents, dict)
    errors = processor.validate_yaml(contents)
    if len(errors) > 0:
        errstr = (
            f'Could not parse YAML file "{yaml_path}".\n'
            + "The following problems were found:\n"
            + "".join(f"  - {e}\n" for e in errors)
        )

        print(errstr, file=sys.stderr)
        raise RuntimeError("Failed to parse YAML input")

    listeners, clusters = processor.process_yaml(contents)
    return generate_bootstrap(listeners, clusters)


def do_translate(args):
    processor = getattr(processors, args.processor)

    config_root = process_yaml(processor(), args.path)

    # XXX(fuhry@2022-04-18) both of the things done here are pretty awful, but (1) google
    # native protobuf doesn't support yaml so we need json as an intermediate format, and
    # (2) de-namespacing has to be done at this level because the json_format module
    # deserializes google.protobuf.Any messages and writes them as json.
    result_str = google.protobuf.json_format.MessageToJson(
        config_root, sort_keys=True, preserving_proto_field_name=True
    ).replace("type.googleapis.com/envoyproto.", "type.googleapis.com/")

    result_str = yaml.dump(json.loads(result_str))

    if args.output is not None:
        with open(args.output, "w") as fp:
            fp.write(result_str)
    else:
        sys.stdout.write(result_str)
