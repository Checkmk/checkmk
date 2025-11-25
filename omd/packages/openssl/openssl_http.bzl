load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def openssl_workspace():
    version_str = "3.5.4"
    filename = "openssl-" + version_str + ".tar.gz"
    http_archive(
        name = "openssl",
        urls = [
            "https://github.com/openssl/openssl/releases/download/openssl-" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "967311f84955316969bdb1d8d4b983718ef42338639c621ec4c34fddef355e99",
        build_file = "@omd_packages//omd/packages/openssl:BUILD.openssl.bazel",
        strip_prefix = "openssl-" + version_str,
    )
