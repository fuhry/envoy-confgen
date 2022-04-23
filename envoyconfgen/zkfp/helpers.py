from envoyconfgen.helpers import clean_vhost_name
from envoyconfgen.structs import SNIProxyVirtualHost


def http_cluster_name(vhost: SNIProxyVirtualHost) -> str:
    return "%s_%s_%d" % (clean_vhost_name(vhost.host), "http", vhost.http_port)


def https_cluster_name(vhost: SNIProxyVirtualHost) -> str:
    return "%s_%s_%d" % (clean_vhost_name(vhost.host), "https", vhost.https_port)
