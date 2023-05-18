load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

OPENSSL_VERSION = "1.1.1t"

def openssl():
    http_archive(
        name = "openssl",
        urls = [
            "https://www.openssl.org/source/openssl-" + OPENSSL_VERSION + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/openssl-" + OPENSSL_VERSION + ".tar.gz",
        ],
	sha256 = "8dee9b24bdb1dcbf0c3d1e9b02fb8f6bf22165e807f45adeb7c9677536859d3b",
        build_file = "@omd_packages//packages/openssl:BUILD.openssl",
        strip_prefix = "openssl-" + OPENSSL_VERSION,
    )
