load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def openssl(version_str, sha256):
    http_archive(
        name = "openssl",
        urls = [
            "https://www.openssl.org/source/openssl-" + version_str + ".tar.gz",
            UPSTREAM_MIRROR_URL + "openssl-" + version_str + ".tar.gz",
        ],
        sha256 = sha256,
        build_file = "@omd_packages//packages/openssl:BUILD.openssl",
        strip_prefix = "openssl-" + version_str,
    )
