load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def re2(version_str, sha256):
    filename = "re2-" + version_str + ".tar.gz"
    http_archive(
        name = "re2",
        urls = [
            # Also checked in under "/third_party/re2"
            # TODO: "releases/download/" + version_str + "/" + filename introduced with 2023-06-02 release and later
            # "https://github.com/google/re2/releases/download/" + version_str + "/" + filename,
            "https://github.com/google/re2/archive/refs/tags/" + version_str + ".tar.gz",
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        strip_prefix = "re2-" + version_str,
    )
