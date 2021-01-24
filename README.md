# Envoy Zero Knowledge Frontend Proxy

Configurator for Envoy to expose bare-minimum TLS SNI proxy functionality in a simple YAML format.

## Features

- Generate initial configuration
- TODO: Reconfigure running Envoy instance using XDS
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
