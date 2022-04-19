# Envoy Zero Knowledge Frontend Proxy

Configurator for Envoy to expose bare-minimum TLS SNI proxy functionality in a simple YAML format.

## Features

- Generates startup configuration with static resources only
- TODO: XDS service
- TODO: Instant reload using inotify

## Schema

```yaml
listeners:
  - protocol: http
    port: 80
    address: "::"
  - protocol: https
    port: 443
    address: "::"
backends:
  # one entry per backend host
  - host: example.com
    proxy_protocol: v2
    # optional, defaults to 80
    http_port: 80
    # optional, defaults to 443
    http_port: 443
    patterns:
      # each pattern will be matched on the HTTP host header (plain http) or
      # TLS SNI (HTTPS)
      - "*.example.com"
      - "example.com"
```

## Requirements

* [envoyproto-python](https://github.com/fuhry/envoyproto-python).

# Author

Dan Fuhry <[dan@fuhry.com](mailto:dan@fuhry.com)>

# License

This project is released under the [Apache License 2.0](LICENSE).
