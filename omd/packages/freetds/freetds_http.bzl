load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")


def freetds(version_str, sha256):
    http_archive(
        name="freetds",
        build_file="@omd_packages//packages/freetds:BUILD.freetds.bazel",
        urls=[
            "https://www.freetds.org/files/stable/freetds-" + version_str + ".tar.gz",
            UPSTREAM_MIRROR_URL + "freetds-" + version_str + ".tar.gz",
        ],
        sha256=sha256,
        strip_prefix="freetds-" + version_str,
    )
