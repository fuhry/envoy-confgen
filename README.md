# Envoy Config Generator

Tool for building processors that turn simple YAML into complete, working Envoy proxy configuration.

## Usage

```shell
$ envoy-confgen -p <processor> input.yaml [-o output.yaml]
```

* `<processor>` is the processor you want to have parse your YAML. Think of it as a profile or preset.
* `input.yaml` - format is defined in schemas below
* `-o output.yaml` - file to write generated envoy configuration to; if omitted, writes to standard output.

## Processors

### `mtls_sidecar`: mTLS-enforcing universal sidecar

Universal sidecar designed to wrap any HTTP service in mTLS.

The schema is simple:

```yaml
backend:
  host: 127.0.0.1    # optional, defaults to "127.0.0.1"
  port: 12345
  ca_cert: /some/path   # optional - if omitted, connects using plain HTTP
listener:
  port: 12346
  ca_cert: /some/path
  cert: /some/path
  key: /some/path
  match_cn:
    - pattern_1
    - pattern_2
  timeouts:             # optional
    route: 120s         # optional, 120s is the default
```

`match_cn` uses simple wildcards:

* `*` matches a single domain component - so `foo.*.bar` matches `foo.one.bar` but not `foo.one.two.bar`.
* `**` matches any number of domain components - `foo.**.bar` matches `foo.one.bar` and `foo.one.two.bar`.

### `zkfp`: zero-knowledge frontend proxy

SNI proxy that can route to the correct backends without the need for certificates on the edge.

The schema looks like this:

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

# Requirements

* [envoyproto-python](https://github.com/fuhry/envoyproto-python).

# Author

Dan Fuhry <[dan@fuhry.com](mailto:dan@fuhry.com)>

# License

This project is released under the [Apache License 2.0](LICENSE).
