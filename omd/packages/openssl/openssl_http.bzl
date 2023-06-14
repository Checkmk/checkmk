load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def openssl(version_str, sha256):
    filename = "openssl-" + version_str + ".tar.gz"
    http_archive(
        name = "openssl",
        urls = [
            "https://www.openssl.org/source/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        build_file = "@omd_packages//packages/openssl:BUILD.openssl",
        strip_prefix = "openssl-" + version_str,
    )
