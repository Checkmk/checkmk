load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")


def python(version_str, sha256):
    http_archive(
        name="python",
        build_file="@omd_packages//packages/Python:BUILD.Python.bazel",
        url="https://www.python.org/ftp/python/" + version_str + "/Python-" + version_str + ".tar.xz",
        sha256="29e4b8f5f1658542a8c13e2dd277358c9c48f2b2f7318652ef1675e402b9d2af",
        strip_prefix="Python-" + version_str,
    )
