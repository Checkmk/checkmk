load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def redis_workspace():
    version_str = "8.4.5"
    filename = "redis-" + version_str + ".tar.gz"
    http_archive(
        name = "redis",
        urls = [
            "https://download.redis.io/releases/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "686321b1a03bb8f0ad7114e29516a31273e200ec69aa9bf457de3c2be3f2184f",
        build_file = "@omd_packages//omd/packages/redis:BUILD.redis.bazel",
        strip_prefix = "redis-" + version_str,
    )
