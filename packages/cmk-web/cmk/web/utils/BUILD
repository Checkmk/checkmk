load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "utils",
    srcs = glob(["*.py"]),
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = ["//packages/cmk-ccc:regex"],
)
