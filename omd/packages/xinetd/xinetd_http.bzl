load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def xinetd(version_str, sha256):
    filename = "xinetd-" + version_str + ".tar.xz"
    http_archive(
        name = "xinetd",
        build_file = "@omd_packages//omd/packages/xinetd:BUILD.xinetd.bazel",
        strip_prefix = "xinetd-" + version_str,
        urls = [
            "https://github.com/openSUSE/xinetd/releases/download/" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
    )
