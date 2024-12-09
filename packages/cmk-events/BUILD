load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
])

py_library(
    name = "cmk-events",
    srcs = [
        "cmk/events/__init__.py",
        "cmk/events/event_context.py",
        "cmk/events/log_to_history.py",
        "cmk/events/notification_result.py",
        "cmk/events/notification_spool_file.py",
        "cmk/events/py.typed",
    ],
    data = [":pyproject.toml"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc",
        "//packages/cmk-livestatus-client:py_livestatus",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-events",
    strip_path_prefixes = ["packages/cmk-events"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-events",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
