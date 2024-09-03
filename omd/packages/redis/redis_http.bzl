load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def redis_workspace():
    version_str = "6.2.6"
    filename = "redis-" + version_str + ".tar.gz"
    http_archive(
        name = "redis",
        urls = [
            "https://download.redis.io/releases/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "5b2b8b7a50111ef395bf1c1d5be11e6e167ac018125055daa8b5c2317ae131ab",
        build_file = "@omd_packages//omd/packages/redis:BUILD.redis.bazel",
        strip_prefix = "redis-" + version_str,
    )
