load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def jaeger_workspace():
    version_str = "1.58.1"
    filename = "jaeger-" + version_str + "-linux-amd64.tar.gz"
    upstream_url = "https://github.com/jaegertracing/jaeger/releases/download/v" + version_str + "/"

    http_file(
        name = "jaeger",
        urls = [
            upstream_url + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "0581d1d3c59ea32d1c3d8a1a6783341ab99a050428abb5d29c717e468680c365",
    )
