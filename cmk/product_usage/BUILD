load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files(
    ["cli.py"],
    visibility = ["//bin:__pkg__"],
)

py_library(
    name = "product_usage",
    srcs = glob(
        ["**/*.py"],
        exclude = ["cli.py"],
    ),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("requests"),
        requirement("werkzeug"),
    ],
)

py_library(
    name = "product_usage_cli",
    srcs = ["cli.py"],
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/base:app",
        "//cmk/base:config",
        "//cmk/product_usage",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
    ],
)
