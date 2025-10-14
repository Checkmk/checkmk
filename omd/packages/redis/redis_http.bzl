load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def redis_workspace():
    version_str = "6.2.20"
    filename = "redis-" + version_str + ".tar.gz"
    http_archive(
        name = "redis",
        urls = [
            "https://download.redis.io/releases/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "7f8b8a7aed53c445a877adf9e3743cdd323518524170135a58c0702f2dba6ef4",
        build_file = "@omd_packages//omd/packages/redis:BUILD.redis.bazel",
        strip_prefix = "redis-" + version_str,
    )
