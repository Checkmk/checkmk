load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def redis(version_str, sha256):
    http_archive(
        name = "redis",
        urls = [
            "https://download.redis.io/releases/redis-" + version_str + ".tar.gz",
            UPSTREAM_MIRROR_URL + "redis-" + version_str + ".tar.gz",
        ],
        sha256 = sha256,
        build_file = '@omd_packages//packages/redis:BUILD.redis',
        strip_prefix = 'redis-' + version_str,
    )
