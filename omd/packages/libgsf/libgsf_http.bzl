load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def libgsf(version_str, sha256):
    filename = "libgsf-" + version_str + ".tar.xz"
    http_archive(
        name = "libgsf",
        build_file = "@omd_packages//packages/libgsf:BUILD.libgsf.bazel",
        strip_prefix = "libgsf-" + version_str,
        urls = [
            "https://ftp.osuosl.org/pub/blfs/conglomeration/libgsf/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
    )
