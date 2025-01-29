load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def rabbitmq_workspace():
    version_str = "3.13.6"
    filename = "rabbitmq-server-generic-unix-" + version_str + ".tar.xz"
    http_archive(
        name = "rabbitmq",
        build_file = "@omd_packages//omd/packages/rabbitmq:BUILD",
        urls = [
            "https://github.com/rabbitmq/rabbitmq-server/releases/download/v" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "7bfc742e3d227e8a2b1ea2a0b5ef3ba4b6a7987d5e220e0fbf0919d29b6ed43c",
        strip_prefix = "rabbitmq_server-" + version_str,
    )
