load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def re2(version, sha256):
    filename = "re2-" + version
    http_archive(
        name = "re2",
        urls = [
            # Also checked in under "/third_party/re2"
            "https://github.com/google/re2/archive/refs/tags/" + version + ".tar.gz",
            # TODO: add mirror
        ],
        sha256 = sha256,
        strip_prefix = filename,
    )
