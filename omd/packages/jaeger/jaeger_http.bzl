load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def jaeger_workspace():
    version_str = "2.18.0"
    filename = "jaeger-" + version_str + "-linux-amd64.tar.gz"
    upstream_url = "https://github.com/jaegertracing/jaeger/releases/download/v" + version_str + "/"

    http_file(
        name = "jaeger",
        urls = [
            upstream_url + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "1d810bf04f7e08dac796ad532fc68f1a8fceb0333d2524ae767d88533e69ed75",
    )
