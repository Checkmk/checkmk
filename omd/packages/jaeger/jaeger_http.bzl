load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def jaeger(version_str, sha256):
    filename = "jaeger-" + version_str + "-linux-amd64.tar.gz"
    upstream_url = "https://github.com/jaegertracing/jaeger/releases/download/v" + version_str + "/"

    http_file(
        name = "jaeger",
        urls = [
            upstream_url + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
    )
