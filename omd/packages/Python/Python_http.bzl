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
        sha256 = "c30bb24b7f1e9a19b11b55a546434f74e739bb4c271a3e3a80ff4380d49f7adb",
        strip_prefix = "Python-" + version_str,
    )
