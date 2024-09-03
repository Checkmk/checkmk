load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def snap7_workspace():
    version_str = "1.4.2"
    filename = "snap7-" + version_str + ".tar.gz"
    http_archive(
        name = "snap7",
        urls = [
            # since version 1.4.2 only 7z will be released. To get a tar.gz
            # use the snap7 repackage target
            # "https://sourceforge.net/projects/snap7/files/" + version_str + "snap7-full-" + version_str + ".7z",
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "fe137737b432d95553ebe5d5f956f0574c6a80c0aeab7a5262fb36b535df3cf4",
        build_file = "@omd_packages//omd/packages/snap7:BUILD.snap7.bazel",
        strip_prefix = "snap7-" + version_str,
    )
