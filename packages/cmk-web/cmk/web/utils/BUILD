load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "utils",
    srcs = glob(["*.py"]),
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:regex",
        "//packages/cmk-web:context",
        requirement("flask"),
    ],
)
