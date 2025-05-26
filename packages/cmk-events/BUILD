load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-events",
    srcs = [
        "cmk/events/__init__.py",
        "cmk/events/event_context.py",
        "cmk/events/log_to_history.py",
        "cmk/events/notification_result.py",
        "cmk/events/notification_spool_file.py",
    ],
    data = [
        ":cmk/events/py.typed",
        ":pyproject.toml",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:store",
        "//packages/cmk-livestatus-client:py_livestatus",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-events"],
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-events",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-events",
    strip_path_prefixes = ["packages/cmk-events"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [":cmk-events"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
