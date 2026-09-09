load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

exports_files(["dev-requirements.in"])

py_library(
    name = "pkg_marker",
    srcs = ["__init__.py"],
    imports = [".."],
    visibility = ["//:__subpackages__"],
)

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    deps = [
        "//tests/testlib/common",
        requirement("playwright"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pytest-metadata"),
        "//tests/testlib/pytest_helpers",
        "//tests/testlib/system",
    ],
)
