load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

OPENSSL_VERSION = "1.1.1u"

def openssl():
    http_archive(
        name = "openssl",
        urls = [
            "https://www.openssl.org/source/openssl-" + OPENSSL_VERSION + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/openssl-" + OPENSSL_VERSION + ".tar.gz",
        ],
	sha256 = "e2f8d84b523eecd06c7be7626830370300fbcc15386bf5142d72758f6963ebc6",
        build_file = "@omd_packages//packages/openssl:BUILD.openssl",
        strip_prefix = "openssl-" + OPENSSL_VERSION,
    )
