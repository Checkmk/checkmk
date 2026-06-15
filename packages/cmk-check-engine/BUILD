load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

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
        "cmk/checkengine/snmplib/__init__.py",
        "cmk/checkengine/snmplib/_detect.py",
        "cmk/checkengine/snmplib/_getoid.py",
        "cmk/checkengine/snmplib/_parse.py",
        "cmk/checkengine/snmplib/_table.py",
        "cmk/checkengine/snmplib/_typedefs.py",
        "cmk/checkengine/snmplib/_walk.py",
    ],
    data = ["cmk/checkengine/snmplib/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":helper-interface",
        "//packages/cmk-ccc:cleanup",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:tty",
    ],
)

py_library(
    name = "snmp-backends",
    srcs = [
        "cmk/checkengine/snmp_backends/_utils.py",
        "cmk/checkengine/snmp_backends/classic.py",
        "cmk/checkengine/snmp_backends/stored_walk.py",
    ],
    data = ["cmk/checkengine/snmp_backends/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":helper-interface",
        ":snmplib",
    ],
)

py_library(
    name = "helper-interface",
    srcs = [
        "cmk/checkengine/helper_interface/__init__.py",
        "cmk/checkengine/helper_interface/_agentdatatype.py",
        "cmk/checkengine/helper_interface/_crashreporting.py",
        "cmk/checkengine/helper_interface/_exceptions.py",
        "cmk/checkengine/helper_interface/_source_info.py",
    ],
    data = ["cmk/checkengine/helper_interface/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-ccc:hostaddress",
    ],
)

py_library(
    name = "fetchers",
    srcs = [
        "cmk/checkengine/fetchers/__init__.py",
        "cmk/checkengine/fetchers/_abstract.py",
        "cmk/checkengine/fetchers/_ipmi.py",
        "cmk/checkengine/fetchers/_metric_backend.py",
        "cmk/checkengine/fetchers/_nofetcher.py",
        "cmk/checkengine/fetchers/_piggyback.py",
        "cmk/checkengine/fetchers/_program.py",
        "cmk/checkengine/fetchers/_snmp/__init__.py",
        "cmk/checkengine/fetchers/_snmp/_cache.py",
        "cmk/checkengine/fetchers/_snmp/_fetcher.py",
        "cmk/checkengine/fetchers/_snmp/_scan.py",
        "cmk/checkengine/fetchers/_tcp/__init__.py",
        "cmk/checkengine/fetchers/_tcp/agent_protocol.py",
        "cmk/checkengine/fetchers/filecache/__init__.py",
        "cmk/checkengine/fetchers/filecache/_agent.py",
        "cmk/checkengine/fetchers/filecache/_cache.py",
        "cmk/checkengine/fetchers/filecache/_snmp.py",
        "cmk/checkengine/fetchers/snmp_backend.py",
    ] + glob(
        [
            "cmk/checkengine/fetchers/_utils/*.py",
        ],
    ),
    data = ["cmk/checkengine/fetchers/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":helper-interface",
        ":snmp-backends",
        ":snmplib",
        requirement("pyghmi"),
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:password_store",
    ],
)

py_library(
    name = "fetcher-protocol",
    srcs = [
        "cmk/checkengine/fetcher.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":helper-interface",
        ":snmplib",
        "//packages/cmk-ccc:cpu-tracking",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:resulttype",
    ],
)

py_library(
    name = "specs",
    srcs = glob([
        "cmk/checkengine/specs/*.py",
    ]),
    data = ["cmk/checkengine/specs/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
    ],
)

py_library(
    name = "section-parser",
    srcs = [
        "cmk/checkengine/sectionparser.py",
        "cmk/checkengine/sectionparserutils.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":helper-interface",
        ":specs",
        "//cmk/piggyback:backend",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-check-engine/cmk/checkengine/parser",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
    ],
)

py_library(
    name = "lib",
    srcs = [
        "cmk/checkengine/submitters.py",
        "cmk/checkengine/summarize.py",
        "cmk/checkengine/value_store.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":helper-interface",
        ":specs",
        "//cmk/piggyback:backend",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:timeout",
        "//packages/cmk-check-engine/cmk/checkengine/parser",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
    ],
)

py_test(
    name = "fetchers-tests",
    size = "small",
    srcs = glob(["tests/cmk/checkengine/fetchers/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        "__test__",
        requirement("pytest"),
        requirement("pyghmi"),
        ":fetchers",
        "//packages/cmk-plugin-apis:agent_based",
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_test(
    name = "snmplib-tests",
    size = "small",
    srcs = glob(["tests/cmk/checkengine/snmplib/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        "__test__",
        "snmplib",
        "//packages/cmk-plugin-apis:agent_based",
        requirement("pytest"),
    ],
)

py_test(
    name = "snmp-backends-tests",
    size = "small",
    srcs = glob(["tests/cmk/checkengine/snmp_backends/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        "__test__",
        "snmp-backends",
        "snmplib",
        requirement("pytest"),
    ],
)

py_test(
    name = "specs-tests",
    size = "small",
    srcs = glob(["tests/cmk/checkengine/specs/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        "__test__",
        "specs",
        requirement("pytest"),
    ],
)

py_test(
    name = "parser-tests",
    size = "small",
    srcs = glob([
        "tests/cmk/checkengine/parser/*.py",
    ]) + [
        ":__test__.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        "//packages/cmk-check-engine/cmk/checkengine/parser",
        requirement("pytest"),
    ],
)

py_test(
    name = "section-parser-tests",
    size = "small",
    srcs = glob([
        "tests/cmk/checkengine/sectionparser/*.py",
    ]) + [
        ":__test__.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        ":section-parser",
        requirement("pytest"),
    ],
)

py_test(
    name = "lib-tests",
    size = "small",
    srcs = [
        "tests/cmk/checkengine/test_submitters.py",
        "tests/cmk/checkengine/test_summarizers.py",
        "tests/cmk/checkengine/test_value_store.py",
        ":__test__.py",
    ],
    main = "__test__.py",
    deps = [
        "__test__",
        ":lib",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
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
    visibility = ["//visibility:public"],
    deps = [
        ":fetcher-protocol",
        ":fetchers",
        ":helper-interface",
        ":lib",
        ":section-parser",
        ":snmp-backends",
        ":snmplib",
        ":specs",
        "//packages/cmk-check-engine/cmk/checkengine/parser",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
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

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":fetchers",
        ":fetcher-protocol",
        ":helper-interface",
        ":snmplib",
        ":specs",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-check-engine/cmk/checkengine/parser",
    ],
    requirements_in = "requirements.in",
)
