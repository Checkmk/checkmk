load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def redis(version_str, sha256):
    filename = "redis-" + version_str + ".tar.gz"
    http_archive(
        name = "redis",
        urls = [
            "https://download.redis.io/releases/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        build_file = "@omd_packages//omd/packages/redis:BUILD.redis",
        strip_prefix = "redis-" + version_str,
    )
