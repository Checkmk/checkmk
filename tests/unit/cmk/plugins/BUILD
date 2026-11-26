load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "plugins",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    data = glob(
        include = [
            "**/*.json",
            "**/*.yaml",
        ],
    ),
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/config",
        "//cmk/gui/rule_specs:legacy_converter",
        "//cmk/gui/watolib",
        "//cmk/plugins",
        "//cmk/plugins/diagnostics/cli",
        "//cmk/plugins/diagnostics/cli/handlers",
        "//cmk/product_usage",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-plugin-apis:cli",
        "//packages/cmk-plugins:azure_deprecated",
        "//packages/cmk-plugins:azure_v2",
        "//packages/cmk-plugins:docker",
        "//packages/cmk-plugins:proxmox_ve",
        "//tests/testlib/common",
        "//tests/testlib/unit:bakelet_testing",
        requirement("exchangelib"),
        requirement("feedparser"),
        requirement("polyfactory"),
        requirement("pysmb"),
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("python-snap7"),
        requirement("requests"),
        requirement("responses"),
        requirement("time-machine"),
        requirement("vcrpy"),
    ],
)
