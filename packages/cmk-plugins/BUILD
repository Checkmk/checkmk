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
    name = "plugins-lib",
    srcs = [
        "cmk/plugins/lib/cache_helper.py",
        "cmk/plugins/lib/container_cgroupv2.py",
        "cmk/plugins/lib/cpu.py",
        "cmk/plugins/lib/cpu_load.py",
        "cmk/plugins/lib/cpu_util.py",
        "cmk/plugins/lib/cpu_utilization_os.py",
        "cmk/plugins/lib/db.py",
        "cmk/plugins/lib/device_types.py",
        "cmk/plugins/lib/df.py",
        "cmk/plugins/lib/dhcp_pools.py",
        "cmk/plugins/lib/diskstat.py",
        "cmk/plugins/lib/elphase.py",
        "cmk/plugins/lib/entity_mib.py",
        "cmk/plugins/lib/entity_sensors.py",
        "cmk/plugins/lib/eval_regex.py",
        "cmk/plugins/lib/fan.py",
        "cmk/plugins/lib/humidity.py",
        "cmk/plugins/lib/if64.py",
        "cmk/plugins/lib/interfaces.py",
        "cmk/plugins/lib/inventory_interfaces.py",
        "cmk/plugins/lib/ip_format.py",
        "cmk/plugins/lib/labels.py",
        "cmk/plugins/lib/lnx_if.py",
        "cmk/plugins/lib/memory.py",
        "cmk/plugins/lib/mssql_counters.py",
        "cmk/plugins/lib/multipath.py",
        "cmk/plugins/lib/node_exporter.py",
        "cmk/plugins/lib/ps.py",
        "cmk/plugins/lib/size_trend.py",
        "cmk/plugins/lib/tcp_connections.py",
        "cmk/plugins/lib/temperature.py",
        "cmk/plugins/lib/timesync.py",
        "cmk/plugins/lib/ucd_hr_detection.py",
        "cmk/plugins/lib/uptime.py",
        "cmk/plugins/lib/wlc_clients.py",
    ],
    data = ["cmk/plugins/lib/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        "plugins-lib",
    ],
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "plugins-lib-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/lib/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":plugins-lib",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-plugins",
    strip_path_prefixes = ["packages/cmk-plugins"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":plugins-lib",
    ],
)

filegroup(
    name = "py_typed",
    srcs = [
        "cmk/plugins/lib/py.typed",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
