load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def lcab(version_str, sha256):
    filename = "lcab-" + version_str + ".tar.gz"
    http_archive(
        name = "lcab",
        build_file = "@omd_packages//packages/lcab:BUILD.lcab.bazel",
        strip_prefix = "lcab-" + version_str,
        urls = [
            "http://archlinux.c3sl.ufpr.br/other/lcab/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
    )
