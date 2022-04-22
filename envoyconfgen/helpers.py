import re

import google.protobuf.any_pb2
import google.protobuf.message
import google.protobuf.duration_pb2

import envoyproto.envoy.config.accesslog.v3 as accesslog
from envoyproto.envoy.extensions.access_loggers.file.v3 import file as fal

from .config import singleton

config = singleton.get_config()

def clean_vhost_name(host: str) -> str:
    return re.sub('[^a-z0-9]+', '_', host)


def typed_config(message: google.protobuf.message.Message) -> google.protobuf.any_pb2.Any:
    msg = google.protobuf.any_pb2.Any()
    msg.Pack(message)
    # NOTE(fuhry@2022-04-18): the de-namespacing is currently done at a later stage
    # in :ref:`.convert.do_translate`.
    # msg.type_url = 'type.googleapis.com/' + msg.type_url.removeprefix('type.googleapis.com/envoyproto.')
    return msg


def file_access_log() -> accesslog.accesslog.AccessLog:
    return accesslog.accesslog.AccessLog(
       name="envoy.access_loggers.file",
       typed_config=typed_config(
           fal.FileAccessLog(
               path=config['envoy']['access_log']
           )
       ) 
    )


