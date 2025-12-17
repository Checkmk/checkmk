load("@rules_python//python:defs.bzl", "py_binary", "py_library")

py_library(
    name = "framework",
    srcs = ["framework.py"],
)

py_library(
    name = "checker_localization",
    srcs = ["checker_localization.py"],
    visibility = ["//tests/astrein:__subpackages__"],
    deps = [":framework"],
)

py_binary(
    name = "astrein",
    srcs = ["cli.py"],
    main = "cli.py",
    visibility = ["//visibility:public"],
    deps = [
        ":checker_localization",
        ":framework",
    ],
)
