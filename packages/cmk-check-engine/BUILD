load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files(
    [
        "dev-requirements.in",
        "pyproject.toml",
        "requirements.in",
    ],
)

py_library(
    name = "snmplib",
    srcs = [
        "cmk/snmplib/__init__.py",
        "cmk/snmplib/_detect.py",
        "cmk/snmplib/_getoid.py",
        "cmk/snmplib/_table.py",
        "cmk/snmplib/_typedefs.py",
        "cmk/snmplib/_walk.py",
    ],
    data = ["cmk/snmplib/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:cleanup",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:tty",
    ],
)

py_library(
    name = "helper-interface",
    srcs = [
        "cmk/helper_interface/__init__.py",
        "cmk/helper_interface/_agentdatatype.py",
        "cmk/helper_interface/_exceptions.py",
        "cmk/helper_interface/_source_info.py",
    ],
    data = ["cmk/helper_interface/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:hostaddress",
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "snmplib-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/cmk/snmplib/__init__.py",
        "tests/cmk/snmplib/test_ab_type_defs.py",
        "tests/cmk/snmplib/test_type_defs.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "snmplib",
        "//packages/cmk-plugin-apis:agent_based",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-check-engine",
    strip_path_prefixes = ["packages/cmk-check-engine"],
    # Keep in sync with pyproject.toml
    version = "1.0.0",
    deps = [
        ":helper-interface",
        ":snmplib",
    ],
)

package_wheel(
    name = "wheel_pkg",
    whl = "wheel",
)

pkg_tar(
    name = "pkg_tar",
    visibility = ["//omd:__pkg__"],
    deps = [
        ":wheel_pkg",
    ],
)
