load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

REDIS_VERSION = "6.2.6"

def redis():
    http_archive(
        name = "redis",
        urls = [
            "https://download.redis.io/releases/redis-" + REDIS_VERSION + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/redis-" + REDIS_VERSION + ".tar.gz",
        ],
        sha256 = "5b2b8b7a50111ef395bf1c1d5be11e6e167ac018125055daa8b5c2317ae131ab",
        build_file = '@omd_packages//packages/redis:BUILD.redis',
        strip_prefix = 'redis-' + REDIS_VERSION,
    )
