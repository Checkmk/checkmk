load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def openssl_workspace():
    version_str = "3.0.16"
    filename = "openssl-" + version_str + ".tar.gz"
    http_archive(
        name = "openssl",
        urls = [
            "https://github.com/openssl/openssl/releases/download/openssl-" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "57e03c50feab5d31b152af2b764f10379aecd8ee92f16c985983ce4a99f7ef86",
        build_file = "@omd_packages//omd/packages/openssl:BUILD.openssl.bazel",
        strip_prefix = "openssl-" + version_str,
    )
