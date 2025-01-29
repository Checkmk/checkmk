load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def libgsf_workspace():
    version_str = "1.14.44"
    filename = "libgsf-" + version_str + ".tar.xz"
    http_archive(
        name = "libgsf",
        build_file = "@omd_packages//omd/packages/libgsf:BUILD.libgsf.bazel",
        strip_prefix = "libgsf-" + version_str,
        urls = [
            "https://ftp.osuosl.org/pub/blfs/conglomeration/libgsf/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "68bede10037164764992970b4cb57cd6add6986a846d04657af9d5fac774ffde",
    )
