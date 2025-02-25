load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")
load("//:package_versions.bzl", "PYTHON_VERSION")

def python_workspace():
    version_str = PYTHON_VERSION
    filename = "Python-" + version_str + ".tar.xz"
    http_archive(
        name = "python",
        build_file = "@omd_packages//omd/packages/Python:BUILD.Python.bazel",
        urls = [
            "https://www.python.org/ftp/python/" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "7220835d9f90b37c006e9842a8dff4580aaca4318674f947302b8d28f3f81112",
        strip_prefix = "Python-" + version_str,
    )
