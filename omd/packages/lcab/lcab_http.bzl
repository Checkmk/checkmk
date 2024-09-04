load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def lcab_workspace():
    version_str = "1.0b12"
    filename = "lcab-" + version_str + ".tar.gz"
    http_archive(
        name = "lcab",
        build_file = "@omd_packages//omd/packages/lcab:BUILD.lcab.bazel",
        strip_prefix = "lcab-" + version_str,
        urls = [
            "http://archlinux.c3sl.ufpr.br/other/lcab/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "065f2c1793b65f28471c0f71b7cf120a7064f28d1c44b07cabf49ec0e97f1fc8",
    )
