load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "html_validation",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("requests"),
    ],
)
