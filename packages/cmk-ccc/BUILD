load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cleanup",
    srcs = ["cmk/ccc/cleanup.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "inotify",
    srcs = ["cmk/ccc/inotify.py"],
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
    name = "daemon",
    srcs = ["cmk/ccc/daemon.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "exceptions",
        "store",
    ],
)

py_library(
    name = "debug",
    srcs = ["cmk/ccc/debug.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "exceptions",
    srcs = ["cmk/ccc/exceptions.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "hostaddress",
    srcs = ["cmk/ccc/hostaddress.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "i18n",
    srcs = ["cmk/ccc/i18n.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "log",
    srcs = ["cmk/ccc/log.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "observer",
    srcs = ["cmk/ccc/observer.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "plugin-registry",
    srcs = ["cmk/ccc/plugin_registry.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "profile",
    srcs = ["cmk/ccc/profile.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "regex",
    srcs = ["cmk/ccc/regex.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "exceptions",
        "i18n",
    ],
)

py_library(
    name = "site",
    srcs = ["cmk/ccc/site.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
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
        "debug",
        "exceptions",
        "i18n",
        "//packages/cmk-trace",
    ],
)

py_library(
    name = "translations",
    srcs = ["cmk/ccc/translations.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "regex",
    ],
)

py_library(
    name = "user",
    srcs = ["cmk/ccc/user.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "tar-archive",
    srcs = ["cmk/ccc/tar_archive.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "version",
    srcs = ["cmk/ccc/version.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "version-info",
    srcs = ["cmk/ccc/version_info.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "site",
        "version",
    ],
)

py_library(
    name = "general-version-infos",
    srcs = ["cmk/ccc/general_version_infos.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "version-info",
    ],
)

py_library(
    name = "timeout",
    srcs = ["cmk/ccc/timeout.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "exceptions",
    ],
)

py_library(
    name = "tty",
    srcs = ["cmk/ccc/tty.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

_ALL = [
    "cleanup",
    "config-path",
    "cpu-tracking",
    "daemon",
    "debug",
    "exceptions",
    "hostaddress",
    "i18n",
    "inotify",
    "log",
    "observer",
    "plugin-registry",
    "profile",
    "resulttype",
    "regex",
    "site",
    "store",
    "tar-archive",
    "timeout",
    "translations",
    "tty",
    "user",
    "version",
    "version-info",
    "general-version-infos",
]

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = _ALL,
)

py_cmk_test(
    name = "daemon-tests",
    size = "small",
    srcs = [
        "tests/test_daemon.py",
    ],
    deps = [
        "daemon",
        "exceptions",
        "store",
    ],
)

py_cmk_test(
    name = "hostaddress-tests",
    size = "small",
    srcs = [
        "tests/test_hostaddress.py",
    ],
    deps = [
        "hostaddress",
    ],
)

py_cmk_test(
    name = "regex-tests",
    size = "small",
    srcs = [
        "tests/test_regex.py",
    ],
    deps = [
        "regex",
    ],
)

py_cmk_test(
    name = "resulttype-tests",
    size = "small",
    srcs = [
        "tests/test_resulttype.py",
    ],
    deps = [
        "resulttype",
    ],
)

py_cmk_test(
    name = "translations-tests",
    size = "small",
    srcs = [
        "tests/test_translations.py",
    ],
    deps = [
        "translations",
    ],
)

py_cmk_test(
    name = "tty-tests",
    size = "small",
    srcs = [
        "tests/test_tty.py",
    ],
    deps = [
        "tty",
    ],
)

py_cmk_test(
    name = "store-tests",
    size = "small",
    srcs = [
        "tests/test_store.py",
    ],
    deps = [
        "debug",
        "store",
    ],
)

py_cmk_test(
    name = "config-path-tests",
    size = "small",
    srcs = [
        "tests/test_config_path.py",
    ],
    deps = [
        "config-path",
    ],
)

py_cmk_test(
    name = "cpu-tracking-tests",
    size = "small",
    srcs = [
        "tests/test_cpu_tracking.py",
    ],
    deps = [
        "cpu-tracking",
    ],
)

py_cmk_test(
    name = "tar-archive-tests",
    size = "small",
    srcs = [
        "tests/test_tar_archive.py",
    ],
    deps = [
        "tar-archive",
    ],
)

py_cmk_test(
    name = "user-tests",
    size = "small",
    srcs = [
        "tests/test_user.py",
    ],
    deps = [
        "user",
    ],
)

py_cmk_test(
    name = "observer-tests",
    size = "small",
    srcs = [
        "tests/test_observer.py",
    ],
    deps = [
        "observer",
    ],
)

py_cmk_test(
    name = "log-tests",
    size = "small",
    srcs = [
        "tests/test_log.py",
    ],
    deps = [
        "log",
        requirement("time-machine"),
    ],
)

py_library(
    name = "wheel_only_files",
    srcs = ["cmk/ccc/__init__.py"],
    data = ["cmk/ccc/py.typed"],
    imports = ["."],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-ccc",
    entry_points = {"console_scripts": ["cmk-general-version-infos = cmk.ccc.general_version_infos:main"]},
    strip_path_prefixes = ["packages/cmk-ccc"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = _ALL + [":wheel_only_files"],
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

py_requirements_test(
    name = "requirements-test",
    libs = _ALL + [":wheel_only_files"],
    requirements_in = "requirements.in",
)
