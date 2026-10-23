load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")

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
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-livestatus-client",
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
        "//cmk/base/config",
        "//cmk/product_usage",
        "//cmk/utils:paths",
    ],
)

py_binary(
    name = "manifest_generator",
    testonly = True,
    srcs = ["manifest.py"],
    main = "manifest.py",
    deps = [":product_usage"],
)

run_binary(
    name = "manifest",
    testonly = True,
    outs = ["manifest.json"],
    args = ["$(execpath manifest.json)"],
    tool = ":manifest_generator",
    visibility = ["//visibility:public"],
)
