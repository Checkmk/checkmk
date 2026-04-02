load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@rules_shell//shell:sh_library.bzl", "sh_library")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

py_library(
    name = "config",
    srcs = ["cmk/logwatch/config.py"],
    imports = ["."],
    visibility = ["//cmk:__subpackages__"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
    ],
)

py_library(
    name = "plugins",
    srcs = glob(["cmk/plugins/logwatch/**/*.py"]),
    data = [
        "cmk/plugins/logwatch/py.typed",
    ] + glob([
        "cmk/plugins/logwatch/checkman/*",
    ]),
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ec:event",
        "//packages/cmk-ec:forwarder",
        "//packages/cmk-ec:syslog",
        "//packages/cmk-plugin-apis:agent_based",
    ],
)

py_test(
    name = "plugins-test",
    size = "small",
    srcs = glob(["tests/unit/cmk/plugins/logwatch/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":plugins",
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":config",
        ":plugins",
    ],
    tags = ["no-mypy"],
)

filegroup(
    name = "py_typed",
    srcs = glob(["**/py.typed"]),
)

filegroup(
    name = "checkman",
    srcs = glob(
        ["cmk/plugins/logwatch/checkman/**/*"],
    ),
)

py_wheel(
    name = "wheel",
    distribution = "cmk-logwatch",
    strip_path_prefixes = ["packages/cmk-logwatch"],
    tags = ["manual"],
    version = "1.0.0",
    deps = [
        ":checkman",
        ":config",
        ":plugins",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
    ],
)
