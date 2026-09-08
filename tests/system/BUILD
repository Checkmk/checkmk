load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "pkg_marker",
    testonly = True,
    srcs = ["__init__.py"],
    imports = ["../.."],
    visibility = ["//tests:__subpackages__"],
)

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    imports = ["../.."],
    visibility = ["//tests:__subpackages__"],
    deps = [
        ":pkg_marker",
        "//tests/testlib/pytest_helpers",
        requirement("pytest"),
    ],
)
