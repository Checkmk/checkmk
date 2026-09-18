load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "packaging",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = ["//tests:__subpackages__"],
    deps = [
        "//tests/testlib",
        "//tests/testlib/common:utils",
        requirement("pytest"),
    ],
)
