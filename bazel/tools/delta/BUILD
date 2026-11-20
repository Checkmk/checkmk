load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/tools:starlark_files.bzl", "STARLARK_EXCLUDED", "STARLARK_NAMES")

py_library(
    name = "bazel_delta",
    srcs = [
        "bazel_delta/__init__.py",
        "bazel_delta/__main__.py",
        "bazel_delta/errors.py",
        "bazel_delta/files.py",
        "bazel_delta/lint.py",
        "bazel_delta/summary.py",
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

# `bazel run //:lint -- --delta` fixes, `bazel run //:lint.check -- --delta` only reports.
[
    py_binary(
        name = name,
        srcs = ["bazel_delta/__main__.py"],
        args = [
            "lint",
            "--buildifier=$(rootpath @buildifier_prebuilt//:buildifier)",
            "--buildifier_config=$(rootpath //:buildifier_config)",
        ] + [
            "--starlark_exclude=%s" % pattern
            for pattern in STARLARK_EXCLUDED
        ] + [
            "--starlark_name=%s" % pattern
            for pattern in STARLARK_NAMES
        ] + fix_args,
        data = [
            "//:buildifier_config",
            "@buildifier_prebuilt//:buildifier",
        ],
        main = "bazel_delta/__main__.py",
        visibility = ["//visibility:public"],
        deps = [":bazel_delta"],
    )
    for name, fix_args in [
        (
            "lint",
            ["--fix"],
        ),
        ("lint.check", []),
    ]
]

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]),
    deps = [":bazel_delta"],
)
