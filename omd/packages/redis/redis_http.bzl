load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def redis(version_str, sha256):
    http_archive(
        name = "redis",
        urls = [
            "https://download.redis.io/releases/redis-" + version_str + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/redis-" + version_str + ".tar.gz",
        ],
        sha256 = sha256,
        build_file = '@omd_packages//packages/redis:BUILD.redis',
        strip_prefix = 'redis-' + version_str,
    )
