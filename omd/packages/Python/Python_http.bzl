load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def python(version_str, sha256):
    filename = "Python-" + version_str + ".tar.xz"
    http_archive(
        name = "python",
        build_file = "@omd_packages//omd/packages/Python:BUILD.Python.bazel",
        urls = [
            "https://www.python.org/ftp/python/" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        strip_prefix = "Python-" + version_str,
    )
