load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")
load("//bazel/rules:xcomp/cc.bzl", "cc_binary")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

py_library(
    name = "event",
    srcs = ["cmk/ec/event.py"],
    imports = ["."],
    visibility = [
        "//visibility:public",
    ],
    deps = [
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:translations",
        requirement("python-dateutil"),
    ],
)

py_library(
    name = "syslog",
    srcs = ["cmk/ec/syslog.py"],
    imports = ["."],
    visibility = [
        "//visibility:public",
    ],
)

py_library(
    name = "forwarder",
    srcs = ["cmk/ec/forwarder.py"],
    imports = ["."],
    visibility = [
        "//visibility:public",
    ],
    deps = [
        ":event",
        ":syslog",
        "//packages/cmk-ccc:hostaddress",
    ],
)

py_library(
    name = "mib_compiler",
    srcs = ["cmk/ec/mib_compiler.py"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [requirement("pysmi")],
)

py_library(
    name = "cmk-ec",
    srcs = [
        "cmk/ec/__init__.py",
        "cmk/ec/actions.py",
        "cmk/ec/config.py",
        "cmk/ec/core_queries.py",
        "cmk/ec/defaults.py",
        "cmk/ec/export.py",
        "cmk/ec/helpers.py",
        "cmk/ec/history.py",
        "cmk/ec/history_file.py",
        "cmk/ec/history_mongo.py",
        "cmk/ec/history_sqlite.py",
        "cmk/ec/host_config.py",
        "cmk/ec/log_level.py",
        "cmk/ec/main.py",
        "cmk/ec/mkp.py",
        "cmk/ec/perfcounters.py",
        "cmk/ec/query.py",
        "cmk/ec/rule_matcher.py",
        "cmk/ec/rule_packs.py",
        "cmk/ec/settings.py",
        "cmk/ec/snmp.py",
        "cmk/ec/timeperiod.py",
    ],
    data = [":py_typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":event",
        ":syslog",
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:profile",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:translations",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-crash:crash",
        "//packages/cmk-events",
        "//packages/cmk-mkp-tool",
        requirement("pyasn1"),
        requirement("pymongo"),
        requirement("pysnmp"),
        requirement("setproctitle"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        "cmk-ec",
        "event",
        "forwarder",
        "mib_compiler",
        "syslog",
    ],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/unit/**/*.py"]),
    args = ["packages/cmk-ec/tests/unit"],
    deps = [
        ":cmk-ec",
        ":forwarder",
        requirement("time-machine"),
    ],
)

py_cmk_test(
    name = "component",
    size = "small",
    srcs = glob(["tests/component/**/*.py"]),
    args = ["packages/cmk-ec/tests/component"],
    deps = [":mib_compiler"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-ec",
    entry_points = {"console_scripts": ["mkeventd = cmk.ec.main:main"]},
    strip_path_prefixes = ["packages/cmk-ec"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-ec",
        ":event",
        ":forwarder",
        ":mib_compiler",
        ":py_typed",
        ":syslog",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/ec/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    additional_files = [
        ":mkevent_bin",
        ":mkeventd_open514_bin",
    ],
    visibility = ["//visibility:public"],
    whl = "wheel",
)

sh_library(
    name = "helpers",
    srcs = [
        ".do-it",
        "run",
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":event",
        ":syslog",
        ":forwarder",
        ":cmk-ec",
        ":mib_compiler",
    ],
    requirements_in = "requirements.in",
)

cc_binary(
    name = "mkevent",
    srcs = ["src/mkevent.cc"],
    copts = [
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    features = [
        "static_libstdcpp",
    ],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    tags = ["no-lint"],
)

cc_binary(
    name = "mkeventd_open514",
    srcs = ["src/mkeventd_open514.cc"],
    copts = [
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    features = [
        "static_libstdcpp",
    ],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    tags = ["no-lint"],
)

pkg_files(
    name = "mkevent_bin",
    srcs = [":mkevent"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

# Gets CAP_NET_BIND_SERVICE by the packaging, so it must not be world-executable.
pkg_files(
    name = "mkeventd_open514_bin",
    srcs = [":mkeventd_open514"],
    attributes = pkg_attributes(
        mode = "0750",
    ),
    prefix = "bin",
)
