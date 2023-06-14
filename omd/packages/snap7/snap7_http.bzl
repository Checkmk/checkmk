load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def snap7(version_str, sha256):
    filename = "snap7-" + version_str + ".tar.gz"
    http_archive(
        name = "snap7",
        urls = [
            # since version 1.4.2 only 7z will be released. To get a tar.gz
            # use the snap7 repackage target
            # "https://sourceforge.net/projects/snap7/files/" + version_str + "snap7-full-" + version_str + ".7z",
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        build_file = "@omd_packages//packages/snap7:BUILD.snap7.bazel",
        strip_prefix = "snap7-" + version_str,
    )
