load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "bazel_devserver",
    srcs = [
        "bazel_devserver/__init__.py",
        "bazel_devserver/__main__.py",
        "bazel_devserver/dev_server.py",
        "bazel_devserver/errors.py",
        "bazel_devserver/process_tree.py",
        "bazel_devserver/rebuild_loop.py",
    ],
    imports = ["."],
    deps = [requirement("watchdog")],
)

py_binary(
    name = "devserver",
    srcs = ["bazel_devserver/__main__.py"],
    main = "bazel_devserver/__main__.py",
    visibility = ["//visibility:public"],
    deps = [":bazel_devserver"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]),
    deps = [":bazel_devserver"],
)
