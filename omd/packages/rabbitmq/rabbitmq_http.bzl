load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def rabbitmq(version_str, sha256):
    filename = "rabbitmq-server-generic-unix-" + version_str + ".tar.xz"
    http_archive(
        name = "rabbitmq",
        build_file = "@omd_packages//omd/packages/rabbitmq:BUILD",
        urls = [
            "https://github.com/rabbitmq/rabbitmq-server/releases/download/v" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        strip_prefix = "rabbitmq_server-" + version_str,
    )
