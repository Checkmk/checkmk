load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "docker",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = ["//tests:__subpackages__"],
    deps = [
        requirement("docker"),
        requirement("pytest"),
        requirement("requests"),
        "//tests/testlib",
    ],
)
