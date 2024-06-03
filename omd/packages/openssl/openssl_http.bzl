load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

OPENSSL_VERSION = "1.1.1w"

def openssl():
    http_archive(
        name = "openssl",
        urls = [
            "https://openssl.org/source/old/1.1.1/openssl-" + OPENSSL_VERSION + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/openssl-" + OPENSSL_VERSION + ".tar.gz",
        ],
        sha256 = "cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8",
        build_file = "@omd_packages//packages/openssl:BUILD.openssl",
        strip_prefix = "openssl-" + OPENSSL_VERSION,
    )
