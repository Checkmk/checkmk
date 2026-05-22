load("@rules_python//python:defs.bzl", "py_binary", "py_library")

py_library(
    name = "crash_owner_rollup_lib",
    srcs = [
        "__init__.py",
        "cache.py",
        "cli.py",
        "diff.py",
        "emit.py",
        "fetch.py",
        "routing.py",
    ],
    deps = [
        "//.github/skills/crash_report:crash_report_lib",
    ],
)

py_binary(
    name = "crash_owner_rollup",
    srcs = ["__main__.py"],
    main = "__main__.py",
    deps = [":crash_owner_rollup_lib"],
)
