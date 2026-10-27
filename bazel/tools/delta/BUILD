load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "bazel_delta",
    srcs = [
        "bazel_delta/__init__.py",
        "bazel_delta/__main__.py",
        "bazel_delta/errors.py",
        "bazel_delta/files.py",
    ],
    imports = ["."],
)

# `delta files` prints the files a --delta option covers, see bazel_delta/files.py.
py_binary(
    name = "delta",
    srcs = ["bazel_delta/__main__.py"],
    main = "bazel_delta/__main__.py",
    visibility = ["//bazel/tools:__subpackages__"],
    deps = [":bazel_delta"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]),
    deps = [":bazel_delta"],
)
