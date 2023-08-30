load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

OPENSSL_VERSION = "3.0.12"

def openssl():
    http_archive(
        name = "openssl",
        urls = [
            "https://www.openssl.org/source/openssl-" + OPENSSL_VERSION + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/openssl-" + OPENSSL_VERSION + ".tar.gz",
        ],
        sha256 = "f93c9e8edde5e9166119de31755fc87b4aa34863662f67ddfcba14d0b6b69b61",
        build_file = "@omd_packages//packages/openssl:BUILD.openssl",
        strip_prefix = "openssl-" + OPENSSL_VERSION,
    )
