load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:package_versions.bzl", "PYTHON_VERSION")

def python_workspace():
    version_str = PYTHON_VERSION
    filename = "Python-" + version_str + ".tar.xz"
    http_archive(
        name = "python",
        build_file = "@omd_packages//omd/packages/Python:BUILD.Python.bazel",
        urls = [
            "https://www.python.org/ftp/python/" + version_str + "/" + filename,
            # UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "c08bc65a81971c1dd5783182826503369466c7e67374d1646519adf05207b684",
        strip_prefix = "Python-" + version_str,
    )
