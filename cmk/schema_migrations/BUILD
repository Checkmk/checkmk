load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "oauth",
    srcs = glob(["oauth/**/*.py"]),
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//packages/cmk-schema-manager",
    ],
)
