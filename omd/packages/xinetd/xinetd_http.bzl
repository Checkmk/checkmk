load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def xinetd_workspace():
    version_str = "2.3.15.4"
    filename = "xinetd-" + version_str + ".tar.xz"
    http_archive(
        name = "xinetd",
        build_file = "@omd_packages//omd/packages/xinetd:BUILD.xinetd.bazel",
        strip_prefix = "xinetd-" + version_str,
        urls = [
            "https://github.com/openSUSE/xinetd/releases/download/" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "2baa581010bc70361abdfa37f121e92aeb9c5ce67f9a71913cebd69359cc9654",
    )
