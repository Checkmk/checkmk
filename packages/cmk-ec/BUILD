load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-ec",
    srcs = [
        "cmk/ec/__init__.py",
        "cmk/ec/actions.py",
        "cmk/ec/config.py",
        "cmk/ec/core_queries.py",
        "cmk/ec/defaults.py",
        "cmk/ec/event.py",
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
        "cmk/ec/syslog.py",
        "cmk/ec/timeperiod.py",
    ],
    data = [":py_typed"],
    imports = ["."],
    visibility = [
        "//cmk:__pkg__",
        "//non-free/packages:__subpackages__",
        "//packages:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:profile",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:translations",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-events",
        "//packages/cmk-mkp-tool",
        requirement("pyasn1"),
        requirement("pymongo"),
        requirement("pysnmp"),
        requirement("python-dateutil"),
        requirement("setproctitle"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-ec"],
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
        ":cmk-ec",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-ec",
    strip_path_prefixes = ["packages/cmk-ec"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-ec",
        ":py_typed",
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
    visibility = ["//visibility:public"],
    whl = "wheel",
)
