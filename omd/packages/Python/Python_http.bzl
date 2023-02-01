load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# Also defined in defines.make
python_version_major="3"
python_version_minor="11"
python_version_patch="2"

python_version=python_version_major + "." + python_version_minor + "." + python_version_patch
python_major_minor=python_version_major + python_version_minor
python_major_dot_minor=python_version_major + "." + python_version_minor
python_sha256="29e4b8f5f1658542a8c13e2dd277358c9c48f2b2f7318652ef1675e402b9d2af"

def python():
    http_archive(
        name="python",
        build_file="@omd_packages//packages/Python:BUILD.Python.bazel",
        url="https://www.python.org/ftp/python/" + python_version + "/Python-" + python_version + ".tar.xz",
        sha256=python_sha256,
        strip_prefix="Python-" + python_version,
    )


