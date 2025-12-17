load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def redis_workspace():
    version_str = "8.4.0"
    filename = "redis-" + version_str + ".tar.gz"
    http_archive(
        name = "redis",
        urls = [
            "https://download.redis.io/releases/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "ca909aa15252f2ecb3a048cd086469827d636bf8334f50bb94d03fba4bfc56e8",
        build_file = "@omd_packages//omd/packages/redis:BUILD.redis.bazel",
        strip_prefix = "redis-" + version_str,
    )
