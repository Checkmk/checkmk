load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "pytest_helpers",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = ["//tests:__subpackages__"],
    deps = [
        "//tests/testlib/common",
        requirement("psutil"),
        requirement("pytest"),
        requirement("pytest-check"),
    ],
)
