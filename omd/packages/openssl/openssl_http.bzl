load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def openssl(version_str, sha256):
    http_archive(
        name = "openssl",
        urls = [
            "https://www.openssl.org/source/openssl-" + version_str + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/openssl-" + version_str + ".tar.gz",
        ],
        sha256 = sha256,
        build_file = "@omd_packages//packages/openssl:BUILD.openssl",
        strip_prefix = "openssl-" + version_str,
    )
