load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
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

py_library(
    name = "fetchers",
    srcs = [
        "cmk/fetchers/__init__.py",
        "cmk/fetchers/_abstract.py",
        "cmk/fetchers/_agentprtcl.py",
        "cmk/fetchers/_ipmi.py",
        "cmk/fetchers/_metric_backend.py",
        "cmk/fetchers/_nofetcher.py",
        "cmk/fetchers/_piggyback.py",
        "cmk/fetchers/_program.py",
        "cmk/fetchers/_secrets.py",
        "cmk/fetchers/_snmp.py",
        "cmk/fetchers/_snmpscan.py",
        "cmk/fetchers/_tcp.py",
        "cmk/fetchers/_trigger.py",
        "cmk/fetchers/config.py",
        "cmk/fetchers/filecache/__init__.py",
        "cmk/fetchers/filecache/_agent.py",
        "cmk/fetchers/filecache/_cache.py",
        "cmk/fetchers/filecache/_snmp.py",
        "cmk/fetchers/serializertype.py",
        "cmk/fetchers/snmp.py",
        "cmk/fetchers/snmp_backend/__init__.py",
        "cmk/fetchers/snmp_backend/_utils.py",
        "cmk/fetchers/snmp_backend/classic.py",
        "cmk/fetchers/snmp_backend/stored_walk.py",
    ],
    data = ["cmk/fetchers/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":helper-interface",
        ":snmplib",
        requirement("pyghmi"),
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-crypto",
        "//packages/cmk-plugin-apis:password_store",
    ] + select({
        "@//:gpl+nonfree_repo": [
            "//non-free/packages/cmk-core-helpers:inline-snmp",
        ],
        "@//:gpl_repo": [],
    }),
)

py_test(
    name = "fetchers-tests",
    size = "small",
    srcs = [
        "__test__.py",
        "tests/cmk/fetchers/snmp_backend/test_classic_snmp.py",
        "tests/cmk/fetchers/snmp_backend/test_stored_walk.py",
        "tests/cmk/fetchers/test_agentprtcl.py",
        "tests/cmk/fetchers/test_snmp.py",
        "tests/cmk/fetchers/test_snmpscan.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        requirement("pytest"),
        ":fetchers",
        "//packages/cmk-plugin-apis:agent_based",
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
        ":fetchers",
        ":helper-interface",
        ":snmplib",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

package_wheel(
    name = "wheel_pkg",
    whl = "wheel",
)

pkg_tar(
    name = "pkg_tar",
    stamp = 1,
    visibility = ["//omd:__subpackages__"],
    deps = [
        ":wheel_pkg",
    ],
)
