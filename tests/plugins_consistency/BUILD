load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/base/config",  # hidden in a local import
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        requirement("pytest"),
    ],
)
