load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def jaeger_workspace():
    version_str = "2.0.0"
    filename = "jaeger-" + version_str + "-linux-amd64.tar.gz"
    upstream_url = "https://github.com/jaegertracing/jaeger/releases/download/v1.63.0/"

    http_file(
        name = "jaeger",
        urls = [
            upstream_url + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "d2782c1a240bc2601d6cc74d181c7919e715f2d779111dbb167ec2cd9f8d2a2b",
    )
