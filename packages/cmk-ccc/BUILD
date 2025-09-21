load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
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
    name = "_init",
    srcs = ["cmk/ccc/__init__.py"],
    imports = ["."],
)

py_library(
    name = "cleanup",
    srcs = ["cmk/ccc/cleanup.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "resulttype",
    srcs = ["cmk/ccc/resulttype.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "config-path",
    srcs = ["cmk/ccc/config_path.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "store",
    ],
)

py_library(
    name = "cpu-tracking",
    srcs = ["cmk/ccc/cpu_tracking.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "crash-reporting",
    srcs = ["cmk/ccc/crash_reporting.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "_init",
        "plugin-registry",
        "store",
    ],
)

py_library(
    name = "daemon",
    srcs = ["cmk/ccc/daemon.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "_init",
        "exceptions",
        "store",
    ],
)

py_library(
    name = "debug",
    srcs = ["cmk/ccc/debug.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = ["_init"],
)

py_library(
    name = "exceptions",
    srcs = ["cmk/ccc/exceptions.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = ["_init"],
)

py_library(
    name = "hostaddress",
    srcs = ["cmk/ccc/hostaddress.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = ["_init"],
)

py_library(
    name = "i18n",
    srcs = ["cmk/ccc/i18n.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = ["_init"],
)

py_library(
    name = "observer",
    srcs = ["cmk/ccc/observer.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = ["_init"],
)

py_library(
    name = "plugin-registry",
    srcs = ["cmk/ccc/plugin_registry.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = ["_init"],
)

py_library(
    name = "profile",
    srcs = ["cmk/ccc/profile.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = ["_init"],
)

py_library(
    name = "site",
    srcs = ["cmk/ccc/site.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "_init",
        "i18n",
    ],
)

py_library(
    name = "store",
    srcs = [
        "cmk/ccc/store/__init__.py",
        "cmk/ccc/store/_file.py",
        "cmk/ccc/store/_locks.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "_init",
        "debug",
        "exceptions",
        "i18n",
        "//packages/cmk-trace",
    ],
)

py_library(
    name = "user",
    srcs = ["cmk/ccc/user.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = ["_init"],
)

py_library(
    name = "version",
    srcs = [
        "cmk/ccc/general_version_infos.py",
        "cmk/ccc/version.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "_init",
        "crash-reporting",
        "site",
    ],
)

py_library(
    name = "timeout",
    srcs = ["cmk/ccc/timeout.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "_init",
        "exceptions",
    ],
)

py_library(
    name = "tty",
    srcs = ["cmk/ccc/tty.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [],
)

_ALL = [
    "cleanup",
    "config-path",
    "cpu-tracking",
    "crash-reporting",
    "daemon",
    "debug",
    "exceptions",
    "hostaddress",
    "i18n",
    "observer",
    "plugin-registry",
    "profile",
    "resulttype",
    "site",
    "store",
    "timeout",
    "tty",
    "user",
    "version",
]

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = _ALL,
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "daemon-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_daemon.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "daemon",
        "exceptions",
        "store",
        requirement("pytest"),
    ],
)

py_test(
    name = "hostaddress-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_hostaddress.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "hostaddress",
        requirement("pytest"),
    ],
)

py_test(
    name = "site-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_site.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "site",
        requirement("pytest"),
    ],
)

py_test(
    name = "resulttype-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_resulttype.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "resulttype",
        requirement("pytest"),
    ],
)

py_test(
    name = "tty-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_tty.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "tty",
        requirement("pytest"),
    ],
)

py_test(
    name = "store-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_store.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "debug",
        "store",
        requirement("pytest"),
    ],
)

py_test(
    name = "config-path-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_config_path.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "config-path",
        requirement("pytest"),
    ],
)

py_test(
    name = "cpu-tracking-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_cpu_tracking.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "cpu-tracking",
        requirement("pytest"),
    ],
)

py_test(
    name = "user-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_user.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "user",
        requirement("pytest"),
    ],
)

py_test(
    name = "observer-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/test_observer.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "observer",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-ccc",
    strip_path_prefixes = ["packages/cmk-ccc"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = _ALL + [
        ":py_typed",
    ],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/ccc/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
