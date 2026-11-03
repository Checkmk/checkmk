load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    imports = ["../.."],
    visibility = ["//tests:__subpackages__"],
    deps = [
        "//tests:pkg_marker",
        "//tests/testlib/pytest_helpers",
        "//tests/testlib/system",
        requirement("pytest"),
    ],
)
