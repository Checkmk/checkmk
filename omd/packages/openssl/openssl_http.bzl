load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def openssl_workspace():
    version_str = "3.0.13"
    filename = "openssl-" + version_str + ".tar.gz"
    http_archive(
        name = "openssl",
        urls = [
            "https://www.openssl.org/source/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "88525753f79d3bec27d2fa7c66aa0b92b3aa9498dafd93d7cfa4b3780cdae313",
        build_file = "@omd_packages//omd/packages/openssl:BUILD.openssl.bazel",
        strip_prefix = "openssl-" + version_str,
    )
