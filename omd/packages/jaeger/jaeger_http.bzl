load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def jaeger_workspace():
    version_str = "2.3.0"
    filename = "jaeger-" + version_str + "-linux-amd64.tar.gz"
    upstream_url = "https://github.com/jaegertracing/jaeger/releases/download/v1.66.0/"

    http_file(
        name = "jaeger",
        urls = [
            upstream_url + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "7120929235daf1a0a79c7ffb0c2835d119ec83c5f8b3df99c8a57ccdd25b0184",
    )
