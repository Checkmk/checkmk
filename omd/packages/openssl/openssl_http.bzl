load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def openssl_workspace():
    version_str = "3.0.14"
    filename = "openssl-" + version_str + ".tar.gz"
    http_archive(
        name = "openssl",
        urls = [
            "https://www.openssl.org/source/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "eeca035d4dd4e84fc25846d952da6297484afa0650a6f84c682e39df3a4123ca",
        build_file = "@omd_packages//omd/packages/openssl:BUILD.openssl.bazel",
        strip_prefix = "openssl-" + version_str,
    )
