load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

OPENSSL_VERSION = "1.1.1q"

def openssl():
    http_archive(
        name = "openssl",
        urls = [
            "https://www.openssl.org/source/openssl-" + OPENSSL_VERSION + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/openssl-" + OPENSSL_VERSION + ".tar.gz",
        ],
        sha256 = "d7939ce614029cdff0b6c20f0e2e5703158a489a72b2507b8bd51bf8c8fd10ca",
        build_file = "@omd_packages//packages/openssl:BUILD.openssl",
        strip_prefix = "openssl-" + OPENSSL_VERSION,
    )
